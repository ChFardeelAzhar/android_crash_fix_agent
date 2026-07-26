# Crash Intake Report: `ActivityNotFoundException` on Opening S3 Link from HomeScreen

## Summary
A fatal `android.content.ActivityNotFoundException` occurred when the user tapped a clickable element in the `HomeScreen` composable. The app attempted to open an HTTPS URL pointing to an AWS S3 bucket (`bra-tools.s3.eu-west-1.amazonaws.com`) but no Activity on the device could handle the implicit `ACTION_VIEW` intent. This typically means the device lacks a browser or the intent's data URI is malformed/unhandled.

---

## Confirmed Facts
- **Exception type**: `android.content.ActivityNotFoundException`
- **Exception message**: `No Activity found to handle Intent { act=android.intent.action.VIEW dat=https://bra-tools.s3.eu-west-1.amazonaws.com/... }`
- **Failing user code**:  
  `com.ananinja.tms.ui.home.HomeScreenKt.HomeScreen$lambda$38$0$0(HomeScreen.kt:271)`  
  This is a lambda (likely an `onClick` handler) inside Jetpack Compose's `HomeScreen` composable.
- **Trigger action**: User tap on a clickable composable (detected via `ClickableNode` / `TapGestureDetector`).
- **Intent details**:
  - Action: `android.intent.action.VIEW`
  - Data URI: `https://bra-tools.s3.eu-west-1.amazonaws.com/...` (truncated in log)
- **App version**: 1.0.22 (build 24)
- **Platform**: Android
- **Date**: Mon Jul 20 2026 06:26:48 GMT+0500 (Pakistan Standard Time)
- **Time zone hint**: User in Pakistan (GMT+5), suggesting possible network/regional configuration differences.
- **Firebase Crashlytics present**: Crash was captured and reported by Crashlytics.

---

## Assumptions
1. **The truncated URI ends with a valid path** (e.g., a PDF, image, or other downloadable file). The actual full URI is not visible in the log.
2. **The clickable element is either**:
   - A `Text` or `Image` with a `clickable` modifier that opens a link.
   - A button or card that navigates to an external URL.
3. **The user does not have a default browser installed** OR the device's browser cannot handle the specific HTTPS URL (e.g., because of missing `https` scheme handling, restricted profile, or custom ROM).
4. **The crash occurs on the main thread** (UI thread), as `startActivity` must be called from the UI thread.
5. **The device likely has no WebView-based browser** or the intent resolution failed due to a missing Activity for `ACTION_VIEW` with an `https` scheme.

---

## Exception Type
```
android.content.ActivityNotFoundException
```

---

## Stack Trace Signals

### Key frames (top to bottom):

| Frame | Method/File | Line | Signal |
|-------|-------------|------|--------|
| 1 | `Instrumentation.checkStartActivityResult` | 2018 | **Root cause** – OS detected no Activity to handle the intent. |
| 2–7 | `startActivityForResult` → `startActivity` | – | Standard Android Activity launch chain. |
| 8 | `HomeScreenKt.HomeScreen$lambda$38$0$0` | 271 | **User code trigger** – the lambda that starts the intent. |
| 9–12 | `ClickableNode` -> `TapGestureDetector` | – | **User interaction** – tap gesture detected. |
| 13–17 | Coroutine dispatch (`DispatchedTask`, `CancellableContinuationImpl`) | – | **Async execution** – the tap handler is running on a coroutine. |
| 18–25 | Compose pointer input (`SuspendingPointerInputModifierNodeImpl`, `HitPathTracker`) | – | **UI event delivery** through Compose system. |
| 26–45 | Android View system (`ViewGroup.dispatchTouchEvent`, `DecorView`, `ViewRootImpl`) | – | **Standard touch event dispatch** down to Compose. |

### Thread: Main (1: main)
- The entire crash happens on the **main thread**.

---

## Likely Affected Android Layer
**Application Layer → UI Layer (Jetpack Compose)**  
Specifically:
- **`HomeScreen.kt`** at line 271 – the lambda that builds the `ACTION_VIEW` intent.
- The intent is **not validated** before calling `startActivity`.
- No `try-catch` around `startActivity` to catch `ActivityNotFoundException`.

---

## Severity
**CRITICAL / FATAL**  
- The app crashes immediately upon user tap.
- User cannot use the feature that triggers this link.
- Potential for high user impact if this link is frequently accessed.

---

## Reproduction Clues

### Required conditions:
1. User must be on the **HomeScreen** of the app (com.ananinja.tms).
2. User must tap on a UI element that triggers an **implicit intent** with `ACTION_VIEW` and an **HTTPS URL** pointing to `bra-tools.s3.eu-west-1.amazonaws.com`.
3. The device must have **no Activity that can handle `ACTION_VIEW` for `https://`**.

### Most probable scenario:
- The user is on a device with **no browser installed** (e.g., a restricted device, kiosk mode, or a pure Android TV device).
- Or the device's browser is **disabled**.
- Or the intent is malformed (e.g., the URI is missing the scheme after truncation, but this is unlikely because the log shows `https://`).

### Suggested manual repro:
1. Run the app on an emulator with **no browser** (or uninstall Chrome).
2. Navigate to the HomeScreen.
3. Tap the element that opens the S3 link.
4. Observe `ActivityNotFoundException`.

---

## Device or OS Clues
- **No device model / OS version** is provided in the crash log.
- **Time zone**: `GMT+0500 (Pakistan Standard Time)` → User is likely in Pakistan.
- **Notable**: The crash log includes many background threads (Firebase, Okio, Kotlin coroutines) but no indication of specific device restrictions.
- **No `Build.MODEL` or `Build.VERSION.SDK_INT`** available from the given data.

---

## App Version Clues
- **Version name**: `1.0.22`
- **Version code**: `24`
- This is the only version in the log; no regression information is available.

---

## Missing Information

1. **Full URI** after `https://bra-tools.s3.eu-west-1.amazonaws.com/...` – the actual file/resource path is truncated. This is critical to understand if the URL is valid.
2. **Device model and OS version** – needed to know if this is a known device issue.
3. **Existing browser apps on the device** – unknown.
4. **Whether the user is in a work profile or child mode** – could explain missing browser Activity.
5. **Code context of `HomeScreen.kt:271`** – the exact line that builds the intent.
6. **How the URI is obtained** – hardcoded, from network, or from user input.
7. **Previous occurrences** – first time or recurring crash in this session.
8. **Whether the user has ever successfully opened this link before** – no session history provided.
9. **Whether `PackageManager.queryIntentActivities()` was called to check availability** – very likely not, as there is no such check in the stack trace.

---

## Next Investigation Steps

1. **Check the full source code** of `HomeScreen.kt` around line 271 to see how the intent is created. Look for:
   ```kotlin
   val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://..."))
   context.startActivity(intent)
   ```
2. **Add a safety check** before starting the activity:
   ```kotlin
   val intent = Intent(Intent.ACTION_VIEW, uri)
   if (intent.resolveActivity(packageManager) != null) {
       context.startActivity(intent)
   } else {
       // Fallback: show a dialog, toast, or open in WebView
   }
   ```
3. **Wrap `startActivity` in a `try-catch`** to handle `ActivityNotFoundException` gracefully:
   ```kotlin
   try {
       context.startActivity(intent)
   } catch (e: ActivityNotFoundException) {
       // Log and show user-friendly message
   }
   ```
4. **Verify the S3 URI** is valid and accessible. Check if the bucket policy allows public access.
5. **Collect device and OS version** from Firebase Crashlytics dashboard for this specific crash (session `6A5D794E01C400013A92A485EA6563E3_DNE_0_v2`).
6. **Check if the app targets a specific device type** (e.g., kiosk, TV, or enterprise devices) that might lack a default browser.

---

## Summary Table

| Category | Details |
|----------|---------|
| **Exception** | `android.content.ActivityNotFoundException` |
| **File** | `HomeScreen.kt:271` |
| **Action** | User tap → startActivity(ACTION_VIEW, https://...) |
| **URI** | `https://bra-tools.s3.eu-west-1.amazonaws.com/...` |
| **Root Cause** | No Activity (browser) installed/enabled to handle HTTPS intent |
| **Severity** | Critical – app crashes on user interaction |
| **Fix** | Add intent resolution check + try-catch + fallback UI |