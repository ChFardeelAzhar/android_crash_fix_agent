# Crash Fix Plan: `ActivityNotFoundException` on HomeScreen Tap

## Root Cause

The crash occurs when a user taps an app update UI element (dialog or banner) on the `HomeScreen`. The app attempts to open a server-provided URL (`https://bra-tools.s3.eu-west-1.amazonaws.com/...`) via an implicit `ACTION_VIEW` intent without first checking if any activity on the device can handle it. When the device lacks a web browser (or the default browser is disabled/uninstalled), calling `context.startActivity()` throws `ActivityNotFoundException`, causing a fatal crash on the main thread.

**Two identical unsafe code paths exist:**
1. `HomeScreen.kt:271` - Inside `AppUpdateDialog`'s `onUpdate` lambda
2. `HomeScreen.kt:300` - Inside `AppUpdateBanner`'s `onUpdateClick` lambda

Both execute:
```kotlin
val url = state.appUpdate?.storeUrl ?: return@...
context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
```

**Key facts:**
- URL is provided by the server via `DeviceManager`, not hardcoded
- No `PackageManager.resolveActivity()` or `try-catch` exists anywhere in the codebase
- Both UI paths (dialog for mandatory updates, banner for recommended updates) are affected

## Proposed Fix

### Strategy: Safe Intent Launch with Fallback

The minimal fix adds a `resolveActivity()` check before launching the intent. If no activity can handle the URL, a user-friendly error is shown via a Snackbar instead of crashing the app.

**Changes required:**
1. **Add a `resolveActivity()` check** before both `startActivity()` calls
2. **Add `SnackbarHostState` and coroutine scope** to show fallback message
3. **Keep the same architecture** - no structural changes to MVVM or Compose patterns

## Files To Modify

Only one file needs modification:

### 1. `app/src/main/java/com/ananinja/tms/ui/home/HomeScreen.kt`

**Add required imports:**
```kotlin
import android.content.pm.PackageManager
import androidx.compose.material.SnackbarHostState
import androidx.compose.ui.platform.LocalContext
import kotlinx.coroutines.launch
```

**Add `SnackbarHostState` to the Composable state:**

**Before:**
```kotlin
@Composable
fun HomeScreen(
    viewModel: HomeViewModel = hiltViewModel(),
    onNotificationClick: (Int) -> Unit = {},
    onReservationSelected: (Int) -> Unit = {},
    onMakeReservationSelected: () -> Unit = {},
    onDataEntryClick: () -> Unit = {},
    nestedScrollInteropSource: NestedScrollInteropSource? = null,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val snackbarHostState = remember { SnackbarHostState() }
```

**After:**
```kotlin
@Composable
fun HomeScreen(
    viewModel: HomeViewModel = hiltViewModel(),
    onNotificationClick: (Int) -> Unit = {},
    onReservationSelected: (Int) -> Unit = {},
    onMakeReservationSelected: () -> Unit = {},
    onDataEntryClick: () -> Unit = {},
    nestedScrollInteropSource: NestedScrollInteropSource? = null,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
```

**Modify the `AppUpdateDialog` lambda (around line 267-273):**

**Before:**
```kotlin
AppUpdateDialog(
    releaseNotes = state.appUpdate?.releaseNotes,
    onUpdate = {
        val url = state.appUpdate?.storeUrl ?: return@AppUpdateDialog
        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
    }
)
```

**After:**
```kotlin
AppUpdateDialog(
    releaseNotes = state.appUpdate?.releaseNotes,
    onUpdate = {
        val url = state.appUpdate?.storeUrl ?: return@AppUpdateDialog
        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
        if (intent.resolveActivity(context.packageManager) != null) {
            context.startActivity(intent)
        } else {
            scope.launch {
                snackbarHostState.showSnackbar("No browser available to open the update link")
            }
        }
    }
)
```

**Modify the `AppUpdateBanner` lambda (around line 298-300):**

**Before:**
```kotlin
onUpdateClick = {
    val url = state.appUpdate?.storeUrl ?: return@AppUpdateBanner
    context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
}
```

**After:**
```kotlin
onUpdateClick = {
    val url = state.appUpdate?.storeUrl ?: return@AppUpdateBanner
    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
    if (intent.resolveActivity(context.packageManager) != null) {
        context.startActivity(intent)
    } else {
        scope.launch {
            snackbarHostState.showSnackbar("No browser available to open the update link")
        }
    }
}
```

### Complete Before/After Sections

**Before (lines 267-273):**
```kotlin
        AppUpdateDialog(
            releaseNotes = state.appUpdate?.releaseNotes,
            onUpdate = {
                val url = state.appUpdate?.storeUrl ?: return@AppUpdateDialog
                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            }
        )
```

**After (lines 267-275):**
```kotlin
        AppUpdateDialog(
            releaseNotes = state.appUpdate?.releaseNotes,
            onUpdate = {
                val url = state.appUpdate?.storeUrl ?: return@AppUpdateDialog
                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                if (intent.resolveActivity(context.packageManager) != null) {
                    context.startActivity(intent)
                } else {
                    scope.launch {
                        snackbarHostState.showSnackbar("No browser available to open the update link")
                    }
                }
            }
        )
```

**Before (lines 296-300):**
```kotlin
                onUpdateClick = {
                    val url = state.appUpdate?.storeUrl ?: return@AppUpdateBanner
                    context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                }
```

**After (lines 298-305):**
```kotlin
                onUpdateClick = {
                    val url = state.appUpdate?.storeUrl ?: return@AppUpdateBanner
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                    if (intent.resolveActivity(context.packageManager) != null) {
                        context.startActivity(intent)
                    } else {
                        scope.launch {
                            snackbarHostState.showSnackbar("No browser available to open the update link")
                        }
                    }
                }
```

### Add Snackbar to the Scaffold (if not already present)

Check if `SnackbarHost` is already used in the `Scaffold`. If not, add it:

**Before (if no SnackbarHost):**
```kotlin
Scaffold(
    snackbarHost = { SnackbarHost(snackbarHostState) },
    // ... rest of existing parameters
)
```

**After:**
Ensure `snackbarHostState` is passed to `SnackbarHost` inside the existing `Scaffold` or add it if missing. Look for `Scaffold` definition in `HomeScreen.kt` and add:
```kotlin
snackbarHost = { SnackbarHost(snackbarHostState) },
```

## Validation Steps

### Automated Testing
1. **Unit Test for ViewModel**: Verify that when `storeUrl` is null, no intent is launched (already handled by Elvis operator - no change needed)
2. **Unit Test for Intent Resolution**: Mock `PackageManager` to return null from `resolveActivity()` and verify no crash occurs
3. **Compose UI Test**: 
   - Tap "Update" button with a mock that returns no handler
   - Verify Snackbar message appears
   - Verify no `ActivityNotFoundException` is thrown

### Manual Testing
1. **Device with browser**: Tap update button → URL should open in browser as before (no regression)
2. **Device without browser**: 
   - Use emulator with Chrome removed/disabled
   - Tap update button → Snackbar should show error message
   - App should not crash
3. **Device with null url**: Verify nothing happens (Elvis operator prevents execution)
4. **Edge cases**:
   - Malformed URL (empty string, invalid URI) - should still show Snackbar
   - Rapid taps on the button - should not cause multiple snackbars (though SnackbarHost handles this gracefully)
   - Screen rotation during Snackbar display - should not crash

### Code Review Checklist
- [ ] Imports added correctly (`PackageManager`, `SnackbarHostState`, `launch`)
- [ ] `scope` variable declared and initialized
- [ ] Both `AppUpdateDialog` and `AppUpdateBanner` paths updated
- [ ] `SnackbarHost` added to `Scaffold` (if not already present)
- [ ] No changes to `HomeViewModel`, `DeviceManager`, or data layer
- [ ] No breaking changes to existing behavior (browser-available devices work as before)
- [ ] Custom Tabs not required for this fix (would be a larger refactor)
- [ ] Error message is user-friendly and not technical

### Expected Behavior Matrix

| Scenario | Behavior |
|----------|----------|
| URL valid + browser available | Opens URL in browser (unchanged) |
| URL valid + no browser | Shows "No browser available" Snackbar |
| URL is null | Nothing happens (Elvis returns) |
| URL malformed | `Uri.parse()` may throw - but this is existing behavior; URL comes from server |

### Regression Risks
- **None identified**: The fix only adds a safety check before `startActivity()`. For devices with browsers, behavior is identical. For devices without browsers, the silent no-op becomes a user-visible Snackbar message instead of a crash.
- **Performance**: Single `PackageManager` call per button tap - negligible overhead.

### Deployment Notes
- This fix should be included in version `1.0.23` (next release)
- Consider also adding `try-catch(ActivityNotFoundException)` as a belt-and-suspenders safety measure if `PackageManager` behavior is inconsistent across OEMs:
  ```kotlin
  try {
      if (intent.resolveActivity(context.packageManager) != null) {
          context.startActivity(intent)
      } else {
          scope.launch { snackbarHostState.showSnackbar(...) }
      }
  } catch (e: ActivityNotFoundException) {
      scope.launch { snackbarHostState.showSnackbar(...) }
  }
  ```
  (Not included in minimal fix to avoid over-engineering, but easy to add if needed.)