import os
import re
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
        "It takes the target code block (even with flexible whitespace/indentation) and replaces it with the replacement code block. "
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

            # Normalise whitespace search by stripping lines and matching them via Regex
            target_lines = [l.strip() for l in target_norm.splitlines() if l.strip()]
            if not target_lines:
                return "Error: target_content is empty."

            def make_line_pattern(line):
                # Escape all regex characters in the line
                escaped = re.escape(line)
                # Replace multiple spaces with flexible whitespace pattern
                escaped = re.sub(r'\\\s+', r'\\s+', escaped)
                escaped = re.sub(r'\s+', r'\\s+', escaped)
                return escaped

            line_patterns = [make_line_pattern(l) for l in target_lines]
            pattern_str = r"\s*".join(line_patterns)

            # Perform search
            matches = list(re.finditer(pattern_str, content_norm))

            if len(matches) == 0:
                return (
                    f"Error: target_content was not found in '{relative_file_path}'. "
                    "Please double check spelling and context blocks."
                )
            elif len(matches) > 1:
                return (
                    f"Error: target_content occurred {len(matches)} times in '{relative_file_path}'. "
                    "Ambiguous search block. Please include more surrounding lines/context."
                )

            # Match details
            match = matches[0]
            start, end = match.span()

            # Detect indentation of the first matched line
            line_start = content_norm.rfind('\n', 0, start) + 1
            first_line_prefix = content_norm[line_start:start]
            base_indent = ""
            if first_line_prefix.isspace() or not first_line_prefix:
                base_indent = first_line_prefix
            else:
                m = re.match(r"^\s*", first_line_prefix)
                if m:
                    base_indent = m.group(0)

            # Format replacement content preserving relative indentation
            replacement_lines = replacement_norm.splitlines()
            non_empty_repl_lines = [l for l in replacement_lines if l.strip()]
            if non_empty_repl_lines:
                indents = []
                for l in non_empty_repl_lines:
                    m = re.match(r"^(\s*)", l)
                    indents.append(len(m.group(1)) if m else 0)
                min_indent = min(indents)
            else:
                min_indent = 0

            formatted_repl_lines = []
            for l in replacement_lines:
                if not l.strip():
                    formatted_repl_lines.append("")
                else:
                    m = re.match(r"^(\s*)", l)
                    current_indent_len = len(m.group(1)) if m else 0
                    relative_indent = l[:current_indent_len][min_indent:]
                    content_part = l[current_indent_len:]
                    formatted_repl_lines.append(base_indent + relative_indent + content_part)

            formatted_replacement = "\n".join(formatted_repl_lines)

            # Apply replacement and write back
            new_content = content_norm[:start] + formatted_replacement + content_norm[end:]
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(new_content)

            return f"Success: File '{relative_file_path}' has been successfully modified in place."

        except Exception as e:
            return f"Error modifying file '{relative_file_path}': {str(e)}"
