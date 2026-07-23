# Crash Intake Report

## Summary
This is a **fatal `ActivityNotFoundException`** crash occurring on the **HomeScreen** of the **TMS** Android application (version 1.0.22, build 24). The crash happens when the user taps a clickable element that attempts to launch an implicit `ACTION_VIEW` intent for an AWS S3 URL (`https://bra-tools.s3.eu-west-1.amazonaws.com/...`). The system cannot find any installed Activity that can handle this intent, resulting in a crash.

## Confirmed Facts

### Application & Version
- **Package:** `com.ananinja.tms`
- **Version Name:** `1.0.22`
- **Version Code:** `24`
- **Issue ID:** `9b26cd77e392a55e6224dcfd78f509f7`
- **Session ID:** `6A5D794E01C400013A92A485EA6563E3_DNE_0_v2`

### Exception Details
- **Exception Type:** `android.content.ActivityNotFoundException`
- **Exception Message:** `"No Activity found to handle Intent { act=android.intent.action.VIEW dat=https://bra-tools.s3.eu-west-1.amazonaws.com/... }"`
- **Crashed Thread:** Main thread (Fatal Exception)

### Stack Trace Signals
1. **Originating Code:**
   - `com.ananinja.tms.ui.home.HomeScreenKt.HomeScreen$lambda$38$0$0(HomeScreen.kt:271)` — This is the exact line where the intent is launched.
   - The lambda `$lambda$38` suggests this is inside a Compose function, likely a button or clickable text.

2. **Android Framework Layers Traversed:**
   - `Instrumentation.checkStartActivityResult()` — throws exception
   - `Instrumentation.execStartActivity()` — executes intent
   - `Activity.startActivityForResult()` — called from Jetpack Compose
   - `Activity.startActivity()` — final call

3. **UI Interaction Chain:**
   - Touch event dispatched through Compose touch system
   - `ClickableNode$clickPointerInput$3.invoke-k-4lQ0M` — Compose click handler
   - `TapGestureDetectorKt$detectTapAndPress$2$1.invokeSuspend` — gesture detection
   - Pointer event processing through Compose's `AndroidComposeView`

4. **Intent Details (Confirmed):**
   - **Action:** `android.intent.action.VIEW`
   - **Data URI:** `https://bra-tools.s3.eu-west-1.amazonaws.com/...` (truncated in report)
   - No extras or flags explicitly shown in the truncated intent string

### Device & OS Clues
- **No specific device model captured** (not in provided snippet)
- **No OS version captured** (not in provided snippet)
- **Timezone:** Pakistan Standard Time (GMT+5) — suggests user in Pakistan or nearby region
- **Date:** Mon Jul 20 2026 06:26:48 — this is a future date (likely a test/emulator crash)

### Severity
- **Crash Level:** Fatal (app crashes, user cannot continue)
- **User Impact:** Direct — user taps something expecting a web browser or external app to open, but the app crashes instead
- **Frequency:** Single occurrence reported (in this snippet)

## Assumptions

1. **What the intent is trying to do:** The app is attempting to open an S3 URL (likely a PDF or another document stored on AWS S3) by launching an implicit intent with `ACTION_VIEW`.
2. **Why it fails:** No Activity on the device can handle `https://` URLs. This could be because:
   - The device has no browser installed (rare but possible, e.g., kiosk mode, enterprise device)
   - The browser is disabled or blocked by policy
   - A custom URL scheme is being used but not registered
3. **User action:** The user tapped a clickable element (likely a button, link, or card) on the HomeScreen that triggers opening a document/resource.
4. **Compose version:** The app uses Compose (based on `ComponentActivity.kt`, `ClickableNode.java`, `AndroidComposeView`).
5. **Crash origin:** The crash originates from the main thread during UI interaction, not from a background task.
6. **No `Intent.FLAG_ACTIVITY_NEW_TASK` used:** The crash does not mention `FLAG_ACTIVITY_NEW_TASK`, which is commonly missing when launching activities from non-Activity contexts (but here it’s launched from an Activity, so that’s less relevant).

## Likely Affected Layer

- **UI Layer (Compose HomeScreen)**
- **Android Framework** (Intent resolution system)
- **External App Compatibility Layer** (lack of browser/app that can handle `https://`)

## Reproduction Clues

1. **Prerequisite:** User is on HomeScreen of the app.
2. **Trigger:** User taps a specific UI element that is designed to open a link (likely an announcement, notification, or help/documentation link).
3. **Environment:** Device lacks a default browser or any app that can handle `ACTION_VIEW` with an `https` scheme.
4. **Possible Reproduction Steps:**
   - Install app on a device with no browser (e.g., AVD with no Google apps, enterprise device).
   - Navigate to HomeScreen.
   - Tap the element that triggers the S3 URL.
   - App crashes immediately.

## Missing Information

1. **Complete URL:** The report truncates the URL (`https://bra-tools.s3.eu-west-1.amazonaws.com/...`). Full URL is needed to understand what type of content is being opened.
2. **Device Model & OS Version:** Not captured in this snippet. Critical for understanding if this is device-specific.
3. **Android API Level:** Not present. Important because intent resolution behavior changed in Android 11+ (package visibility).
4. **Does the crash happen consistently?** Single occurrence, but this could be the only user with this issue.
5. **QueryIntentActivities result:** Was a `PackageManager.queryIntentActivities()` check performed before firing the intent? The crash suggests it was **not** used.
6. **`WebView` presence:** If the intent is for a PDF or document, does the app have a WebView-based fallback?
7. **Custom Chrome Tabs setup:** Does the app use Custom Tabs? If so, is the service bound?
8. **Network state:** Was the user offline? Could the URL be malformed?
9. **Exact user action:** What does the HomeScreen element represent? (e.g., button saying "View Report", "Open Document", etc.)
10. **ProGuard/R8 mapping:** The lambda names (`$lambda$38`) make it hard to map back to source. Need a mapping file for exact function.

## Next Investigation Steps

1. **Examine the full URL** — determine if it uses a non-standard scheme (e.g., `customapp://`) that requires a specific app.
2. **Add `PackageManager` check** before firing the intent:
   ```kotlin
   val intent = Intent(Intent.ACTION_VIEW, uri)
   if (intent.resolveActivity(packageManager) != null) {
       startActivity(intent)
   } else {
       // Show user-friendly error or open in WebView
   }
   ```
3. **Implement a fallback** — if no external app can handle the URL, use a WebView within the app to display the content.
4. **Consider using Chrome Custom Tabs** — which provides better integration and handles missing browser scenarios more gracefully.
5. **Add exception handling** — wrap `startActivity()` in a try-catch for `ActivityNotFoundException`:
   ```kotlin
   try {
       startActivity(intent)
   } catch (e: ActivityNotFoundException) {
       // Log and show snackbar/toast
   }
   ```
6. **Check if the device has a browser** — could be a known issue on certain kiosk or enterprise devices.
7. **Verify Android 11+ package visibility** — if targeting API 30+, ensure `<queries>` element in AndroidManifest includes the browser or custom apps needed.
8. **Review HomeScreen.kt line 271** — map lambda to source code to understand what triggers this intent.
9. **Check Firebase Crashlytics dashboard** for:
   - Device distribution of this crash
   - OS version distribution
   - Crash count vs. affected users
10. **Test on a device with no browser** (e.g., AVD with no Google Play services) to reproduce.