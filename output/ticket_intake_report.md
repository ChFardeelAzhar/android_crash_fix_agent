# Ticket Intake Report

**Ticket Type:** Fix  
*(Classified as Fix because the ticket describes an error/crash when the application attempts to contact the GitHub REST API, resulting in a network failure that likely disrupts functionality.)*

---

## Summary
The application fails to retrieve data from the GitHub REST API due to a DNS resolution error for `api.github.com`. The underlying exception (NameResolutionError) indicates that the hostname could not be resolved to an IP address, causing the HTTPS connection to fail after maximum retries. The specific endpoint being called is `/repos/ChFardeelAzhar/CricScore/issues/8`. This prevents features that depend on GitHub data (e.g., issue tracking, feedback) from functioning and may lead to an unhandled exception or crash.

---

## Confirmed Facts
- The error occurred while contacting the GitHub REST API.
- The attempted connection was to `api.github.com` on port 443 (HTTPS).
- The URL path is `/repos/ChFardeelAzhar/CricScore/issues/8`, suggesting an attempt to fetch issue #8 from a specific repository.
- The failure is classified as `NameResolutionError` with the message: `Failed to resolve 'api.github.com' ([Errno 8] nodename nor servname provided, or not known)`.
- The stack trace originates from Python’s `requests` library (`HTTPSConnectionPool`), indicating the error was raised by a component using Python, possibly a build script, backend service, or a cross-compiled library within the Android app.
- No error handling or retry‑with‑backoff appears to be in place; the connection exhausted its retries and propagated a fatal exception.

---

## Assumptions
- The ticket likely came from an Android application or its related toolchain, as the context is an Android engineering analysis.
- If the error is in the Android app itself, the app is using a networking library (perhaps Ktor, OkHttp, or a Python bridge) to interact with the GitHub API. The Python trace might be from an embedded Python environment (e.g., Chaquopy) or a backend service, but for this intake we assume it affects the Android client.
- The device has at least intermittent internet connectivity, but DNS resolution specifically for `api.github.com` fails. This could be due to a local network misconfiguration, VPN, custom DNS settings, or an upstream DNS outage.
- The feature relying on this API call is a core function (e.g., fetching live scores or issue feedback), and the failure is not gracefully handled, potentially causing a crash or an unusable state.

---

## Expected Output
- The application should handle DNS resolution failures gracefully:
  - Display a user‑friendly error message (e.g., “Unable to connect to server. Please check your network connection.”).
  - Not crash or freeze the UI.
  - Optionally retry with exponential backoff or prompt the user to retry.
- If the data is non‑critical, the app should fall back to cached or default content.
- Detailed diagnostic logs should be recorded for developers without exposing stack traces to the end user.
- When the network condition returns to normal, the feature should resume working without manual intervention.

---

## Required Steps
1. **Root‑Cause Analysis**
   - Reproduce the issue on various network conditions (Wi‑Fi, mobile data, VPN, custom DNS).
   - Check whether the DNS failure is transient or persistent for `api.github.com`.
   - Inspect whether the device is using a proxy or a DNS‑over‑HTTPS setting that may block or alter resolution.

2. **Code‑Level Mitigations**
   - Implement proper exception handling in the network layer to catch `UnknownHostException` (Android) / `NameResolutionError` (Python) and convert it to a managed error state.
   - Add a connectivity checker (e.g., `ConnectivityManager`) before network calls, and perform an explicit DNS resolution test if needed.
   - Introduce an automatic retry mechanism with exponential backoff, but ensure total timeout is capped to avoid ANRs.
   - Provide a fallback path (e.g., serve locally cached data if available and show a stale‑data indicator).

3. **UI/UX Improvements**
   - Design an error state for the view that shows a meaningful message and a “Retry” button.
   - Ensure no raw exception details are leaked to the user interface.

4. **Logging & Monitoring**
   - Add structured logging (e.g., `Timber`) to capture the precise error details, network state, and the endpoint URL when the failure occurs.
   - Integrate with crash reporting (e.g., Firebase Crashlytics) to monitor the frequency and conditions of this error.

5. **Testing**
   - Simulate DNS failures using test tools or by temporarily overriding DNS settings.
   - Verify that the app remains stable, does not crash, and correctly shows the error/retry UI.

---

## Acceptance Criteria
*These are not explicitly provided in the raw ticket; the following are reasonable criteria for a fix.*
- When a DNS resolution failure occurs for `api.github.com`, the app does **not** crash or display a raw stack trace.
- The user is shown a clear error indication, such as a snackbar or inline message: “Could not load data. Check your connection and try again.”
- A “Retry” action is available; upon network recovery, the request succeeds and UI updates accordingly.
- The error is logged with sufficient detail (endpoint, error type, timestamp) for diagnostics.
- The feature performs as expected under normal network conditions (no regression).

---

## Severity
**High**  
The error blocks a network‑dependent feature and, if unhandled, may cause a crash that requires the user to restart the app. While not a total application outage, it significantly degrades user experience for anyone using the affected functionality.

---

## Missing Information
- **Source of the error:** Is this from an Android client, a CI/CD script, or a backend service used by the app? Clarifying the environment will guide the fix approach.
- **Device/Platform details:** Android version, device model, network type (Wi‑Fi/mobile), and any custom DNS or proxy settings.
- **Reproduction steps:** Is it consistently reproducible? Does it happen on specific networks or regions?
- **App version:** Which build/version is affected? Has this worked before (regression)?
- **Impact scope:** How many users are experiencing this? Is it tied to a specific screen or feature?
- **Existing error handling:** Is there already a try‑catch around this API call? If so, why is the exception not handled?
- **Criticality:** Is fetching GitHub issues a core feature (e.g., live scores from that repo) or a secondary feedback channel?
- **Acceptance criteria:** The raw ticket contains no explicit AC; the ones listed above are inferred and should be validated with the product owner.

---

**Prepared by:** Android Ticket Analyst  
**Date:** [Current date would be inserted here]