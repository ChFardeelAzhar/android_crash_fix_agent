import os
import subprocess
from pathlib import Path
from typing import Type, List, Dict, Any
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class AntigravityBridgeInput(BaseModel):
    android_project_path: str = Field(..., description="Absolute path to the Android project root.")
    fix_instruction: str = Field(..., description="Verbatim engineering brief instruction to pass to agy -p.")

class AntigravityBridgeTool(BaseTool):
    name: str = "antigravity_bridge_tool"
    description: str = (
        "Invokes the Antigravity developer CLI 'agy' to automatically investigate, plan, "
        "and edit files within the Android project. Auto-approves permissions and accepts edits."
    )
    args_schema: Type[BaseModel] = AntigravityBridgeInput
    max_execution_time: int = 900

    def _run(self, android_project_path: str, fix_instruction: str) -> str:
        timeout_seconds = 900
        project_dir = Path(android_project_path).resolve()
        if not project_dir.is_dir():
            return f"Error: android_project_path '{android_project_path}' is not a valid directory."

        # Sandbox check (similar to git_tool.py)
        if not (project_dir.is_relative_to("/Users/retailopakistan/Documents/tp-app") or project_dir.name == "tp-app"):
            return "Security Error: Path resolves outside the authorized Android application directory."

        # 1. Capture baseline git state
        baseline_head = ""
        baseline_status = ""
        try:
            head_res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(project_dir), capture_output=True, text=True, timeout=10)
            baseline_head = head_res.stdout.strip()
            status_res = subprocess.run(["git", "status", "--porcelain"], cwd=str(project_dir), capture_output=True, text=True, timeout=10)
            baseline_status = status_res.stdout.strip()
        except Exception as e:
            return f"Error capturing baseline Git status: {str(e)}"

        # 2. Run agy CLI non-interactively
        cmd = [
            "agy",
            "--mode", "accept-edits",
            "--dangerously-skip-permissions",
            "-p", fix_instruction
        ]

        agy_stdout = ""
        agy_stderr = ""
        exit_code = -1
        timed_out = False

        try:
            # We run with shell=False for security, and pass environment variables as is
            # Ensure PAGER=cat is set so it doesn't try to page
            env = os.environ.copy()
            env["PAGER"] = "cat"
            
            res = subprocess.run(
                cmd,
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env
            )
            agy_stdout = res.stdout
            agy_stderr = res.stderr
            exit_code = res.returncode
        except subprocess.TimeoutExpired as te:
            timed_out = True
            agy_stdout = te.stdout or ""
            agy_stderr = te.stderr or ""
        except Exception as e:
            return f"Error executing agy CLI: {str(e)}"

        # 3. Capture post-run git state
        post_status = ""
        diff_stat = ""
        files_changed = []
        try:
            status_res = subprocess.run(["git", "status", "--porcelain"], cwd=str(project_dir), capture_output=True, text=True, timeout=10)
            post_status = status_res.stdout.strip()
            
            diff_res = subprocess.run(["git", "diff", "--stat"], cwd=str(project_dir), capture_output=True, text=True, timeout=10)
            diff_stat = diff_res.stdout.strip()

            # Parse files changed from porcelain git status
            # Lines look like: " M app/src/main/...Kt" or "?? app/src/main/...xml"
            if post_status:
                for line in post_status.splitlines():
                    if len(line) > 3:
                        file_path = line[3:].strip()
                        files_changed.append(file_path)
        except Exception as e:
            return f"Error capturing post-run Git status: {str(e)}"

        # 4. Evaluate success criteria
        # A run is successful if files were actually changed on disk, regardless of exit_code or empty stdout
        success = len(files_changed) > 0 and not timed_out

        result_report = {
            "success": success,
            "exit_code": exit_code,
            "timed_out": timed_out,
            "files_changed": files_changed,
            "diff_stat": diff_stat,
            "agy_stdout_len": len(agy_stdout),
            "agy_stderr_len": len(agy_stderr)
        }

        # Include output details in result representation for the Crew
        output_msg = (
            f"### Antigravity Execution Report\n"
            f"- **Success Status:** {'✅ SUCCESS' if success else '❌ FAILED'}\n"
            f"- **Files Changed:** {', '.join(files_changed) if files_changed else 'None'}\n"
            f"- **Exit Code:** {exit_code}\n"
            f"- **Timed Out:** {timed_out}\n\n"
            f"#### Git Diff Stat:\n"
            f"```\n{diff_stat if diff_stat else 'No diff stat available'}\n```\n\n"
            f"#### CLI Stdout Summary:\n"
            f"```\n{agy_stdout[:2000] if agy_stdout else '(Empty stdout)'}\n"
            f"{'... [Truncated]' if len(agy_stdout) > 2000 else ''}\n```\n"
        )
        
        if agy_stderr:
            output_msg += f"\n#### CLI Stderr Summary:\n```\n{agy_stderr[:1000]}\n```\n"
            
        if not success:
            if timed_out:
                output_msg += f"\n❌ Failure Reason: CLI execution timed out after {timeout_seconds} seconds."
            elif not files_changed:
                output_msg += f"\n❌ Failure Reason: No files were modified on disk. The codebase remained unchanged."

        return output_msg
