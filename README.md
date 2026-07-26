# Android Crash-Fix Assistant (`android_crash_fix_agent`)

A CrewAI project utilizing the JSONC-first project structure to analyze Android crashes and perform secure codebase search, planning, and in-place code modifications leveraging the **Antigravity developer CLI (`agy`)**.

## Project Purpose & Capabilities

This assistant is designed to streamline Android crash debugging in distinct phases. It currently implements:

*   **Crash Intake Analysis**: Parses raw crash logs (from Firebase Crashlytics or Logcat) to extract exception types, stack trace markers, affected architecture layers, severity, and device/OS clues.
*   **Prompt Engineering Brief**: Generates a detailed natural-language work brief and instructions block containing code constraints (lifecycle safety, minimal changes) and context.
*   **Antigravity Execution**: Invokes the Antigravity developer CLI (`agy`) via a custom bridge tool to perform codebase investigation, fix planning, and target file editing in a single autonomous step.
*   **Gradle Build & Test Verification**: Runs secure compile and unit test commands using `./gradlew` to ensure modifications compile and pass tests.
*   **ADB Device Reproduction**: Lists active emulators/devices, queries logcat buffers for crash clues, launches target activities, and captures execution screenshots to document verification results.
*   **PR Report Compilation**: Bundles the findings, fix details, compile status, and screenshot verification into a PR description template for developers.

### Safety Guardrails
*   **CLI Sandboxing**: Runs `agy` within a restricted subdirectory to protect system security.
*   **Command Sanitization**: Rejects any inputs to Gradle/ADB tools containing shell command separators or arbitrary execution flags.
*   **Path Sandboxing**: Custom tools enforce strict parent-directory validation to reject any paths resolving outside the target Android project directory.

---

## Project Structure

```text
android_crash_fix_agent/
├── agents/
│   ├── android_crash_analyst.jsonc             # Parses raw crash context
│   ├── android_prompt_engineer.jsonc           # Writes the engineering brief
│   ├── android_antigravity_operator.jsonc      # Invokes Antigravity bridge tool
│   ├── android_build_verifier.jsonc            # Runs compilation checks
│   ├── android_device_operator.jsonc           # Runs ADB testing
│   ├── android_git_release_manager.jsonc       # Commits and pushes branch
│   └── android_pr_report_compiler.jsonc        # Aggregates PR documentation
├── tools/
│   ├── __init__.py
│   ├── antigravity_bridge_tool.py              # Invokes agy CLI to search, plan, & edit
│   ├── gradle_verify_tool.py                   # Securely runs gradle compilation and unit tests
│   ├── adb_tool.py                             # Safely manages adb device reproduction & capture
│   └── git_tool.py                             # Manages branch creation, commits, and remote push
├── crew.jsonc                                  # Crew orchestrator, task list, and inputs
├── .env                                        # Environment variables (DeepSeek keys, etc.)
├── pyproject.toml                              # Dependencies configuration
└── README.md                                   # Project documentation
```

---

## Running the Crew

To run the assistant, configure your environment and run the CrewAI command:

1.  **Configure Environment**: Add your keys to the `.env` file:
    ```env
    DEEPSEEK_API_KEY=your_key_here
    OPENAI_API_KEY=your_key_here
    OPENAI_API_BASE=https://api.deepseek.com
    ANTIGRAVITY_TOKEN=your_token_here (if needed)
    ```
2.  **Define Inputs**: Set the inputs in `crew.jsonc` or pass them when running. The crew accepts:
    *   `raw_crash_context`: The raw crash trace or Firebase Crashlytics text.
    *   `android_project_path`: Absolute path to your Android application directory (e.g., `/Users/retailopakistan/Documents/tp-app`).
3.  **Execute**:
    ```bash
    uv run run.py
    ```

---

## Generated Reports (`output/`)

Upon completion, markdown reports are written to the `output/` directory:

1.  `output/crash_intake_report.md`: Structured breakdown of the crash type, stack trace location, severity, and confirmed facts.
2.  `output/antigravity_brief.md`: Prompt engineering work order containing the `FIX_INSTRUCTION` block.
3.  `output/modification_result.md`: Results of the Antigravity execution, showing exit codes, files changed, and git diff stat.
4.  `output/pr_report.md`: Final review-ready report with PR description, manual QA verification screenshot paths, build/test status, risk level, and developer checklist.

