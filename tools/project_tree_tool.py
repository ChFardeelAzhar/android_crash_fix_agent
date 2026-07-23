import os
from pathlib import Path
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class ProjectTreeInput(BaseModel):
    android_project_path: str = Field(..., description="Absolute path to the Android project root.")
    max_files: int = Field(default=120, description="Maximum number of files to return to avoid token overflow.")

class ProjectTreeTool(BaseTool):
    name: str = "project_tree_tool"
    description: str = (
        "Recursively lists all relevant source files (Kotlin, Java, XML, Gradle, AndroidManifest.xml) "
        "in the target Android project directory. Skips build, .gradle, .git, .idea, and node_modules."
    )
    args_schema: Type[BaseModel] = ProjectTreeInput

    def _run(self, android_project_path: str, max_files: int = 120) -> str:
        # Validate path
        project_dir = Path(android_project_path).resolve()
        if not project_dir.is_dir():
            return f"Error: android_project_path '{android_project_path}' is not a valid directory."

        allowed_extensions = {".kt", ".java", ".xml", ".gradle", ".kts"}
        ignored_dirs = {"build", ".gradle", ".git", ".idea", "node_modules"}

        files_found = []
        truncated = False

        for root, dirs, files in os.walk(project_dir):
            # Prune directory search in-place to avoid entering ignored or dot directories
            dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]

            for file in files:
                file_path = Path(root) / file
                # Guard against any path traversal issues
                try:
                    file_path.resolve().relative_to(project_dir)
                except ValueError:
                    continue  # Resolved path escapes project root, skip it

                if file_path.suffix in allowed_extensions or file_path.name == "AndroidManifest.xml":
                    rel_path = file_path.relative_to(project_dir)
                    files_found.append(str(rel_path))
                    if len(files_found) >= max_files:
                        truncated = True
                        break
            if truncated:
                break

        if not files_found:
            return f"No relevant source files found in {android_project_path}."

        result = "Relevant project files:\n" + "\n".join(f"- {f}" for f in files_found)
        if truncated:
            result += f"\n\n[Warning: File list truncated to first {max_files} files to prevent token limit overflow.]"
        return result
