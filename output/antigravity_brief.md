# Engineering Brief for Autonomous Agent: Fix GitHub API Networking Crash

## 1. Objective
Eliminate the crash caused by DNS resolution failures when the Android app (CricScore) calls the GitHub REST API.  
Safely catch the network exception, present a user‑friendly error state, and allow retry without adding unrelated changes or breaking existing functionality.

## 2. Ticket Summary
The app triggers a fatal exception (unhandled) when it attempts to fetch issue `#8` from the repository `ChFardeelAzhar/CricScore` via the GitHub API endpoint `https://api.github.com/repos/ChFardeelAzhar/CricScore/issues/8`.  
The root cause is a DNS resolution failure for `api.github.com` (`NameResolutionError`), most likely occurring on the device or in a Python-backed networking component (Chaquopy).  
The failure propagates as an uncaught exception, potentially crashing the app.  
The expected behaviour is: no crash, a visible error message with a retry option, and proper logging of the network fault.

## 3. Investigation Instructions
1. **Read the full ticket report** at:  
   `/Users/retailopakistan/Documents/FardeelAgenticProjects/crewai/android_crash_fix_agent/output/ticket_intake_report.md`  
   to grasp all details, stack trace hints, and acceptance criteria.

2. **Explore the codebase** without assuming any file paths.  
   - Search for occurrences of the string `api.github.com`, `/repos/ChFardeelAzhar/CricScore/issues/8`, or similar URL construction logic.  
   - Look for networking libraries in use (OkHttp, Ktor, Retrofit, Volley) or any Python integration (Chaquopy).  
   - Identify the ViewModel, repository, or use‑case class responsible for fetching the GitHub issue.  
   - Check for existing error handling around that network call (e.g., `try‑catch`, `Result` wrappers, sealed classes).  
   - Examine how the fetched data is consumed by the Jetpack Compose UI layer – which screen shows the issue content.

3. **Understand the architectural patterns** already in place (MVVM, state management, dependency injection) so that the fix integrates seamlessly.

## 4. Implementation Constraints
- **Minimal change** – only modify the necessary code to handle the network failure; do not refactor unrelated modules or classes.
- **Lifecycle‑safe coroutines** – use `viewModelScope` or appropriate scope to avoid leaks; never use `GlobalScope`.
- **MVVM consistency** – expose a state (e.g., `UiState<Issue>` sealed class) with `Loading`, `Success`, and `Error` variants from the ViewModel.
- **Compose‑only UI** – modify only the Compose screen that renders the issue; add an error state with a retry button.
- **No breaking of existing tests** – run `./gradlew test` after the changes and ensure all tests pass. If any test fails, adjust the fix but not the test logic.
- **Kotlin only** – no new Java files, Python modifications, or build script changes unless absolutely required to fix the underlying DNS resolution (and such changes would need explicit approval, which is out of scope – assume only app‑level recovery is expected).
- **Logging** – add structured logging (using `Timber` if already present, else standard `Log`) with clear tags, including the endpoint, error type, and timestamp.
- **Retry mechanism (optional but recommended)** – implement a simple retry with exponential backoff up to a small cap to improve user experience, without causing ANRs.

## 5. Definition of Done
- The app no longer crashes when a DNS failure occurs for the GitHub API call.
- The user sees an appropriate error screen (message + retry button) where the issue content would normally appear.
- The network call attempts are retried automatically upon retry tap, and the UI updates accordingly on success.
- Diagnostic logs are emitted, capturing the failure details.
- All existing unit/instrumentation tests pass.
- The changes are applied directly to the working tree (no separate PR or commit instruction).

---

## FIX_INSTRUCTION
```
You are an autonomous Android coding agent. Your task is to fix the crash described in the ticket report located at:
/Users/retailopakistan/Documents/FardeelAgenticProjects/crewai/android_crash_fix_agent/output/ticket_intake_report.md

Open that file first and understand the error: a DNS resolution failure for `api.github.com` causes an unhandled exception when the app tries to fetch issue #8 from the GitHub repo `ChFardeelAzhar/CricScore`. The stack trace originates from Python’s `requests` library, but that detail is secondary; the fix must make the Android app resilient to any network failure for that API call.

Working directory: /Users/retailopakistan/AndroidStudioProjects/CricScore

**Step 1 – Locate the relevant code**
- Search the entire project for the string `api.github.com`. If not found, search for `issues/8` or for URL path building that could lead to the GitHub API endpoints.
- Identify the networking layer (OkHttp, Retrofit, Ktor, or a custom Python bridge). Determine where the HTTP request is made and where its response is processed.
- Find the ViewModel (or repository) that consumes the GitHub issue data. Also identify the Composable screen that displays the issue (e.g., an `IssueDetailScreen` or `FeedbackScreen`).
- Check if there is already any error handling – a `try-catch` block, a sealed `Result` class, or a `NetworkBoundResource` pattern. If none exists, you must add one.

**Step 2 – Implement the fix (minimal, MVVM‑consistent, lifecycle‑safe)**
- In the data/repository layer, wrap the network call in a `try‑catch` that catches `Exception` (specifically `UnknownHostException`, `IOException`, and any thrown by the Python bridge if applicable) and returns a safe result (e.g., `Result.failure` or a custom sealed class like `FetchResult.Error`).
- In the ViewModel, convert that result into a UI state (e.g., a sealed class `IssueUiState` with `Loading`, `Success(data)`, `Error(message)`). Expose it as a `StateFlow`.
- Scope all coroutines with `viewModelScope` (or the appropriate lifecycle‑aware scope).
- In the Compose screen, collect the state and branch: show a `CircularProgressIndicator` for Loading, the content for Success, and an error message (e.g., “Could not load data. Check your connection and try again.”) with a *Retry* button for Error.
- The Retry button should re‑launch the fetch (call the same ViewModel function) without requiring a screen rebuild.
- Optionally implement an automatic retry with exponential backoff (max 3 retries, capped total timeout of 8 seconds) to handle transient DNS failures. If you choose to add this, ensure it does not block the UI thread and that each retry logs the attempt.
- Add Timber logging (or `Log.d` if Timber is absent) at the point of failure: tag like `GitHubApi`, message including endpoint, error class, and stack trace (as string for debugging). Never log sensitive data.
- Do NOT change any code unrelated to this network call (no refactoring of other ViewModels, repositories, or UI components).
- If the project uses dependency injection (Hilt, Koin), ensure any new dependencies (like `ConnectivityManager` if you add network checks) are provided accordingly, but avoid adding complex checks. A simple catch is sufficient for this ticket.

**Step 3 – Testing**
- After making changes, run `./gradlew test` from the project root to verify no existing tests are broken.
- If you added new logic (like retry), ensure the existing tests still pass; do not write new tests unless explicitly instructed (and if you do, keep them minimal).

**Important constraints:**
- Use Kotlin and Jetpack Compose.
- Keep all modifications **lifecycle‑safe** (no `GlobalScope`, no manual thread management).
- Follow MVVM – ViewModel exposes state, Composable observes it.
- Do not introduce new UI patterns or libraries unless absolutely necessary.
- The fix must be applied directly to the working tree – make the edits in place.

Provide a summary of the files changed and the nature of the changes after you are done.
```