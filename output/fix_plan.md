# Safe Minimal Crash Fix Plan for ActivityNotFoundException on HomeScreen

## Likely Root Cause

The crash is a **fatal `ActivityNotFoundException`** that occurs when the user taps the "Update" button in the `AppUpdateDialog` or `AppUpdateBanner` on the HomeScreen. The code calls `context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))` without any safety check, and the device does not have any app capable of handling `https://` URLs (no browser installed, browser disabled, or kiosk-mode device).

**Exact crash points in `HomeScreen.kt`:**
- **Line 271** — inside `AppUpdateDialog.onUpdate` callback
- **Line 300** — inside `AppUpdateBanner.onUpdateClick` callback

Both call sites use:
```kotlin
val url = state.appUpdate?.storeUrl ?: return@AppUpdateDialog
context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
```

There is **no `resolveActivity()` check** and **no try-catch** for `ActivityNotFoundException` anywhere in the project for these code paths.

## Proposed Fix

Apply **minimal, targeted changes** to both call sites in `HomeScreen.kt`:

1. **Add `import android.content.ActivityNotFoundException`** at the top of the file.
2. **Replace the unsafe `context.startActivity()` call** in the `AppUpdateDialog.onUpdate` lambda with a safe version that:
   - Creates the intent
   - Checks `intent.resolveActivity(context.packageManager) != null`
   - Wraps `startActivity()` in a try-catch for `ActivityNotFoundException`
   - Shows a user-friendly Snackbar on failure
3. **Apply the exact same fix** to the `AppUpdateBanner.onUpdateClick` lambda.

## Files Modified

| File | Lines Modified | Change Type |
|------|---------------|-------------|
| `app/src/main/java/com/ananinja/tms/ui/home/HomeScreen.kt` | Import block (add `ActivityNotFoundException`) + 2 call sites (~lines 269-272 and ~lines 299-302) | **Add safety checks** |

## Kotlin / Compose Change Notes

### Import Addition (top of file)
```kotlin
import android.content.ActivityNotFoundException
```

### Change 1: AppUpdateDialog.onUpdate (around line 271)
**Before:**
```kotlin
val url = state.appUpdate?.storeUrl ?: return@AppUpdateDialog
context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
```

**After:**
```kotlin
val url = state.appUpdate?.storeUrl ?: return@AppUpdateDialog
val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
try {
    if (intent.resolveActivity(context.packageManager) != null) {
        context.startActivity(intent)
    } else {
        snackbarHostState.showSnackbar("Unable to open app store link. No browser available.")
    }
} catch (e: ActivityNotFoundException) {
    snackbarHostState.showSnackbar("Unable to open app store link.")
}
```

### Change 2: AppUpdateBanner.onUpdateClick (around line 300)
**Before:**
```kotlin
val url = state.appUpdate?.storeUrl ?: return@AppUpdateBanner
context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
```

**After:**
```kotlin
val url = state.appUpdate?.storeUrl ?: return@AppUpdateBanner
val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
try {
    if (intent.resolveActivity(context.packageManager) != null) {
        context.startActivity(intent)
    } else {
        snackbarHostState.showSnackbar("Unable to open app store link. No browser available.")
    }
} catch (e: ActivityNotFoundException) {
    snackbarHostState.showSnackbar("Unable to open app store link.")
}
```

## File Edit Tool Execution

I applied the changes to `HomeScreen.kt`. The tool confirmed:

1. **Successfully found and replaced** the `onUpdate = {` marker line.
2. **Successfully found and replaced** the `import android.content.Intent` line (to add the import).

However, the exact multiline replacement for the `context.startActivity(...)` call could not be matched precisely due to whitespace/indentation differences. The import and first target line have been applied successfully. The remaining changes need the backup file to be restored and a more precise edit attempted, or the changes can be verified directly in the file.

## Gradle Verify Tool Execution

```bash
# Run from project root /Users/retailopakistan/Documents/tp-app
cd /Users/retailopakistan/Documents/tp-app
./gradlew assembleDebug
```

**Compilation Status:** PENDING — The Gradle build needs to be run to confirm the changes compile successfully.

**Unit Tests Status:** PENDING — Unit tests need to be run via `./gradlew testDebugUnitTest`.

I will now attempt the remaining file edits with precise content matching, then run the Gradle verify tool.

<｜｜DSML｜｜tool_calls>
<｜｜DSML｜｜invoke name="file_edit_tool">
<｜｜DSML｜｜parameter name="android_project_path" string="true">/Users/retailopakistan/Documents/tp-app</｜｜DSML｜｜parameter>
<｜｜DSML｜｜parameter name="relative_file_path" string="true">app/src/main/java/com/ananinja/tms/ui/home/HomeScreen.kt</｜｜DSML｜｜parameter>
<｜｜DSML｜｜parameter name="target_content" string="true">context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))</｜｜DSML｜｜parameter>
<｜｜DSML｜｜parameter name="replacement_content" string="true">val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                try {
                    if (intent.resolveActivity(context.packageManager) != null) {
                        context.startActivity(intent)
                    } else {
                        snackbarHostState.showSnackbar("Unable to open app store link. No browser available.")
                    }
                } catch (e: ActivityNotFoundException) {
                    snackbarHostState.showSnackbar("Unable to open app store link.")
                }</｜｜DSML｜｜parameter>
</｜｜DSML｜｜invoke>
</｜｜DSML｜｜tool_calls>