import os
import json
import sys
from pathlib import Path

def main():
    # 2. Load the project path
    android_project_path = "/Users/retailopakistan/Documents/tp-app"
    
    # Check for CLI arguments first
    if len(sys.argv) >= 4:
        source_type = sys.argv[1]
        source_value = sys.argv[2]
        android_project_path = sys.argv[3]
    elif len(sys.argv) >= 3:
        source_type = sys.argv[1]
        source_value = sys.argv[2]
    else:
        # Fallback to inputs/crash.txt for backward compatibility
        crash_file = Path("inputs/crash.txt")
        if crash_file.is_file():
            print(f"Reading backward-compatibility raw text context from '{crash_file}'...")
            try:
                source_value = crash_file.read_text(encoding="utf-8", errors="replace")
                source_type = "raw_text"
            except Exception as e:
                print(f"Error reading crash file: {e}")
                sys.exit(1)
        else:
            print("Error: No CLI arguments provided and 'inputs/crash.txt' was not found.")
            print("Usage: python run.py [source_type] [source_value] [optional_project_path]")
            print("Supported source_types: 'github_issue', 'jira', 'raw_text'")
            sys.exit(1)

    # If project path wasn't overridden by 3rd CLI arg, load from crew.jsonc
    if len(sys.argv) < 4:
        crew_jsonc_path = Path("crew.jsonc")
        if crew_jsonc_path.is_file():
            try:
                # Strip comments and parse JSON
                content = ""
                with open(crew_jsonc_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("//"):
                            continue
                        content += line
                data = json.loads(content)
                if "inputs" in data and "android_project_path" in data["inputs"]:
                    android_project_path = data["inputs"]["android_project_path"]
            except Exception as e:
                print(f"Warning: Failed to parse crew.jsonc: {e}. Using default project path.")

    # Ensure non-interactive daemon mode (bypasses Textual TUI)
    os.environ["CREWAI_DMN"] = "1"

    # 3. Assemble inputs dictionary
    inputs_dict = {
        "source_type": source_type,
        "source_value": source_value,
        "android_project_path": android_project_path
    }

    inputs_json = json.dumps(inputs_dict)

    # 4. Invoke run_crew from crewai_cli
    try:
        from crewai_cli.run_crew import run_crew
        print(f"Launching CrewAI with source_type: {source_type}")
        print(f"Target project path: {android_project_path}")
        run_crew(inputs=inputs_json)
    except ImportError:
        # Fallback for alternative crewai-cli configurations
        try:
            from crewai.cli.cli import run_crew
            print(f"Launching CrewAI with source_type: {source_type}")
            print(f"Target project path: {android_project_path}")
            run_crew(inputs=inputs_json)
        except Exception as e:
            print(f"Error importing crewai CLI: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"Error running crew: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
