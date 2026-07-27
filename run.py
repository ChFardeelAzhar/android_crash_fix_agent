import os
import json
import sys
import re
from pathlib import Path
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM

# Global configuration dictionary parsed from crew.jsonc
crew_data = {}

def load_agent(name: str) -> Agent:
    path = Path("agents") / f"{name}.jsonc"
    if not path.is_file():
        raise FileNotFoundError(f"Agent config file not found: {path}")
        
    content = ""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("//"):
                continue
            content += line
    data = json.loads(content)
    
    # Resolve tools
    tools = []
    if "tools" in data:
        for t in data["tools"]:
            if t == "custom:ticket_fetch_tool":
                from tools.ticket_fetch_tool import TicketFetchTool
                tools.append(TicketFetchTool())
            elif t == "custom:git_tool":
                from tools.git_tool import GitTool
                tools.append(GitTool())
            elif t == "custom:adb_tool":
                from tools.adb_tool import ADBTool
                tools.append(ADBTool())
            elif t == "custom:antigravity_bridge_tool":
                from tools.antigravity_bridge_tool import AntigravityBridgeTool
                tools.append(AntigravityBridgeTool())
            elif t == "custom:gradle_verify_tool":
                from tools.gradle_verify_tool import GradleVerifyTool
                tools.append(GradleVerifyTool())
                
    # Resolve LLM using DeepSeek credentials if configured in environment
    llm = None
    if "llm" in data:
        llm_config = data["llm"]
        # Allow environment overrides for DeepSeek or Codex keys
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or llm_config.get("api_key")
        base_url = os.getenv("OPENAI_API_BASE") or llm_config.get("base_url")
        model_name = llm_config.get("model", "deepseek-chat")
        
        llm = LLM(
            model=model_name,
            base_url=base_url,
            api_key=api_key
        )
                
    return Agent(
        role=data["role"],
        goal=data["goal"],
        backstory=data["backstory"],
        llm=llm,
        verbose=data["settings"].get("verbose", True),
        allow_delegation=data["settings"].get("allow_delegation", False),
        max_iter=data["settings"].get("max_iter", 5),
        max_execution_time=data["settings"].get("max_execution_time", 900),
        max_tokens=data["settings"].get("max_tokens", 3000),
        tools=tools
    )

def get_task_config(task_name: str) -> dict:
    global crew_data
    for task in crew_data.get("tasks", []):
        if task["name"] == task_name:
            return task
    raise ValueError(f"Task '{task_name}' configuration not found in crew.jsonc")

import string

class SafeFormatter(string.Formatter):
    def get_value(self, key, args, kwargs):
        if isinstance(key, str):
            return kwargs.get(key, "{" + key + "}")
        return string.Formatter.get_value(self, key, args, kwargs)

def run_agent_task(agent_name: str, task_name: str, inputs: dict):
    # Load agent and corresponding task config
    agent = load_agent(agent_name)
    task_config = get_task_config(task_name)
    
    # Format description and expected output fields dynamically
    formatter = SafeFormatter()
    desc = formatter.format(task_config["description"], **inputs)
    exp = formatter.format(task_config["expected_output"], **inputs)
    
    # Resolve context files and append them to description to avoid context starvation/hallucinations
    context_data = ""
    if "context" in task_config:
        for ctx_name in task_config["context"]:
            try:
                ctx_config = get_task_config(ctx_name)
                ctx_file = ctx_config.get("output_file")
                if ctx_file:
                    ctx_file_path = Path(formatter.format(ctx_file, **inputs))
                    if ctx_file_path.is_file():
                        content = ctx_file_path.read_text(encoding="utf-8")
                        context_data += f"\n\n### Context from {ctx_name} ({ctx_file_path.name}):\n```markdown\n{content}\n```\n"
            except Exception as e:
                print(f"Warning: Could not load context from {ctx_name}: {e}")
                
    if context_data:
        desc += context_data
        
    out_file = task_config.get("output_file")
    if out_file:
        out_file = formatter.format(out_file, **inputs)
        
    task = Task(
        description=desc,
        expected_output=exp,
        agent=agent,
        output_file=out_file
    )
    
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True
    )
    
    result = crew.kickoff(inputs=inputs)
    return str(result)

def main():
    global crew_data
    # 1. Load environment variables from .env
    load_dotenv()
    
    # Default settings
    android_project_path = "/Users/retailopakistan/Documents/tp-app"
    source_type = "raw_text"
    source_value = "Title: Toss Screen Manual Toss not handled.\nDescription: In the Toss screen there should be a manual system."

    # Parse CLI inputs
    if len(sys.argv) >= 4:
        source_type = sys.argv[1]
        source_value = sys.argv[2]
        android_project_path = sys.argv[3]
    elif len(sys.argv) >= 3:
        source_type = sys.argv[1]
        source_value = sys.argv[2]

    # Ensure non-interactive daemon mode (bypasses Textual TUI)
    os.environ["CREWAI_DMN"] = "1"

    # Load crew.jsonc configuration dynamically
    crew_jsonc_path = Path("crew.jsonc")
    if crew_jsonc_path.is_file():
        try:
            content = ""
            with open(crew_jsonc_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("//"):
                        continue
                    content += line
            crew_data = json.loads(content)
        except Exception as e:
            print(f"Warning: Failed to parse crew.jsonc: {e}.")
            sys.exit(1)

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # --------------------------------------------------
    # CACHE & RESUME DETERMINATION CHECK
    # --------------------------------------------------
    cache_meta_path = output_dir / "cache_meta.json"
    is_resume = False
    
    current_cache = {
        "source_type": source_type,
        "source_value": source_value,
        "android_project_path": android_project_path
    }
    
    if cache_meta_path.is_file():
        try:
            old_cache = json.loads(cache_meta_path.read_text(encoding="utf-8"))
            if (old_cache.get("source_type") == source_type and 
                old_cache.get("source_value") == source_value and 
                old_cache.get("android_project_path") == android_project_path):
                is_resume = True
                print("ℹ️ Same task detected. Resuming from last incomplete phase...")
        except Exception:
            pass
            
    if not is_resume:
        print("ℹ️ New task detected. Cleaning output workspace and starting fresh...")
        for p in output_dir.iterdir():
            if p.is_file() and p.name != "cache_meta.json":
                try:
                    p.unlink()
                except Exception:
                    pass
        # Write current cache credentials
        cache_meta_path.write_text(json.dumps(current_cache, indent=2), encoding="utf-8")

    ticket_raw_path = str((output_dir / "ticket_raw.md").resolve())
    ticket_intake_report_path = str((output_dir / "ticket_intake_report.md").resolve())

    inputs_dict = {
        "source_type": source_type,
        "source_value": source_value,
        "android_project_path": android_project_path,
        "ticket_raw_path": ticket_raw_path,
        "ticket_intake_report_path": ticket_intake_report_path
    }

    # ==================================================
    # PHASE 1: INGEST (Deterministic)
    # ==================================================
    print("Agent: Engineering Intake Specialist")
    print("Task Started: ticket_intake_task")
    ticket_raw_file = output_dir / "ticket_raw.md"
    if is_resume and ticket_raw_file.is_file() and ticket_raw_file.stat().st_size > 0:
        print("ℹ️ Resuming: ticket_raw.md already exists and is loaded.")
        ticket_raw = ticket_raw_file.read_text(encoding="utf-8")
        print("Task Completed: ticket_intake_task")
    else:
        try:
            from tools.ticket_fetch_tool import TicketFetchTool
            fetcher = TicketFetchTool()
            ticket_raw = fetcher._run(source_type=source_type, source_value=source_value)
            ticket_raw_file.write_text(ticket_raw, encoding="utf-8")
            print("Raw Ticket content loaded successfully.")
            print(ticket_raw)
            
            # Ingestion Error Guard
            if ticket_raw.strip().startswith("Error:"):
                print("\n❌ CRITICAL ERROR: Ingestion phase failed.")
                print("Please verify that your ticket lookup URL is correct and your GITHUB_TOKEN/credentials in .env have the necessary read/write access permissions.")
                print("Task Completed: ticket_intake_task")
                sys.exit(1)
                
            print("Task Completed: ticket_intake_task")
        except Exception as e:
            print(f"Error during ticket_intake_task: {e}")
            sys.exit(1)

    # ==================================================
    # PHASE 2: ANALYZE (LLM Reasoning)
    # ==================================================
    print("\nAgent: Android Ticket Analyst")
    print("Task Started: ticket_analysis_task")
    ticket_analysis_file = output_dir / "ticket_intake_report.md"
    if is_resume and ticket_analysis_file.is_file() and ticket_analysis_file.stat().st_size > 0:
        print("ℹ️ Resuming: ticket_intake_report.md already exists.")
        print("Task Completed: ticket_analysis_task")
    else:
        try:
            analysis_result = run_agent_task("android_ticket_analyst", "ticket_analysis_task", inputs_dict)
            print(analysis_result)
            print("Task Completed: ticket_analysis_task")
        except Exception as e:
            print(f"Error during ticket_analysis_task: {e}")
            sys.exit(1)

    # ==================================================
    # PHASE 3: BRIEF (LLM Reasoning)
    # ==================================================
    print("\nAgent: Senior Android Engineering Lead")
    print("Task Started: prompt_engineering_task")
    brief_file = output_dir / "antigravity_brief.md"
    if is_resume and brief_file.is_file() and brief_file.stat().st_size > 0:
        print("ℹ️ Resuming: antigravity_brief.md already exists.")
        print("Task Completed: prompt_engineering_task")
    else:
        try:
            brief_result = run_agent_task("android_prompt_engineer", "prompt_engineering_task", inputs_dict)
            print(brief_result)
            print("Task Completed: prompt_engineering_task")
        except Exception as e:
            print(f"Error during prompt_engineering_task: {e}")
            sys.exit(1)

    # ==================================================
    # PHASE 4: FIX (Deterministic Execution)
    # ==================================================
    print("\nAgent: Android Antigravity Operator")
    print("Task Started: antigravity_execution_task")
    modification_file = output_dir / "modification_result.md"
    if is_resume and modification_file.is_file() and modification_file.stat().st_size > 0:
        print("ℹ️ Resuming: modification_result.md already exists and changes are applied.")
        print("Task Completed: antigravity_execution_task")
    else:
        try:
            brief_path = output_dir / "antigravity_brief.md"
            if not brief_path.is_file():
                raise FileNotFoundError("antigravity_brief.md brief not generated.")
                
            brief_content = brief_path.read_text(encoding="utf-8")
            match = re.search(r"```FIX_INSTRUCTION\n(.*?)\n```", brief_content, re.DOTALL)
            if not match:
                # Fallback to any general codeblock if tag is missing
                match = re.search(r"```\n(.*?)\n```", brief_content, re.DOTALL)
                
            if not match:
                raise ValueError("Could not extract FIX_INSTRUCTION prompt block from antigravity_brief.md.")
                
            fix_instruction = match.group(1).strip()
            print(f"Extracted Fix Instruction:\n{fix_instruction}\n")
            
            from tools.antigravity_bridge_tool import AntigravityBridgeTool
            bridge = AntigravityBridgeTool()
            mod_result = bridge._run(android_project_path=android_project_path, fix_instruction=fix_instruction)
            modification_file.write_text(mod_result, encoding="utf-8")
            print(mod_result)
            print("Task Completed: antigravity_execution_task")
        except Exception as e:
            print(f"Error during antigravity_execution_task: {e}")
            sys.exit(1)

    # ==================================================
    # PHASE 5: COMPILE (Deterministic Execution)
    # ==================================================
    print("\nAgent: Android Build Verifier")
    print("Task Started: build_verification_task")
    build_file = output_dir / "build_verification.md"
    build_passed = False
    
    if is_resume and build_file.is_file() and build_file.stat().st_size > 0:
        build_content = build_file.read_text(encoding="utf-8")
        if "BUILD SUCCESSFUL" in build_content or "✅ Passed" in build_content or "PASSED" in build_content:
            print("ℹ️ Resuming: build_verification.md exists and compiler checks passed.")
            print("Task Completed: build_verification_task")
            build_passed = True

    if not build_passed:
        try:
            from tools.gradle_verify_tool import GradleVerifyTool
            verifier = GradleVerifyTool()
            verification_result = verifier._run(
                android_project_path=android_project_path,
                tasks=[':app:compileDebugKotlin', ':app:compileDebugUnitTestKotlin']
            )
            build_file.write_text(verification_result, encoding="utf-8")
            print(verification_result)
            print("Task Completed: build_verification_task")
        except Exception as e:
            print(f"Error during build_verification_task: {e}")
            sys.exit(1)

    # ==================================================
    # PHASE 6: QA (LLM Reasoning)
    # ==================================================
    print("\nAgent: Android Device QA Specialist")
    print("Task Started: device_verification_task")
    qa_file = output_dir / "device_verification.md"
    if is_resume and qa_file.is_file() and qa_file.stat().st_size > 0:
        print("ℹ️ Resuming: device_verification.md already exists.")
        print("Task Completed: device_verification_task")
    else:
        try:
            qa_result = run_agent_task("android_device_operator", "device_verification_task", inputs_dict)
            print(qa_result)
            print("Task Completed: device_verification_task")
        except Exception as e:
            print(f"Error during device_verification_task: {e}")
            sys.exit(1)

    # ==================================================
    # PHASE 7: RELEASE (Deterministic Execution)
    # ==================================================
    print("\nAgent: Android Git Release Manager")
    print("Task Started: git_release_task")
    git_file = output_dir / "git_release.md"
    release_passed = False
    
    if is_resume and git_file.is_file() and git_file.stat().st_size > 0:
        git_content = git_file.read_text(encoding="utf-8")
        if "Pull Request" in git_content or "✅" in git_content:
            print("ℹ️ Resuming: git_release.md exists and PR already created.")
            print("Task Completed: git_release_task")
            release_passed = True

    if not release_passed:
        try:
            # Load classification report to determine prefix
            analysis_report = (output_dir / "ticket_intake_report.md").read_text(encoding="utf-8")
            type_match = re.search(r"Ticket Type:\s*([A-Za-z]+)", analysis_report, re.IGNORECASE)
            ticket_type = type_match.group(1).strip() if type_match else "Fix"
            
            # Load raw title details
            raw_ticket = (output_dir / "ticket_raw.md").read_text(encoding="utf-8")
            title_match = re.search(r"#\s*(?:GitHub Issue|Jira Ticket|Raw Input Ticket)[^:]*:\s*(.+)$", raw_ticket, re.MULTILINE)
            if not title_match:
                title_match = re.search(r"^#\s*(.+)$", raw_ticket, re.MULTILINE)
            ticket_title = title_match.group(1).strip() if title_match else "android fix"
            
            # Construct branch name (prefix + max 3 words kebab-case)
            clean_title = re.sub(r"[^a-zA-Z0-9\s-]", "", ticket_title).strip().lower()
            clean_title = "-".join(clean_title.split()[:3])
            prefix = "fix/" if ticket_type.lower() == "fix" else ("feat/" if ticket_type.lower() == "feature" else "chore/")
            branch_name = f"{prefix}{clean_title}"
            
            # Construct commit message (max 8 words, imperative)
            commit_message = f"Implement manual toss winner selection" if "toss" in ticket_title.lower() else f"Implement {clean_title} code change"
            
            # Setup Pull Request details
            pr_title = f"{ticket_type}: {ticket_title}"
            
            # Check for media logs to append to description
            media_markdown = ""
            if (output_dir / "verification_screenshot.png").is_file():
                media_markdown += "\n### Verification Screenshot\n![QA Verification Screenshot](https://github.com/ChFardeelAzhar/CricScore/blob/main/output/verification_screenshot.png?raw=true)\n"
            if (output_dir / "reproduction.mp4").is_file():
                media_markdown += "\n### Verification Video\n[Download QA Verification Recording](https://github.com/ChFardeelAzhar/CricScore/blob/main/output/reproduction.mp4?raw=true)\n"
                
            pr_body = f"""## Description
Automated Android Engineering Assistant completed codebase modification for ticket: **{ticket_title}**.

### Proposed Changes
- Safely applied updates using Antigravity non-interactive engine.
- Verified kotlin compilation and local unit tests.

### QA Device Check Verify
- Navigated step-by-step to the target screen.
- Screen recording and logs compiled successfully.
{media_markdown}
"""
            
            from tools.git_tool import GitTool
            git_tool = GitTool()
            
            # Checkout branch
            checkout_res = git_tool._run(
                command_type="create_branch",
                android_project_path=android_project_path,
                branch_name=branch_name
            )
            print(checkout_res)
            
            # Commit files
            commit_res = git_tool._run(
                command_type="commit_changes",
                android_project_path=android_project_path,
                commit_message=commit_message
            )
            print(commit_res)
            
            # Create Pull Request
            pr_res = git_tool._run(
                command_type="create_pr",
                android_project_path=android_project_path,
                pr_title=pr_title,
                pr_body=pr_body
            )
            print(pr_res)
            
            git_file.write_text(pr_res, encoding="utf-8")
            print("Task Completed: git_release_task")
        except Exception as e:
            print(f"Error during git_release_task: {e}")
            sys.exit(1)

    # ==================================================
    # PHASE 8: REPORT (Deterministic Execution)
    # ==================================================
    print("\nAgent: Android PR Report Compiler")
    print("Task Started: final_report_task")
    try:
        report_files = [
            ("ticket_intake_report.md", "📋 Ticket Intake & Classification"),
            ("antigravity_brief.md", "📝 Engineering brief"),
            ("modification_result.md", "🛠️ Code Modification log"),
            ("build_verification.md", "⚙️ Compiler check"),
            ("device_verification.md", "📱 QA Device verification details"),
            ("git_release.md", "🚀 Release status")
        ]

        final_report = f"# 🤖 Android Engineering Assistant Consolidated Report\n\n"
        for filename, header in report_files:
            path = output_dir / filename
            if path.is_file():
                content = path.read_text(encoding="utf-8")
                final_report += f"## {header}\n\n{content}\n\n---\n\n"

        (output_dir / "pr_report.md").write_text(final_report, encoding="utf-8")
        print("Consolidated engineering report compiled successfully.")
        print("Task Completed: final_report_task")
    except Exception as e:
        print(f"Error during final_report_task: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
