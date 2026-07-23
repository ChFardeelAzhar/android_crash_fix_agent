# Codebase Investigation Report: ActivityNotFoundException in HomeScreen

## Relevant Files

| File | Role | Status |
|------|------|--------|
| `app/src/main/java/com/ananinja/tms/ui/home/HomeScreen.kt` | **Primary crash location** — lines 270-271 contain the `startActivity` call that fails | ✅ **Confirmed** |
| `app/src/main/java/com/ananinja/tms/ui/home/HomeViewModel.kt` | Provides `state.appUpdate` (contains `storeUrl`) | ✅ **Confirmed** |
| `app/src/main/java/com/ananinja/tms/ui/components/AppUpdateDialog.kt` | Dialog that triggers the `onUpdate` lambda (line 71 calls `onUpdate` which invokes the crash) | ✅ **Confirmed** |
| `app/src/main/java/com/ananinja/tms/ui/components/AppUpdateBanner.kt` | Banner that similarly triggers `onUpdateClick` which invokes the same crash path | ✅ **Confirmed** |
| `network/src/main/java/com/ananinja/tms/network/dto/DeviceDtos.kt` | Defines `AppUpdateInfo` DTO with `storeUrl: String?` field | ✅ **Confirmed** |
| `app/src/main/java/com/ananinja/tms/data/local/DeviceManager.kt` | Provides `appUpdate` flow; maps `storeUrl` from API response | ✅ **Confirmed** |
| `app/src/main/java/com/ananinja/tms/ui/home/tabs/ProfileTab.kt` | Contains another `startActivity` call (line 544, unrelated to this crash) | ✅ **Confirmed** |

## Relevant Components

| Component | Type | Description |
|-----------|------|-------------|
| `HomeScreen` | Compose `@Composable` | Contains the failing lambda at line 271 |
| `AppUpdateDialog` | Compose `@Composable` Dialog | "Update available" dialog with "Update" button |
| `AppUpdateBanner` | Compose `@Composable` Banner | Non-blocking "Update available" banner |
| `HomeViewModel` | ViewModel (Hilt) | Observes `deviceManager.appUpdate` flow, emits events to show dialog/banner |
| `DeviceManager` | Local data manager | Polls/observes app update info from API |
| `AppUpdateInfo` | DTO (`data class`) | Contains `storeUrl` field — the URL used in the failing intent |

## Architecture Area

**UI Layer → Compose UI (HomeScreen) → App Update Flow**

The crash occurs in the **app update** feature, specifically when a user taps "Update" on either:
- `AppUpdateDialog` (mandatory update — shown on app launch)
- `AppUpdateBanner` (recommended update — shown on Active/History tabs)

The `storeUrl` value comes from the backend API response, mapped through `DeviceManager` and served to UI via `HomeViewModel.state.appUpdate.storeUrl`.

The crash is **not** in the core job order / driver queue / tracking functionality, but in the **app update prompt UI**.

## Search Queries Run

| Query | Results | Notes |
|-------|---------|-------|
| `startActivity` | 6 matches | Found in `HomeScreen.kt` (lines 169, 271, 300), `ProfileTab.kt` (line 544), `MapUtil.kt` (lines 14, 17) |
| `Intent.ACTION_VIEW` | 5 matches | Two are the failing calls (lines 271, 300 in `HomeScreen.kt`); others are maps and deep link intents |
| `storeUrl` | 5 matches | Used in `HomeScreen.kt` (2x), `DeviceManager.kt` (2x), `DeviceDtos.kt` (1x) |
| `resolveActivity` | 1 match | Only used in `MapUtil.kt`; **not** used anywhere near the crash site |
| `No Activity found` | 0 matches | No custom try-catch or error handling exists for this scenario |

## Findings

1. **CRASH IS IN APP UPDATE FLOW — NOT IN A JOB ORDER / DOCUMENT LINK**

   The crash report mentions URL `https://bra-tools.s3.eu-west-1.amazonaws.com/...` which appears to be an **app store URL** for the app update. The app likely hosts its APK on S3 (since the app package is `com.ananinja.tms` and is distributed outside Google Play). The `storeUrl` field in `AppUpdateInfo` DTO receives this S3 URL from the backend.

2. **TWO CRASH SITES — SAME CAUSE**

   Both sites in `HomeScreen.kt` have the identical unsafe pattern:
   ```kotlin
   // Line 271 (AppUpdateDialog onUpdate)
   context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
   
   // Line 300 (AppUpdateBanner onUpdateClick)
   context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
   ```

3. **NO SAFETY CHECK EXISTS**

   The app has only **one** example of safe intent resolution (`MapUtil.kt` line 13 uses `resolveActivity`), but this pattern is **not** applied to the app update flow.

4. **THE `storeUrl` IS A URL TO AN S3-HOSTED APK**

   The `bra-tools.s3.eu-west-1.amazonaws.com` bucket hosts the APK file. When the user taps "Update", the app tries to open this URL in a browser to download the APK. On devices without a browser (enterprise/kiosk devices), this crashes.

5. **THE HOME VIEW MODEL FLOW**

   `DeviceManager.appUpdate` → `HomeViewModel.observeAppUpdate()` → emits `ShowUpdateDialog` or `ShowUpdateBanner` → UI shows dialog/banner → user taps "Update" → **CRASH**

## Evidence From Stack Trace

| Stack Frame | Mapped File | Line |
|-------------|------------|------|
| `com.ananinja.tms.ui.home.HomeScreenKt.HomeScreen$lambda$38$0$0` | `HomeScreen.kt` | 271 |
| `Intent.ACTION_VIEW` usage with `Uri.parse(url)` | `HomeScreen.kt` | 271 |
| `url = state.appUpdate?.storeUrl` | `HomeScreen.kt` | 270 |
| `AppUpdateDialog` → `Button(onClick = onUpdate)` | `AppUpdateDialog.kt` | 71 |
| `HomeViewModel.observeAppUpdate()` emits events | `HomeViewModel.kt` | 134-147 |
| `AppUpdateInfo.storeUrl` is nullable String | `DeviceDtos.kt` | 24 |

The stack trace shows the lambda `$lambda$38$0$0` corresponds to the `onUpdate` callback of `AppUpdateDialog`, confirming the user tapped "Update" in the mandatory update dialog.

## Files To Inspect First

| Priority | File | Reason |
|----------|------|--------|
| **1** | `app/src/main/java/com/ananinja/tms/ui/home/HomeScreen.kt` (lines 266-274 and 296-304) | **Primary crash site** — needs `resolveActivity` check before `startActivity` |
| **2** | `app/src/main/java/com/ananinja/tms/ui/components/AppUpdateDialog.kt` | Dialog UI; consider adding fallback (e.g., copy link to clipboard) when no browser available |
| **3** | `app/src/main/java/com/ananinja/tms/ui/components/AppUpdateBanner.kt` | Banner UI; same fallback consideration |
| **4** | `app/src/main/java/com/ananinja/tms/ui/home/HomeViewModel.kt` (lines 134-147) | ViewModel logic that triggers the update UI; consider adding error handling |
| **5** | `network/src/main/java/com/ananinja/tms/network/dto/DeviceDtos.kt` | DTO definition; verify if `storeUrl` could be validated earlier |
| **6** | `app/src/main/java/com/ananinja/tms/data/local/DeviceManager.kt` (lines around 279, 312) | Source of `storeUrl` data; consider adding URL validation |
| **7** | `app/src/main/java/com/ananinja/tms/util/MapUtil.kt` | **Reference implementation** — shows the correct `resolveActivity` pattern already used elsewhere |

### Immediate Fix Required

Add intent resolution check before both `startActivity` calls in `HomeScreen.kt`:

```kotlin
// Lines 270-271 and 299-300 should become:
val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
if (intent.resolveActivity(context.packageManager) != null) {
    context.startActivity(intent)
} else {
    // Fallback: show snackbar "No browser available to download update"
    // Or: copy URL to clipboard with message
    // Or: log to Crashlytics with full URL for debugging
}
```