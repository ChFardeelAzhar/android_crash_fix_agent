import os
from pathlib import Path
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class ProjectSearchInput(BaseModel):
    android_project_path: str = Field(..., description="Absolute path to the Android project root.")
    query: str = Field(..., description="String query or class name to search for in files.")
    max_matches: int = Field(default=30, description="Maximum number of match occurrences to return.")

class ProjectSearchTool(BaseTool):
    name: str = "project_search_tool"
    description: str = (
        "Searches for a query string in source files (.kt, .java, .xml, .gradle, .kts, AndroidManifest.xml) "
        "within the target Android project path. Returns relative paths, line numbers, and matching lines. "
        "Skips build, .gradle, .git, .idea, and node_modules."
    )
    args_schema: Type[BaseModel] = ProjectSearchInput

    def _run(self, android_project_path: str, query: str, max_matches: int = 30) -> str:
        project_dir = Path(android_project_path).resolve()
        if not project_dir.is_dir():
            return f"Error: android_project_path '{android_project_path}' is not a valid directory."

        if not query:
            return "Error: query parameter cannot be empty."

        allowed_extensions = {".kt", ".java", ".xml", ".gradle", ".kts"}
        ignored_dirs = {"build", ".gradle", ".git", ".idea", "node_modules"}

        matches = []
        truncated = False
        query_lower = query.lower()

        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]

            for file in files:
                file_path = Path(root) / file
                try:
                    file_path.resolve().relative_to(project_dir)
                except ValueError:
                    continue

                if file_path.suffix in allowed_extensions or file_path.name == "AndroidManifest.xml":
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                            for line_idx, line in enumerate(f, 1):
                                if query_lower in line.lower():
                                    rel_path = file_path.relative_to(project_dir)
                                    # Truncate long matching lines to avoid token pollution
                                    line_content = line.strip()
                                    if len(line_content) > 160:
                                        line_content = line_content[:160] + "..."
                                    matches.append((str(rel_path), line_idx, line_content))
                                    if len(matches) >= max_matches:
                                        truncated = True
                                        break
                    except Exception:
                        pass
                if truncated:
                    break
            if truncated:
                break

        if not matches:
            return f"No matches found for query '{query}' in project source files."

        result = f"Search results for '{query}' (max {max_matches}):\n"
        for rel_path, line_num, content in matches:
            result += f"- {rel_path}:{line_num}: {content}\n"

        if truncated:
            result += f"\n[Warning: Search results truncated to first {max_matches} matches.]"
        return result
