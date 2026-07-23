import os
import re
import subprocess
from pathlib import Path
from typing import Type, List
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class GradleVerifyInput(BaseModel):
    android_project_path: str = Field(..., description="Absolute path to the Android project root.")
    tasks: List[str] = Field(
        default=["compileDebugKotlin", "testDebugUnitTest"],
        description="List of Gradle tasks to execute (e.g. ['compileDebugKotlin', 'testDebugUnitTest'])."
    )

class GradleVerifyTool(BaseTool):
    name: str = "gradle_verify_tool"
    description: str = (
        "Executes specified Gradle tasks (such as compilation and unit tests) "
        "inside the Android project to verify code changes. Restricts task names to safe patterns "
        "and handles path-sandboxing securely."
    )
    args_schema: Type[BaseModel] = GradleVerifyInput

    def _run(self, android_project_path: str, tasks: List[str] = None) -> str:
        if tasks is None:
            tasks = ["compileDebugKotlin", "testDebugUnitTest"]

        project_dir = Path(android_project_path).resolve()
        if not project_dir.is_dir():
            return f"Error: android_project_path '{android_project_path}' is not a valid directory."

        # Command Injection Guard: Validate task names
        # Allowed: must start with alphanumeric or colon, followed by alphanumeric, colons, dashes, or dots.
        # This prevents passing command flags (starting with -) as task names.
        task_regex = re.compile(r"^[a-zA-Z0-9:][a-zA-Z0-9:\-\.]*$")
        for task in tasks:
            if not task_regex.match(task):
                return (
                    f"Security Error: Invalid Gradle task name '{task}'. "
                    "Only alphanumeric characters, colons, dashes, and dots are allowed, and it cannot start with a dash."
                )

        # Locate gradlew executable
        is_windows = os.name == "nt"
        gradlew_name = "gradlew.bat" if is_windows else "gradlew"
        gradlew_path = project_dir / gradlew_name

        if not gradlew_path.is_file():
            return f"Error: Gradle wrapper '{gradlew_name}' not found at '{project_dir}'."

        # Ensure execution permissions on Unix
        if not is_windows:
            try:
                os.chmod(gradlew_path, 0o755)
            except Exception as e:
                # Log permission update issue, but continue anyway
                pass

        try:
            # Build command list
            cmd = [str(gradlew_path)] + tasks
            
            # Execute Gradle command
            # Timeout set to 5 minutes (300 seconds) to allow gradle daemon to run
            result = subprocess.run(
                cmd,
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=300
            )

            # Format and truncate stdout and stderr outputs to avoid token limit overflow
            def truncate_log(log_text: str, max_lines: int = 150) -> str:
                if not log_text:
                    return ""
                lines = log_text.splitlines()
                if len(lines) > max_lines:
                    return f"[... truncated {len(lines) - max_lines} lines ...]\n" + "\n".join(lines[-max_lines:])
                return "\n".join(lines)

            truncated_stdout = truncate_log(result.stdout)
            truncated_stderr = truncate_log(result.stderr)

            output = f"Gradle execution finished with exit code {result.returncode}.\n"
            if truncated_stdout:
                output += f"\n--- Standard Output ---\n{truncated_stdout}\n"
            if truncated_stderr:
                output += f"\n--- Standard Error ---\n{truncated_stderr}\n"

            return output

        except subprocess.TimeoutExpired:
            return f"Error: Gradle execution timed out after 300 seconds."
        except Exception as e:
            return f"Error executing Gradle command: {str(e)}"
