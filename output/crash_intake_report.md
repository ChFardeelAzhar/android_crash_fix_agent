# Crash Intake Report: ActivityNotFoundException in HomeScreen

## Summary
This is a **fatal crash** caused by an `ActivityNotFoundException` when the app attempts to open a URL via an implicit `ACTION_VIEW` intent. The crash occurs in the `HomeScreen` composable function at line 271 of `HomeScreen.kt`. The device does not have any application capable of handling HTTPS URLs (e.g., no web browser installed or the browser failed to handle the specific Amazon S3 URL).

## Confirmed Facts
- **Crash Type**: Fatal exception (crashes the application)
- **Exception**: `android.content.ActivityNotFoundException`
- **Exception Message**: "No Activity found to handle Intent { act=android.intent.action.VIEW dat=https://bra-tools.s3.eu-west-1.amazonaws.com/... }"
- **Failing Code Location**: 
  - File: `com.ananinja.tms.ui.home.HomeScreenKt`
  - Line: 271
  - Function: `HomeScreen$lambda$38$0$0`
- **App Package**: `com.ananinja.tms` (TMS - likely a Transportation/Task Management System)
- **App Version**: 1.0.22 (build 24)
- **User Action**: Tapping on a clickable element in the Home screen
- **Failing Intent**: 
  - Action: `android.intent.action.VIEW`
  - Data URI: `https://bra-tools.s3.eu-west-1.amazonaws.com/...` (truncated in log)
- **Intent Type**: Implicit intent (no specific package/component targeted)
- **Crashlytics Issue ID**: `9b26cd77e392a55e6224dcfd78f509f7`
- **Crash Date**: Mon Jul 20 2026 06:26:48 GMT+0500 (Pakistan Standard Time)
- **UI Framework**: Jetpack Compose (`ClickableNode`, `TapGestureDetector`)
- **Touch Event Chain**: Touch event → Compose pointer input → Click handler → `startActivity`

## Assumptions
- The app is trying to open an Amazon S3-hosted resource (likely a PDF, document, or image) from `bra-tools` bucket in `eu-west-1` region
- The URL is being trimmed/masked by Crashlytics (ends with `...`), so the full URL path is unknown
- The device lacks any browser application capable of handling HTTPS URLs (could be a device management restriction, work profile with disabled browsers, or a custom ROM)
- The clickable element is likely a button, card, or link in the Home screen UI
- The device might be a managed device (enterprise/kiosk) where browser access is restricted

## Exception Type
```
android.content.ActivityNotFoundException
```

### Exception Details
- **Class**: `android.content.ActivityNotFoundException`
- **Package**: `android.content`
- **Thrown when**: When `startActivity(Intent)` or its variants are called and there is no Activity registered to handle the specified Intent
- **Check method**: `android.app.Instrumentation.checkStartActivityResult()`

## Stack Trace Signals
| Signal | Details |
|--------|---------|
| **Primary Trigger** | User tap on Compose clickable element |
| **Failing Method** | `HomeScreenKt.HomeScreen$lambda$38$0$0` at line 271 |
| **Intent Creation Location** | Not shown in stack trace (likely defined in composable lambda) |
| **startActivity Call** | Via `Activity.startActivity(Intent)` |
| **Compose Event Flow** | Tap gesture → `ClickableNode` → `TapGestureDetector` → coroutine dispatch |
| **No Activity Resolver** | `Instrumentation.checkStartActivityResult` detected no matching activity |
| **Touch Path** | `Dialog` dispatch → `DecorView` → `ViewGroup` chain → `AndroidComposeView` → Compose input system |

## Likely Affected Layer
**Android Framework Layer (Implicit Intent Resolution)**

The crash occurs in the Android Framework's `Instrumentation` class during intent resolution. This is not an app logic bug in the traditional sense - the app correctly constructs an `ACTION_VIEW` intent, but the Android system fails to find any installed activity that can handle `https://` URIs.

### Component Stack:
1. **UI**: Jetpack Compose (HomeScreen composable)
2. **Intent**: Implicit ACTION_VIEW with HTTPS URI
3. **System**: Android PackageManager/Instrumentation - cannot resolve intent

## Severity
**Critical** - The crash is fatal and causes the application to terminate immediately. Any user tapping on the specific element in the Home screen will experience a crash. This affects app usability and user experience.

### Severity Factors:
- **Frequency**: Can occur every time the user taps this specific UI element
- **User Impact**: Application crash, potential data loss
- **Business Impact**: If the S3 resource is critical for operations (e.g., viewing tools, reports, or documents), this blocks essential functionality
- **Recurrence**: Deterministic - crashes 100% of the time on devices without a browser

## Reproduction Clues
1. **User Action**: Tap on a specific clickable element in the Home screen of the TMS app
2. **Prerequisite**: No browser application installed/enabled on the device
3. **Expected Behavior**: Open the S3 URL in a browser or WebView
4. **Actual Behavior**: Crash due to `ActivityNotFoundException`
5. **URL Pattern**: `https://bra-tools.s3.eu-west-1.amazonaws.com/...` (Amazon S3 resource)
6. **Context**: The element appears to be a link/button to download or view a document/tool from S3

### Reproduction Steps:
1. Install app version 1.0.22 (24) on a device without any browser app
2. Navigate to Home screen
3. Find and tap the clickable element that triggers the S3 URL intent
4. Observe crash

## Missing Information
1. **Full URL**: The complete URL path is truncated (`...`). Need to know the exact resource being accessed
2. **Device Model/OS Version**: Not specified in crash context
3. **Device Browser Status**: Unknown if device has no browser, or browser cannot handle the URL
4. **User Action Context**: What is the label/text on the clicked element?
5. **Network Status**: Was the device online when attempting to open the URL?
6. **Android Version**: Not specified in the crash dump
7. **Number of Occurrences**: Single user or widespread issue?
8. **Other Devices**: Does the same crash occur on other devices or is this device-specific?
9. **Crash Count**: How many times has this crash occurred in production?
10. **Region**: Only in Pakistan Standard Time zone (as per crash timestamp)?

## Next Investigation Steps

### Immediate Fixes (Developer)
1. **Add Safety Check**: Before calling `startActivity()`, check if there is an app that can handle the intent using `PackageManager.queryIntentActivities()`
2. **Fallback Handling**: If no browser is available, show a user-friendly message or offer alternative actions
3. **Use Custom Tab/WebView**: Consider using Chrome Custom Tabs or an in-app WebView instead of relying on external browser
4. **Deep Link Verification**: Ensure the S3 URL is properly formatted and accessible

### Investigation Needed
1. **Review HomeScreen.kt:271**: Examine the exact code generating the intent
2. **Check Device Inventory**: Determine if affected devices are managed/kiosk devices
3. **Analyze Full URL**: Request the complete URL from backend/API logs
4. **User Feedback**: Contact affected user(s) to understand device setup
5. **Recreate in Kiosk Mode**: Test on a device with all browsers disabled

### Code Example (Fix)
```kotlin
// Before (current - crash prone)
context.startActivity(Intent(Intent.ACTION_VIEW, uri))

// After (safe approach)
val intent = Intent(Intent.ACTION_VIEW, uri)
if (intent.resolveActivity(packageManager) != null) {
    context.startActivity(intent)
} else {
    // Show dialog: "No browser available to open this link"
    // Or open in WebView within the app
    // Or offer to copy the link to clipboard
}
```

### Long-term Recommendations
1. **Implement fallback URLs**: Provide alternative download methods
2. **Add deep linking**: Register app to handle its own links
3. **Monitor in Crashlytics**: Track this specific issue and set alerts
4. **Consider offline support**: Cache S3 resources for offline access
5. **Enterprise Device Handling**: Detect if running on managed devices and adjust behavior accordingly