# Crash Intake Report: `ActivityNotFoundException` on HomeScreen Tap

## Summary
A **fatal** `ActivityNotFoundException` occurs when a user taps a clickable element on the `HomeScreen` (Compose UI) that attempts to open an HTTPS URL (`https://bra-tools.s3.eu-west-1.amazonaws.com/...`). The device lacks any application registered to handle the `ACTION_VIEW` intent for this URL, causing the crash.

## Confirmed Facts
- **Exception Type:** `android.content.ActivityNotFoundException`
- **Exception Message:** `No Activity found to handle Intent { act=android.intent.action.VIEW dat=https://bra-tools.s3.eu-west-1.amazonaws.com/... }`
- **Failing Source Location:** `com.ananinja.tms.ui.home.HomeScreenKt.HomeScreen$lambda$38$0$0(HomeScreen.kt:271)` — line 271 of `HomeScreen.kt`
- **UI Trigger:** Compose `ClickableNode` tap gesture detected via `TapGestureDetector` on the HomeScreen.
- **Intent Action:** `android.intent.action.VIEW`
- **Intent Data URI:** `https://bra-tools.s3.eu-west-1.amazonaws.com/...` (URL truncated in crash log, ends with `...` indicating long query/path)
- **App Version:** 1.0.22 (24)
- **Date/Time:** `Mon Jul 20 2026 06:26:48 GMT+0500` (Pakistan Standard Time)
- **Crash is produced on the main thread** (UI thread) — visible from the stack trace ending in `Looper.loop` -> `ActivityThread.main`.

## Assumptions
- The URL is being opened by the system (via implicit intent) rather than a WebView or in-app browser.
- The user likely does **not** have a web browser installed or the default browser has been disabled/uninstalled on that device.
- The URL might be dynamically constructed or fetched from server data, and the truncated part could contain additional path/query parameters.
- The crash occurs during normal usage, likely tapping a link/button in the HomeScreen that opens an external resource (e.g., a PDF, image, or web page hosted on AWS S3).

## Exception Type

```
android.content.ActivityNotFoundException: No Activity found to handle Intent { act=android.intent.action.VIEW dat=https://bra-tools.s3.eu-west-1.amazonaws.com/... }
```

## Stack Trace Signals

| Signal | Detail |
|--------|--------|
| **Top of stack** | `Instrumentation.checkStartActivityResult()` throws the exception |
| **User code entry** | `HomeScreenKt.HomeScreen$lambda$38$0$0(HomeScreen.kt:271)` — this is likely a lambda inside a Composable function that calls `startActivity()` |
| **Compose chain** | `ClickableNode` -> `TapGestureDetector` -> pointer input handling |
| **Android framework** | `Activity.startActivity()` -> `Instrumentation.execStartActivity()` |
| **Thread** | Main thread (UI) — evident by `Looper.loop` -> `ActivityThread.main` |
| **Other threads** | All other threads are idle/waiting (e.g., `DefaultDispatcher`, `Okio Watchdog`, Firebase threads) — no concurrent crash cause |

## Likely Affected Layer
- **Application Layer:** `HomeScreen.kt` Composable function
- **Android Framework:** Implicit intent resolution for `ACTION_VIEW` — no browser/intent handler registered on device
- **Compose UI Layer:** `ClickableNode` -> `TapGestureDetector` — user interaction triggers the intent

## Severity
**FATAL** — Application crashes completely, user cannot continue without killing and restarting the app. The crash is unrecoverable in the current flow.

## Reproduction Clues
- **Prerequisites:**
  1. Device **without** a web browser installed (or default browser disabled).
  2. App version **1.0.22 (24)**.
  3. User taps a specific UI element on the `HomeScreen` that attempts to open `https://bra-tools.s3.eu-west-1.amazonaws.com/...` via implicit intent.
  
- **Steps to reproduce:**
  1. Launch the app (version 1.0.22).
  2. Navigate to the HomeScreen.
  3. Tap the clickable element associated with the lambda at `HomeScreen.kt:271`.
  4. The app crashes with `ActivityNotFoundException`.

- **Possible UI triggers:** A button or link labeled "View Tools", "Open Resource", or similar that fetches a URL from server data.

## Device or OS Clues
- **No specific device/OS version** is provided in the crash log (only stack traces, no device model/OS API level).
- The crash could occur on any Android version, but devices with no or minimal pre-installed apps (e.g., Android Go, custom ROMs, enterprise-managed devices) are more likely to be affected.
- Timezone: Pakistan Standard Time (GMT+5).

## App Version Clues
- App version: **1.0.22 (24)**
- The crash might be introduced recently in this version if URL opening logic was added/changed.

## Missing Information
- **Device model and OS API level** — essential to know if this is widespread or device-specific.
- **Full URL** — the truncated URL (`...`) prevents understanding the exact resource type.
- **Crash rate/affected users** — how often this crash occurs (percentage of sessions).
- **User action context** — what the user tapped (button text/icon) and the screen state.
- **Whether the app uses `PackageManager.queryIntentActivities()`** before launching the intent (to check if a handler exists).
- **If a fallback mechanism exists** (e.g., opening in a WebView, showing a dialog, or using `CustomTabsIntent`).

## Next Investigation Steps

### 1. Check the source code at `HomeScreen.kt:271`
- Locate the lambda `HomeScreen$lambda$38` to understand what triggers the intent.
- Determine if the URL is hardcoded or dynamically retrieved (e.g., from API response, DeepLink, or configuration).

### 2. Add intent handler verification before launching
- **Recommended fix:** Use `PackageManager.resolveActivity()` before calling `startActivity()`:
  ```kotlin
  val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
  if (intent.resolveActivity(packageManager) != null) {
      context.startActivity(intent)
  } else {
      // Show error or fallback e.g., open in a WebView
  }
  ```

### 3. Consider using `CustomTabsIntent` or in-app WebView
- Instead of implicit intent, use `CustomTabsIntent.Builder().build().launchUrl(context, uri)` (Chrome Custom Tabs) which gracefully handles missing browsers.

### 4. Review URL construction logic
- Ensure the URL is properly validated and not malformed.
- Check if the `...` truncation is from the crash logger or actual intent data — long URLs may be truncated by Crashlytics.

### 5. Monitor device distribution in Crashlytics
- Look at the "Devices" and "OS" tabs in the Crashlytics dashboard for this issue (`9b26cd77e392a55e6224dcfd78f509f7`) to identify device patterns.

### 6. Add error logging
- Wrap the `startActivity()` call in a try-catch to log the URL and device state without crashing.

### 7. Test on emulators without browsers
- Set up an emulator that has no web browser installed (or remove Chrome) to reproduce the issue.

### 8. Consider using Android App Links or Deep Links
- If the URL belongs to the app’s domain/functionality, consider handling it directly via `AndroidManifest.xml` intent filters.