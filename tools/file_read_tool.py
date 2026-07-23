import os
from pathlib import Path
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class FileReadInput(BaseModel):
    android_project_path: str = Field(..., description="Absolute path to the Android project root.")
    relative_file_path: str = Field(..., description="Path to the file relative to the Android project root.")
    max_lines: int = Field(default=220, description="Maximum number of lines to read to avoid token overflow.")

class FileReadTool(BaseTool):
    name: str = "file_read_tool"
    description: str = (
        "Reads the contents of a specific file inside the Android project. "
        "Accepts a relative file path and returns the content with line numbers. "
        "Will reject reads that try to escape the project directory."
    )
    args_schema: Type[BaseModel] = FileReadInput

    def _run(self, android_project_path: str, relative_file_path: str, max_lines: int = 220) -> str:
        project_dir = Path(android_project_path).resolve()
        if not project_dir.is_dir():
            return f"Error: android_project_path '{android_project_path}' is not a valid directory."

        if not relative_file_path:
            return "Error: relative_file_path parameter cannot be empty."

        # Resolve path to handle parent directory traversal or absolute paths
        target_file = (project_dir / relative_file_path).resolve()

        # Enforce that the target file must reside strictly inside the target project directory
        try:
            target_file.relative_to(project_dir)
        except ValueError:
            return f"Security Error: Access denied. File '{relative_file_path}' resolves outside the android project path."

        if not target_file.is_file():
            return f"Error: File '{relative_file_path}' does not exist or is not a file."

        try:
            lines = []
            truncated = False
            with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                for idx, line in enumerate(f, 1):
                    lines.append(f"{idx}: {line.rstrip()}")
                    if idx >= max_lines:
                        truncated = True
                        break

            output = f"File: {relative_file_path} ({len(lines)} lines shown):\n" + "\n".join(lines)
            if truncated:
                output += f"\n\n[Warning: File truncated to first {max_lines} lines to prevent token limit overflow.]"
            return output
        except Exception as e:
            return f"Error reading file '{relative_file_path}': {str(e)}"
