# Android Crash-Fix Assistant (`android_crash_fix_agent`)

A CrewAI project utilizing the JSONC-first project structure to analyze Android crashes and perform secure codebase search, controlled file edits, Gradle verification, and ADB device interactions on a local Android repository.

## Project Purpose & Capabilities

This assistant is designed to streamline Android crash debugging in distinct phases. It currently implements:

*   **Crash Intake Analysis**: Parses raw crash logs (from Firebase Crashlytics or Logcat) to extract exception types, stack trace markers, affected architecture layers, severity, and device/OS clues.
*   **Secure Codebase Investigation**: Uses custom local Python tools to list source files, search for class/method names referenced in the stack trace, and inspect relevant code files.
*   **Controlled File Edits**: Employs an exact-match search-and-replace edit tool with backup capabilities to safely apply code fixes.
*   **Gradle Build & Test Verification**: Runs secure compile and unit test commands using `./gradlew` to ensure modifications compile and pass tests.
*   **ADB Device Reproduction**: Lists active emulators/devices, queries logcat buffers for crash clues, launches target activities, and captures execution screenshots to document verification results.
*   **PR Report Compilation**: Bundles the findings, fix details, compile status, and screenshot verification into a PR description template for developers.

### Safety Guardrails
*   **Controlled Edits**: Edits are applied using an exact-match block tool to prevent generic, out-of-context file overwrites.
*   **Command Sanitization**: Rejects any inputs to Gradle/ADB tools containing shell command separators or arbitrary execution flags.
*   **Path Sandboxing**: Custom tools enforce strict parent-directory validation to reject any paths resolving outside the target Android project directory.

---

## Project Structure

```text
android_crash_fix_agent/
├── agents/
│   ├── android_crash_intake_analyst.jsonc      # Parses raw crash context
│   ├── android_codebase_investigator.jsonc     # Searches & reads code, checks adb devices
│   ├── android_fix_planner.jsonc               # Devises fix strategy & applies edits
│   └── android_pr_report_writer.jsonc          # Generates final PR description & screen captures
├── tools/
│   ├── __init__.py
│   ├── project_tree_tool.py                    # Recursively lists source files securely
│   ├── project_search_tool.py                  # Case-insensitive text search in code
│   ├── file_read_tool.py                       # Reads line-numbered file contents securely
│   ├── file_edit_tool.py                       # Controlled exact-match file editing
│   ├── gradle_verify_tool.py                   # Securely runs gradle compilation and unit tests
│   ├── adb_tool.py                             # Safely manages adb device reproduction & capture
│   └── git_tool.py                             # Manages branch creation, commits, and PR Compare generation
├── crew.jsonc                                  # Crew orchestrator, task list, and inputs
├── .env                                        # Environment variables (OpenRouter keys, etc.)
├── pyproject.toml                              # Dependencies configuration
└── README.md                                   # Project documentation
```

---

## Running the Crew

To run the assistant, configure your environment and run the CrewAI command:

1.  **Configure API Key**: Add your OpenRouter API key to the `.env` file:
    ```env
    OPENROUTER_API_KEY=your_key_here
    ```
2.  **Define Inputs**: Set the inputs in `crew.jsonc` or pass them when running. The crew accepts:
    *   `raw_crash_context`: The raw crash trace or Firebase Crashlytics text.
    *   `android_project_path`: Absolute path to your Android application directory (e.g., `/Users/retailopakistan/Documents/tp-app`).
3.  **Execute**:
    ```bash
    uv run run.py
    ```

### Sample `raw_crash_context` Input

```text
Fatal Exception: java.lang.NullPointerException: Attempt to invoke virtual method 'java.lang.String com.example.myapp.model.User.getName()' on a null object reference
       at com.example.myapp.ui.profile.ProfileViewModel.loadUserProfile(ProfileViewModel.kt:42)
       at com.example.myapp.ui.profile.ProfileScreenKt$ProfileScreen$2$1.invoke(ProfileScreen.kt:85)
       at com.example.myapp.ui.profile.ProfileScreenKt$ProfileScreen$2$1.invoke(ProfileScreen.kt:83)
```

---

## Generated Reports (`output/`)

Upon completion, four markdown reports are written to the `output/` directory:

1.  `output/crash_intake_report.md`: Structured breakdown of the crash type, stack trace location, severity, and confirmed facts.
2.  `output/codebase_investigation.md`: Results of codebase search queries, file reads, and connected ADB devices/logcat check.
3.  `output/fix_plan.md`: Proposes root cause analysis, Kotlin/Compose edits, and includes the file_edit / gradle verification outputs.
4.  `output/pr_report.md`: Final review-ready report with PR description, manual QA verification screenshot paths, build/test status, risk level, and developer checklist.

---

## Future Roadmap (Phase 6 and beyond)

- [x] **Phase 3: Controlled File Edits**: Safe, exact-match search-and-replace edit tool (`file_edit_tool.py`) implemented and registered to the fix planner agent.
- [x] **Phase 4: Gradle Build & Test Verification**: Safe executing tool (`gradle_verify_tool.py`) that runs `./gradlew` tasks and returns compiler/test results to the agent.
- [x] **Phase 5: ADB Device Reproduction**: Use ADB commands to list devices, retrieve logcat logs, start target activity, and capture screenshots/videos (`adb_tool.py`).
- [x] **Phase 6: Git & PR Integration**: Automate branch creation, staging file edits, committing, and submitting PR compare scripts and copy-paste templates (`git_tool.py`).
- [ ] **Phase 7: Direct Firebase Integration**: Fetch crash logs directly from Firebase Crashlytics API using CLI credentials.
