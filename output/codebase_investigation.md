# Codebase Investigation Report — `ActivityNotFoundException` on HomeScreen

## Relevant Files

| File Path | Status | Relevance |
|-----------|--------|-----------|
| `app/src/main/java/com/ananinja/tms/ui/home/HomeScreen.kt` | **Confirmed** (read via file_read_tool) | Primary crash origin — contains two `Intent(Intent.ACTION_VIEW, ...)` calls at lines 271 and 300 |
| `app/src/main/java/com/ananinja/tms/ui/home/HomeViewModel.kt` | **Confirmed** | Contains `HomeUiState.appUpdate` which provides the `storeUrl` used in the intent |
| `app/src/main/java/com/ananinja/tms/ui/components/AppUpdateDialog.kt` | **Confirmed** | Contains `onUpdate` callback that triggers `context.startActivity()` |
| `app/src/main/java/com/ananinja/tms/ui/components/AppUpdateBanner.kt` | **Confirmed** | Contains `onUpdateClick` callback that triggers `context.startActivity()` |
| `network/src/main/java/com/ananinja/tms/network/dto/DeviceDtos.kt` | **Confirmed** | Defines `AppUpdateInfo` data class with nullable `storeUrl` field |
| `app/src/main/java/com/ananinja/tms/data/local/DeviceManager.kt` | **Confirmed** | Fetches and exposes `AppUpdateInfo` including `storeUrl` from the server |
| `app/src/main/java/com/ananinja/tms/ui/navigation/TmsNavGraph.kt` | **Confirmed** | Composable navigation graph that hosts `HomeScreen` |
| `app/src/main/AndroidManifest.xml` | **Confirmed** | No `<queries>` element for browser/app resolution (relevant for API 30+) |
| `app/src/main/java/com/ananinja/tms/util/MapUtil.kt` | **Confirmed** | Demonstrates that `resolveActivity()` checks exist elsewhere but were not applied to the crash path |

## Relevant Components

| Component | Type | Role in Crash |
|-----------|------|---------------|
| `HomeScreen` | Composable function | Crash occurs inside `HomeScreen$lambda$38$0$0` — the lambda inside the `onUpdate` or `onUpdateClick` callback |
| `AppUpdateDialog` | Composable component | Contains `onUpdate` lambda that calls `context.startActivity()` with `Intent.ACTION_VIEW` |
| `AppUpdateBanner` | Composable component | Contains `onUpdateClick` lambda that calls `context.startActivity()` with `Intent.ACTION_VIEW` |
| `HomeViewModel` | ViewModel | Emits `HomeEvent.ShowUpdateDialog` or `HomeEvent.ShowUpdateBanner` based on `appUpdate.updateAction` |
| `DeviceManager` | Singleton (data layer) | Fetches `storeUrl` from backend API via `DevicesMeQuery` and exposes it as `appUpdate` StateFlow |
| `AppUpdateInfo` | DTO (data class) | Contains `storeUrl: String?` — the URL that the app tries to open |
| `MainActivity` | Android Activity | Hosts the Compose content; the `startActivity` call originates from this context |

## Architecture Area

**Affected Layer:** UI Layer (Compose) — specifically the App Update Dialog/Banner interaction flow

**Data Flow of the Crash:**
```
DeviceManager.fetchDeviceMe()
    → DevicesMeQuery (GraphQL)
        → returns AppUpdateInfo(storeUrl = "https://bra-tools.s3.eu-west-1.amazonaws.com/...")
    → _appUpdate.value = device.appUpdate   [DeviceManager.kt:123]
        → HomeViewModel.observeAppUpdate()     [HomeViewModel.kt:134-147]
            → if (updateAction == RECOMMENDED) emit ShowUpdateBanner
            → else emit ShowUpdateDialog
                → HomeScreen LaunchedEffect catches event, sets showUpdateDialog/showUpdateBanner = true
                    → User clicks "Update" button
                        → lambda: context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                            → CRASH: ActivityNotFoundException
```

## Search Queries Run

| Query | Tool | Results |
|-------|------|---------|
| `HomeScreen` | `project_search_tool` | 3 matches — confirmed crash file location |
| `ACTION_VIEW` | `project_search_tool` | 4 matches — 2 in `HomeScreen.kt` (lines 271, 300), 1 in `MapUtil.kt`, 1 in `TmsFirebaseMessagingService.kt` |
| `storeUrl` | `project_search_tool` | 4 matches — 2 in `HomeScreen.kt`, 2 in `DeviceManager.kt` |
| `AppUpdateInfo` | `project_search_tool` | 8 matches — across `HomeViewModel.kt`, `DeviceManager.kt`, `DeviceDtos.kt` |
| `s3.amazonaws.com` | `project_search_tool` | **0 matches** — URL is fetched from server, not hardcoded |
| `bra-tools` | `project_search_tool` | **0 matches** — URL is fetched from server, not hardcoded |
| `ActivityNotFoundException` | `project_search_tool` | **0 matches** — no try-catch for this exception anywhere |
| `try.*startActivity` | `project_search_tool` | **0 matches** — no try-catch wrapping `startActivity()` for the app update path |
| `resolveActivity` | `project_search_tool` | **1 match** — only in `MapUtil.kt`, NOT in the crash path |

## Findings

1. **Exact Crash Origin:** The crash originates from **two identical code paths** in `HomeScreen.kt`:
   - **Line 271** (inside `AppUpdateDialog.onUpdate` callback):
     ```kotlin
     val url = state.appUpdate?.storeUrl ?: return@AppUpdateDialog
     context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
     ```
   - **Line 300** (inside `AppUpdateBanner.onUpdateClick` callback):
     ```kotlin
     val url = state.appUpdate?.storeUrl ?: return@AppUpdateBanner
     context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
     ```

2. **No Safety Check:** Neither code path performs a `PackageManager.resolveActivity()` check before launching the intent. The `MapUtil.kt` file (line 13) demonstrates that the development team is aware of this pattern (`if (mapsIntent.resolveActivity(context.packageManager) != null)`), but it was **not applied** to the app update URLs.

3. **No Exception Handling:** There is **no try-catch** for `ActivityNotFoundException` anywhere in the project. A search for `ActivityNotFoundException` returned zero results.

4. **URL Source:** The `storeUrl` is dynamically fetched from the server via GraphQL `DevicesMeQuery`. The URL `https://bra-tools.s3.eu-west-1.amazonaws.com/...` is **not hardcoded** in the source code — it comes from the backend's `appUpdate.storeUrl` field. This means:
   - The URL is an AWS S3 bucket link (likely hosting an APK or app bundle)
   - The server controls which URL is sent
   - The crash is not reproducible with a static URL but depends on the server response

5. **Android 11+ Package Visibility:** The `AndroidManifest.xml` does **not** contain a `<queries>` element to declare intent queries for browsers or web-handling apps. On Android 11+ (API 30+), `PackageManager.queryIntentActivities()` is restricted unless explicitly declared, but since the code doesn't even call `resolveActivity()`, this is a secondary concern.

6. **Device Scenario:** The `storeUrl` points to `bra-tools.s3.eu-west-1.amazonaws.com` — an AWS S3 bucket. If the device has no browser or app that can handle `https://` URLs, the crash occurs. This could happen on:
   - Kiosk/enterprise devices with browsers disabled
   - Emulators without Google services/browser
   - Devices with restricted profiles
   - Devices where the default browser was uninstalled or disabled

7. **Lambda Mapping:** The stack trace reports `HomeScreenKt.HomeScreen$lambda$38$0$0` at line 271. The lambda `$lambda$38` corresponds to the `onUpdate` callback of `AppUpdateDialog` (line 269-272 of HomeScreen.kt).

## Evidence From Stack Trace

```
com.ananinja.tms.ui.home.HomeScreenKt.HomeScreen$lambda$38$0$0(HomeScreen.kt:271)
```

This maps directly to:
```kotlin
AppUpdateDialog(
    releaseNotes = state.appUpdate?.releaseNotes,
    onUpdate = {                    // ← lambda $38 starts here
        val url = state.appUpdate?.storeUrl ?: return@AppUpdateDialog
        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
    }                               // ← lambda $38 ends here
)
```

The stack trace continues:
```
Instrumentation.checkStartActivityResult()  ← throws ActivityNotFoundException
Instrumentation.execStartActivity()
Activity.startActivityForResult()
Activity.startActivity()
```

This confirms the `context.startActivity()` call inside the lambda is the exact crash point.

## Files To Inspect First

1. **`app/src/main/java/com/ananinja/tms/ui/home/HomeScreen.kt`** (lines 265-304)
   - **Action:** Add `resolveActivity()` check before both `startActivity()` calls
   - **Action:** Wrap both `startActivity()` calls in try-catch for `ActivityNotFoundException`

2. **`app/src/main/java/com/ananinja/tms/ui/components/AppUpdateDialog.kt`**
   - **Action:** Consider accepting context + URL as parameters and handling safety checks in the composable itself

3. **`app/src/main/java/com/ananinja/tms/ui/components/AppUpdateBanner.kt`**
   - **Action:** Same as above — add safety checks

4. **`app/src/main/AndroidManifest.xml`**
   - **Action:** Add `<queries>` element for Android 11+ targeting:
   ```xml
   <queries>
       <intent>
           <action android:name="android.intent.action.VIEW" />
           <data android:scheme="https" />
       </intent>
   </queries>
   ```

5. **`app/src/main/java/com/ananinja/tms/ui/home/HomeViewModel.kt`**
   - **Action:** Consider adding a `fallbackUrl` or validation logic before emitting `showUpdateDialog`/`showUpdateBanner`

6. **`network/src/main/java/com/ananinja/tms/network/dto/DeviceDtos.kt`**
   - **Action:** Add validation/documentation that `storeUrl` must be a valid, accessible URL

## Recommended Fix (Minimal)

```kotlin
// In HomeScreen.kt, lines 269-272 and 299-302, replace:
context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))

// With:
val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
if (intent.resolveActivity(context.packageManager) != null) {
    context.startActivity(intent)
} else {
    // Log to crashlytics and show user a snackbar
    snackbarHostState.showSnackbar("Unable to open app store link")
}
```