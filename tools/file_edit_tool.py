import os
import shutil
from pathlib import Path
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class FileEditInput(BaseModel):
    android_project_path: str = Field(..., description="Absolute path to the Android project root.")
    relative_file_path: str = Field(..., description="Path to the file relative to the Android project root.")
    target_content: str = Field(..., description="The exact block of code in the file that you want to replace.")
    replacement_content: str = Field(..., description="The new block of code to replace the target_content.")

class FileEditTool(BaseTool):
    name: str = "file_edit_tool"
    description: str = (
        "Safely modifies a file in the Android project using search-and-replace. "
        "It takes the exact target code block and replaces it with the replacement code block. "
        "It validates paths, creates a backup (*.bak) before modifying, and ensures the target block "
        "is found exactly once to prevent incorrect edits."
    )
    args_schema: Type[BaseModel] = FileEditInput

    def _run(self, android_project_path: str, relative_file_path: str, target_content: str, replacement_content: str) -> str:
        project_dir = Path(android_project_path).resolve()
        if not project_dir.is_dir():
            return f"Error: android_project_path '{android_project_path}' is not a valid directory."

        if not relative_file_path:
            return "Error: relative_file_path parameter cannot be empty."

        # Resolve path and enforce sandbox boundary
        target_file = (project_dir / relative_file_path).resolve()
        try:
            target_file.relative_to(project_dir)
        except ValueError:
            return f"Security Error: Access denied. File '{relative_file_path}' resolves outside the android project path."

        if not target_file.is_file():
            return f"Error: File '{relative_file_path}' does not exist or is not a file."

        try:
            with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            # Normalise line endings for search consistency
            content_norm = content.replace("\r\n", "\n")
            target_norm = target_content.replace("\r\n", "\n")
            replacement_norm = replacement_content.replace("\r\n", "\n")

            # Check occurrences of target content
            count = content_norm.count(target_norm)
            if count == 0:
                return (
                    f"Error: target_content was not found in '{relative_file_path}'. "
                    "Make sure spelling, whitespace, newlines, and indentation match exactly."
                )
            elif count > 1:
                return (
                    f"Error: target_content occurred {count} times in '{relative_file_path}'. "
                    "Ambiguous search block. Please include more surrounding lines/context."
                )

            # Create backup file
            backup_file = target_file.with_suffix(target_file.suffix + ".bak")
            shutil.copy2(target_file, backup_file)

            # Apply replacement and write back
            new_content = content_norm.replace(target_norm, replacement_norm)
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(new_content)

            return (
                f"Success: File '{relative_file_path}' has been successfully modified.\n"
                f"A backup of the original file was saved to '{backup_file.name}'."
            )

        except Exception as e:
            return f"Error modifying file '{relative_file_path}': {str(e)}"
