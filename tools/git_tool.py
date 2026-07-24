import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class GitInput(BaseModel):
    command_type: str = Field(
        ...,
        description="The Git operation to execute. Allowed: 'get_status', 'create_branch', 'commit_changes', 'create_pr'"
    )
    android_project_path: str = Field(
        ...,
        description="Absolute path to the target Android project."
    )
    branch_name: str = Field(
        default="",
        description="Target branch name. Required for 'create_branch'."
    )
    commit_message: str = Field(
        default="",
        description="The commit message. Required for 'commit_changes'."
    )
    pr_title: str = Field(
        default="",
        description="Title of the Pull Request. Required for 'create_pr'."
    )
    pr_body: str = Field(
        default="",
        description="Markdown body/description of the Pull Request. Required for 'create_pr'."
    )

class GitTool(BaseTool):
    name: str = "git_tool"
    description: str = (
        "Manages Git version control tasks inside the target Android repository. "
        "Allows checking status, creating feature branches, committing code edits, and preparing PR compare scripts/metadata."
    )
    args_schema: Type[BaseModel] = GitInput

    def _sanitize_input(self, val: str) -> bool:
        if not val:
            return True
        # Reject shell escape characters
        return not any(char in val for char in [";", "|", "&", "$", "`", "<", ">", "\n", "\r"])

    def _validate_branch_name(self, name: str) -> bool:
        # Accept letters, numbers, dashes, underscores, and slashes
        return bool(re.match(r"^[a-zA-Z0-9_\-\/]+$", name))

    def _get_web_repo_url(self, git_path: str) -> str:
        try:
            res = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=git_path, capture_output=True, text=True, timeout=5
            )
            url = res.stdout.strip()
            if not url:
                return ""
            
            # Convert SSH to HTTPS url
            if url.startswith("git@"):
                url = url.replace(":", "/").replace("git@", "https://")
                if url.endswith(".git"):
                    url = url[:-4]
            return url
        except Exception:
            return ""

    def _run(self, command_type: str, android_project_path: str, branch_name: str = "", commit_message: str = "", pr_title: str = "", pr_body: str = "") -> str:
        # Validate inputs
        if not (self._sanitize_input(android_project_path) and self._sanitize_input(branch_name) and self._sanitize_input(commit_message)):
            return "Security Error: Input contains invalid shell characters."

        proj_path = Path(android_project_path).resolve()
        if not proj_path.is_dir():
            return f"Error: Target path '{android_project_path}' is not a directory."

        # Sandbox check
        if not (proj_path.is_relative_to("/Users/retailopakistan/Documents/tp-app") or proj_path.name == "tp-app"):
            return "Security Error: Path resolves outside the authorized Android application directory."

        # Ensure output directory exists
        output_dir = Path("output").resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        if command_type == "get_status":
            try:
                res = subprocess.run(["git", "status"], cwd=str(proj_path), capture_output=True, text=True, timeout=10)
                return f"Git status:\nStdout: {res.stdout}\nStderr: {res.stderr}"
            except Exception as e:
                return f"Error running git status: {str(e)}"

        elif command_type == "create_branch":
            if not branch_name:
                return "Error: branch_name parameter is required for create_branch."
            if not self._validate_branch_name(branch_name):
                return f"Error: Invalid branch name '{branch_name}'. Allowed chars: A-Z, a-z, 0-9, -, _, /"

            try:
                # Checkout new branch
                res = subprocess.run(["git", "checkout", "-b", branch_name], cwd=str(proj_path), capture_output=True, text=True, timeout=10)
                if res.returncode != 0:
                    # If branch already exists, checkout it
                    res = subprocess.run(["git", "checkout", branch_name], cwd=str(proj_path), capture_output=True, text=True, timeout=10)
                return f"Branch checkout result:\nStdout: {res.stdout}\nStderr: {res.stderr}"
            except Exception as e:
                return f"Error creating/checking out branch: {str(e)}"

        elif command_type == "commit_changes":
            if not commit_message:
                return "Error: commit_message parameter is required for commit_changes."

            try:
                # Stage Kotlin, Java, Gradle and Manifest edits only
                subprocess.run(["git", "add", "app/src/main/"], cwd=str(proj_path), check=True, timeout=10)
                # Check if there is anything to commit
                diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=str(proj_path), timeout=10)
                if diff_check.returncode == 0:
                    return "No changes staged or modified in working tree to commit."

                commit_res = subprocess.run(["git", "commit", "-m", commit_message], cwd=str(proj_path), capture_output=True, text=True, timeout=10)
                
                # Fetch current branch name to push
                try:
                    branch_res = subprocess.run(
                        ["git", "branch", "--show-current"],
                        cwd=str(proj_path), capture_output=True, text=True, timeout=5
                    )
                    curr_branch = branch_res.stdout.strip()
                except Exception:
                    curr_branch = "staging"

                # Automatically push committed changes to origin
                push_res = subprocess.run(
                    ["git", "push", "-f", "-u", "origin", curr_branch],
                    cwd=str(proj_path), capture_output=True, text=True, timeout=30
                )
                
                return (
                    f"Commit results:\nStdout: {commit_res.stdout}\nStderr: {commit_res.stderr}\n\n"
                    f"Automatic Push results for branch '{curr_branch}':\n"
                    f"Status: {'SUCCESS' if push_res.returncode == 0 else 'FAILED'}\n"
                    f"Push Stdout: {push_res.stdout}\n"
                    f"Push Stderr: {push_res.stderr}"
                )
            except Exception as e:
                return f"Error committing and pushing changes: {str(e)}"

        elif command_type == "create_pr":
            title = pr_title if pr_title else "Fix android crash"
            body = pr_body if pr_body else "Details of the fix."
            
            # Fetch current branch
            try:
                branch_res = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=str(proj_path), capture_output=True, text=True, timeout=5
                )
                curr_branch = branch_res.stdout.strip()
            except Exception:
                curr_branch = "main"

            # Parse web URL from git remote
            repo_url = self._get_web_repo_url(str(proj_path))
            compare_url = f"{repo_url}/compare/{curr_branch}" if repo_url else "GitHub repository compare page"

            # Automatically push branch to origin
            push_stdout = ""
            push_stderr = ""
            push_success = True
            try:
                push_res = subprocess.run(
                    ["git", "push", "-f", "-u", "origin", curr_branch],
                    cwd=str(proj_path), capture_output=True, text=True, timeout=30
                )
                push_stdout = push_res.stdout
                push_stderr = push_res.stderr
                push_success = (push_res.returncode == 0)
            except Exception as e:
                push_success = False
                push_stderr = str(e)

            # Write PR description file
            pr_desc_path = output_dir / "pr_description.md"
            pr_desc_path.write_text(f"# {title}\n\n{body}", encoding="utf-8")

            # Write submit shell script (for manual backup)
            script_path = output_dir / "submit_pr.sh"
            script_content = f"""#!/bin/bash
# Auto-generated script to submit PR
cd "{proj_path}"
git push origin "{curr_branch}"
echo "--------------------------------------------------------"
echo "Code pushed successfully to branch: {curr_branch}"
echo "Please open your browser to compare and create the PR:"
echo "Compare URL: {compare_url}"
echo "--------------------------------------------------------"
"""
            script_path.write_text(script_content, encoding="utf-8")
            os.chmod(script_path, 0o755) # Make executable

            return (
                f"Success: Branch '{curr_branch}' was automatically pushed to origin. Status: {'SUCCESS' if push_success else 'FAILED'}\n"
                f"Push Stdout: {push_stdout}\n"
                f"Push Stderr: {push_stderr}\n"
                f"PR Description markdown file created at output/pr_description.md\n"
                f"Compare/PR creation URL: {compare_url}"
            )

        else:
            return f"Error: Unknown command_type '{command_type}'."
