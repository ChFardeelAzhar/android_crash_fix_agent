import os
import json
import sys
from pathlib import Path

def main():
    # 1. Read the crash log from inputs/crash.txt
    crash_file = Path("inputs/crash.txt")
    if not crash_file.is_file():
        print(f"Error: Crash file '{crash_file}' not found!")
        print("Please place your crash log text in 'inputs/crash.txt' and run again.")
        sys.exit(1)

    print(f"Reading crash context from '{crash_file}'...")
    try:
        crash_context = crash_file.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"Error reading crash file: {e}")
        sys.exit(1)

    # 2. Load the project path from crew.jsonc inputs
    android_project_path = "/Users/retailopakistan/Documents/tp-app"
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

    # 3. Assemble inputs dictionary
    inputs_dict = {
        "raw_crash_context": crash_context,
        "android_project_path": android_project_path
    }

    inputs_json = json.dumps(inputs_dict)

    # 4. Invoke run_crew from crewai_cli
    try:
        from crewai_cli.run_crew import run_crew
        print(f"Launching CrewAI with target project: {android_project_path}")
        print("Bypassing manual console input prompts...")
        run_crew(inputs=inputs_json)
    except ImportError:
        # Fallback for alternative crewai-cli configurations
        try:
            from crewai.cli.cli import run_crew
            print(f"Launching CrewAI with target project: {android_project_path}")
            print("Bypassing manual console input prompts...")
            run_crew(inputs=inputs_json)
        except Exception as e:
            print(f"Error importing crewai CLI: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"Error running crew: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
