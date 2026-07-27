import os
import re
import requests
from requests.auth import HTTPBasicAuth
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class TicketFetchInput(BaseModel):
    source_type: str = Field(
        ...,
        description="The source tracker type. Allowed: 'github_issue', 'jira', 'raw_text'"
    )
    source_value: str = Field(
        ...,
        description="The URL (for github_issue/jira) or the raw text content itself (for raw_text)."
    )

class TicketFetchTool(BaseTool):
    name: str = "ticket_fetch_tool"
    description: str = (
        "Fetches issue, PR, or task details from external tracking platforms (GitHub, Jira) "
        "using environment credentials, or handles raw text directly. Returns a unified markdown ticket report."
    )
    args_schema: Type[BaseModel] = TicketFetchInput

    def _run(self, source_type: str, source_value: str) -> str:
        source_type = source_type.strip().lower()
        source_value = source_value.strip()

        if source_type == "raw_text":
            return self._handle_raw_text(source_value)
        elif source_type == "github_issue":
            return self._handle_github_issue(source_value)
        elif source_type == "jira":
            return self._handle_jira(source_value)
        else:
            return f"Error: Unsupported source_type '{source_type}'. Allowed types are 'github_issue', 'jira', 'raw_text'."

    def _handle_raw_text(self, text: str) -> str:
        return (
            f"# Raw Input Ticket\n"
            f"- **Source Type:** Raw Text\n\n"
            f"## Content\n"
            f"{text}\n"
        )

    def _handle_github_issue(self, url: str) -> str:
        import urllib.parse
        
        # Unquote URL to decode query params (e.g. %7C -> |)
        unquoted_url = urllib.parse.unquote(url)
        
        # Try matching GitHub Projects board pane issue pattern:
        # e.g., issue=ChFardeelAzhar|CricScore|8
        proj_match = re.search(r"[?&]issue=([^&|]+)[|/]([^&|]+)[|/](\d+)", unquoted_url)
        
        if proj_match:
            owner, repo, number = proj_match.groups()
        else:
            # Fall back to standard issue/PR url regex
            # Example: https://github.com/Dev-Entity/tp-app/issues/12
            # Example: https://github.com/Dev-Entity/tp-app/pull/15
            match = re.search(r"github\.com/([^/]+)/([^/]+)/(issues|pull)/(\d+)", unquoted_url)
            if not match:
                # Check for classic project card URL or direct project cards endpoint
                card_match = re.search(r"card[s]?-(\d+)", unquoted_url)
                card_direct = re.search(r"projects/columns/cards/(\d+)", unquoted_url)
                card_id = None
                if card_match:
                    card_id = card_match.group(1)
                elif card_direct:
                    card_id = card_direct.group(1)

                if card_id:
                    return self._fetch_github_card(card_id)
                
                return f"Error: Could not parse GitHub issue/PR URL from '{url}'. Expected format: https://github.com/owner/repo/issues/number"
            owner, repo, _, number = match.groups()
        token = os.environ.get("GITHUB_TOKEN")
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if token:
            headers["Authorization"] = f"token {token}"

        # Fetch Issue/PR
        issue_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
        try:
            r = requests.get(issue_url, headers=headers, timeout=15)
            if r.status_code != 200:
                return f"Error: GitHub API returned status code {r.status_code} for issue lookup: {r.text}"
            
            issue_data = r.json()
            title = issue_data.get("title", "No Title")
            body = issue_data.get("body", "No Description")
            state = issue_data.get("state", "unknown")
            labels = ", ".join([l.get("name", "") for l in issue_data.get("labels", [])])
            author = issue_data.get("user", {}).get("login", "unknown")

            # Fetch Comments
            comments_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}/comments"
            comments_str = ""
            cr = requests.get(comments_url, headers=headers, timeout=15)
            if cr.status_code == 200:
                comments = cr.json()
                if comments:
                    comments_str = "\n## Comments\n"
                    for idx, c in enumerate(comments, 1):
                        c_author = c.get("user", {}).get("login", "unknown")
                        c_body = c.get("body", "")
                        comments_str += f"### Comment #{idx} by @{c_author}\n{c_body}\n\n"

            markdown_report = (
                f"# GitHub Issue #{number}: {title}\n"
                f"- **Source URL:** {url}\n"
                f"- **State:** {state}\n"
                f"- **Author:** @{author}\n"
                f"- **Labels:** {labels if labels else 'None'}\n\n"
                f"## Description\n"
                f"{body}\n"
                f"{comments_str}"
            )
            return markdown_report

        except Exception as e:
            return f"Error: Exception occurred while contacting GitHub REST API: {str(e)}"

    def _fetch_github_card(self, card_id: str) -> str:
        token = os.environ.get("GITHUB_TOKEN")
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if token:
            headers["Authorization"] = f"token {token}"

        card_url = f"https://api.github.com/projects/columns/cards/{card_id}"
        try:
            r = requests.get(card_url, headers=headers, timeout=15)
            if r.status_code != 200:
                return f"Error: GitHub API returned status code {r.status_code} for project card {card_id}: {r.text}"
            
            card_data = r.json()
            content_url = card_data.get("content_url")
            note = card_data.get("note")

            if content_url:
                # content_url is the direct API URL for the issue or PR
                # e.g. https://api.github.com/repos/owner/repo/issues/123
                ir = requests.get(content_url, headers=headers, timeout=15)
                if ir.status_code == 200:
                    issue_data = ir.json()
                    title = issue_data.get("title", "No Title")
                    body = issue_data.get("body", "No Description")
                    state = issue_data.get("state", "unknown")
                    labels = ", ".join([l.get("name", "") for l in issue_data.get("labels", [])])
                    author = issue_data.get("user", {}).get("login", "unknown")
                    html_url = issue_data.get("html_url", content_url)

                    return (
                        f"# GitHub Project Card #{card_id} (Referenced Issue)\n"
                        f"- **Source URL:** {html_url}\n"
                        f"- **State:** {state}\n"
                        f"- **Author:** @{author}\n"
                        f"- **Labels:** {labels if labels else 'None'}\n\n"
                        f"## Description\n"
                        f"{body}\n"
                    )
            
            if note:
                return (
                    f"# GitHub Project Card #{card_id} (Note)\n"
                    f"- **Content Type:** Note\n\n"
                    f"## Note Content\n"
                    f"{note}\n"
                )

            return f"Error: Project card '{card_id}' does not contain an issue link or text note."

        except Exception as e:
            return f"Error: Exception occurred while fetching GitHub Project card {card_id}: {str(e)}"

    def _handle_jira(self, url: str) -> str:
        # Regex to parse issue key
        # Example: https://my-domain.atlassian.net/browse/PROJ-123
        # Example: https://my-domain.atlassian.net/jira/your-work/browse/PROJ-123
        match = re.search(r"atlassian\.net/(?:.*/)?browse/([A-Z0-9]+-\d+)", url)
        if not match:
            # Fallback regex to capture standard issue key format e.g. PROJ-123
            key_match = re.search(r"([A-Z0-9]+-\d+)", url)
            if key_match:
                issue_key = key_match.group(1)
            else:
                return f"Error: Could not parse Jira issue key from '{url}'. Expected format: https://domain.atlassian.net/browse/PROJ-123"
        else:
            issue_key = match.group(1)

        # Parse Jira domain from URL or fallback to environment
        domain_match = re.search(r"https?://([^/]+)", url)
        jira_domain = domain_match.group(1) if domain_match else os.environ.get("JIRA_DOMAIN")
        if not jira_domain:
            return "Error: Jira domain is missing. Please provide a full Jira URL or set 'JIRA_DOMAIN' in environment variables."

        # Ensure domain starts with protocol if needed, but REST API needs it
        jira_base_url = f"https://{jira_domain}"

        email = os.environ.get("JIRA_EMAIL")
        token = os.environ.get("JIRA_API_TOKEN")

        if not email or not token:
            return "Error: Jira credentials missing. Please set 'JIRA_EMAIL' and 'JIRA_API_TOKEN' in environment variables."

        auth = HTTPBasicAuth(email, token)
        headers = {
            "Accept": "application/json"
        }

        # 1. Dynamically resolve custom field ID for "Acceptance Criteria"
        field_lookup_url = f"{jira_base_url}/rest/api/2/field"
        ac_field_id = None
        ac_field_name = "Acceptance Criteria"
        try:
            fr = requests.get(field_lookup_url, headers=headers, auth=auth, timeout=10)
            if fr.status_code == 200:
                fields_list = fr.json()
                for field in fields_list:
                    name = field.get("name", "").strip().lower()
                    if name == ac_field_name.lower():
                        ac_field_id = field.get("id")
                        break
        except Exception:
            # Ignore and rely on fallback or print warning in final ticket
            pass

        # 2. Fetch the Jira Issue
        issue_url = f"{jira_base_url}/rest/api/2/issue/{issue_key}"
        try:
            r = requests.get(issue_url, headers=headers, auth=auth, timeout=15)
            if r.status_code != 200:
                return f"Error: Jira API returned status code {r.status_code} for issue {issue_key}: {r.text}"

            issue_data = r.json()
            fields = issue_data.get("fields", {})

            summary = fields.get("summary", "No Summary")
            description = fields.get("description", "No Description")
            issue_type = fields.get("issuetype", {}).get("name", "unknown")
            status = fields.get("status", {}).get("name", "unknown")

            # Extract Acceptance Criteria
            acceptance_criteria = "Not Specified"
            if ac_field_id and ac_field_id in fields:
                ac_val = fields.get(ac_field_id)
                if ac_val:
                    acceptance_criteria = str(ac_val)
            else:
                # Secondary search for any customfield that has a name containing "acceptance"
                # in case the exact name match failed but metadata matches
                pass

            # Extract Comments
            comments_str = ""
            comments_data = fields.get("comment", {}).get("comments", [])
            if comments_data:
                comments_str = "\n## Comments\n"
                for idx, c in enumerate(comments_data, 1):
                    author = c.get("author", {}).get("displayName", "unknown")
                    body = c.get("body", "")
                    comments_str += f"### Comment #{idx} by {author}\n{body}\n\n"

            markdown_report = (
                f"# Jira Ticket {issue_key}: {summary}\n"
                f"- **Source URL:** {url}\n"
                f"- **Issue Type:** {issue_type}\n"
                f"- **Status:** {status}\n"
                f"- **Acceptance Criteria:** {acceptance_criteria}\n\n"
                f"## Description\n"
                f"{description}\n"
                f"{comments_str}"
            )
            return markdown_report

        except Exception as e:
            return f"Error: Exception occurred while contacting Jira REST API: {str(e)}"
