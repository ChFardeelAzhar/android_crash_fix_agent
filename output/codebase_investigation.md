# Codebase Investigation Report: `ActivityNotFoundException` on HomeScreen Tap

## Relevant Files

| File | Path | Status |
|------|------|--------|
| **HomeScreen.kt** | `app/src/main/java/com/ananinja/tms/ui/home/HomeScreen.kt` | **Confirmed** - The crash occurs at line 271 |
| **HomeViewModel.kt** | `app/src/main/java/com/ananinja/tms/ui/home/HomeViewModel.kt` | **Confirmed** - Provides `state.appUpdate` with `storeUrl` |
| **AppUpdateDialog.kt** | `app/src/main/java/com/ananinja/tms/ui/components/AppUpdateDialog.kt` | **Confirmed** - Contains the `onUpdate` callback triggered by crash |
| **AppUpdateBanner.kt** | `app/src/main/java/com/ananinja/tms/ui/components/AppUpdateBanner.kt` | **Confirmed** - Contains the `onUpdateClick` callback (line 300) |
| **DeviceDtos.kt** | `network/src/main/java/com/ananinja/tms/network/dto/DeviceDtos.kt` | **Confirmed** - Defines `AppUpdateInfo.storeUrl` field |
| **DeviceManager.kt** | `app/src/main/java/com/ananinja/tms/data/local/DeviceManager.kt` | **Confirmed** - Maps server response to `AppUpdateInfo.storeUrl` |
| **MapUtil.kt** | `app/src/main/java/com/ananinja/tms/util/MapUtil.kt` | **Confirmed** - Contains `ACTION_VIEW` intents (but not related to this crash) |
| **TmsFirebaseMessagingService.kt** | `app/src/main/java/com/ananinja/tms/service/TmsFirebaseMessagingService.kt` | **Confirmed** - Contains `ACTION_VIEW` intent (but at line 197, not crash location) |

## Relevant Components

| Component | Type | Relevance |
|-----------|------|-----------|
| `HomeScreen` | @Composable function | **Primary crash site** at line 271 |
| `AppUpdateDialog` | @Composable function | **Direct trigger** - the lambda `onUpdate` calls `startActivity()` |
| `AppUpdateBanner` | @Composable function | **Secondary trigger** - same pattern at line 300 |
| `HomeViewModel` | ViewModel | Provides `state.appUpdate?.storeUrl` data |
| `DeviceManager` | Singleton service | Fetches and caches `storeUrl` from server response |
| `AppUpdateInfo` | DTO data class | Contains `storeUrl: String?` field |

## Architecture Area

**Layer:** UI Layer -> Compose Screens -> Home Screen
**Pattern:** MVVM with clean architecture
**Responsibility:** The crash occurs in the **Presentation layer** when handling a user tap on an app update UI element. The `HomeViewModel` receives `AppUpdateInfo` from `DeviceManager` (which gets it from the server via GraphQL mutation). The URL is passed as-is to `context.startActivity()` with no safety checks.

The flow is:
1. `DeviceManager` fetches device registration response containing `appUpdate.storeUrl`
2. `HomeViewModel.observeAppUpdate()` collects this and emits `ShowUpdateDialog` or `ShowUpdateBanner`
3. `HomeScreen` shows `AppUpdateDialog` or `AppUpdateBanner`
4. User taps "Update" button → lambda at line 271 or 300 executes
5. `context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))` is called **without** checking if any activity can handle the intent

## Search Queries Run

| Query | Results |
|-------|---------|
| `HomeScreen` | Found 3 occurrences: definition at line 67, import in `TmsNavGraph.kt:22`, usage at `TmsNavGraph.kt:158` |
| `HomeScreen.kt` | No results via search tool (file was found via tree tool) |
| `ActivityNotFoundException` | No results in project source code (not caught anywhere) |
| `ACTION_VIEW` | Found 5 occurrences across 3 files |
| `bra-tools.s3` | **No matches** (URL is stored on server, not hardcoded) |
| `storeUrl` | Found 4 occurrences: 2 in `HomeScreen.kt`, 2 in `DeviceManager.kt`, 1 in `DeviceDtos.kt` |
| `appUpdate` | Found in `HomeViewModel.kt`, `HomeScreen.kt`, `DeviceManager.kt` |

## Findings

### 1. Crash Location Precisely Identified
The crash occurs at **line 271** of `HomeScreen.kt`:
```kotlin
// Line 269-271 inside AppUpdateDialog's onUpdate lambda:
val url = state.appUpdate?.storeUrl ?: return@AppUpdateDialog
context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
```

And identically at **line 300** for the banner variant:
```kotlin
// Line 298-300 inside AppUpdateBanner's onUpdateClick lambda:
val url = state.appUpdate?.storeUrl ?: return@AppUpdateBanner
context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
```

### 2. Both Code Paths Are Unsafe
The crash report mentions `HomeScreen$lambda$38$0$0(HomeScreen.kt:271)`. The `$lambda$38` is the **39th** lambda defined in `HomeScreen`, which matches the `onUpdate` lambda of `AppUpdateDialog`.

### 3. URL Source is Server-Provided
The URL (`https://bra-tools.s3.eu-west-1.amazonaws.com/...`) is **not hardcoded** in the app. It comes from the server's device registration response via `DeviceManager`. The `AppUpdateInfo.storeUrl` field is set by the backend team. The truncated `...` in the crash log suggests the URL is long and may contain query parameters.

### 4. No Intent Handler Check Exists
The project source code **does not** contain any:
- `PackageManager.resolveActivity()` call
- `PackageManager.queryIntentActivities()` call
- `try-catch` for `ActivityNotFoundException`
- Fallback mechanism (WebView, Custom Tabs, dialog)

### 5. Both AppUpdate UI Elements Are Affected
Both `AppUpdateDialog` (line 271) and `AppUpdateBanner` (line 300) have identical unsafe patterns. The dialog is shown first (on app start if update is mandatory), and the banner is shown later (for recommended updates). The crash log points to line 271, which is the **dialog** path.

### 6. `MapUtil.kt` Is Not Related
The `MapUtil.kt` file also uses `ACTION_VIEW` intents (for opening maps), but those are for map navigation, not for the URL in the crash.

## Evidence From Stack Trace

The stack trace from the crash report maps directly to the source code:

```
HomeScreenKt.HomeScreen$lambda$38$0$0(HomeScreen.kt:271)
```
This refers to the lambda passed as `onUpdate` parameter of `AppUpdateDialog` at line 271:
```kotlin
// Line 267-273 in HomeScreen.kt:
AppUpdateDialog(
    releaseNotes = state.appUpdate?.releaseNotes,
    onUpdate = {
        val url = state.appUpdate?.storeUrl ?: return@AppUpdateDialog
        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))  // LINE 271
    }
)
```

The exception message confirms the exact URL pattern: `https://bra-tools.s3.eu-west-1.amazonaws.com/...`

## Files To Inspect First

1. **`app/src/main/java/com/ananinja/tms/ui/home/HomeScreen.kt`** (lines 267-303)
   - Primary crash site. Add intent resolution check before `startActivity()`.
   - Fix both the dialog (line 271) and banner (line 300) paths.

2. **`app/src/main/java/com/ananinja/tms/ui/components/AppUpdateDialog.kt`**
   - The Composable that receives and executes the `onUpdate` lambda.
   - Could optionally add a safety check here, but the real fix should be in `HomeScreen.kt`.

3. **`app/src/main/java/com/ananinja/tms/ui/components/AppUpdateBanner.kt`**
   - Same issue as dialog but for the banner variant.

4. **`network/src/main/java/com/ananinja/tms/network/dto/DeviceDtos.kt`** (line 24)
   - Confirms `storeUrl` is a `String?` - could be null, but the Elvis operator handles that.

5. **`app/src/main/java/com/ananinja/tms/data/local/DeviceManager.kt`** (lines 275-282, 308-315)
   - Where `storeUrl` is mapped from server response to local model.

6. **`app/src/main/java/com/ananinja/tms/ui/home/HomeViewModel.kt`** (lines 134-146)
   - Where app update data is observed and events are emitted.