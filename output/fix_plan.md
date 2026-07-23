# Crash Fix Plan: ActivityNotFoundException in HomeScreen

## Root Cause

The app crashes with `ActivityNotFoundException` when a user taps the "Update" button in either the `AppUpdateDialog` or the `AppUpdateBanner`. The root cause is that the code directly calls `context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))` without first checking whether any installed Activity can handle the intent. This is a fatal exception that terminates the app immediately.

The crash occurs in two locations in `HomeScreen.kt`:
- **Line 271**: Inside the `AppUpdateDialog`'s `onUpdate` lambda
- **Line 300**: Inside the `AppUpdateBanner`'s `onUpdateClick` lambda (based on the codebase investigation showing two identical unsafe sites)

The `storeUrl` value from the backend points to an Amazon S3-hosted APK (`https://bra-tools.s3.eu-west-1.amazonaws.com/...`). On devices without a browser (common in enterprise/kiosk deployments), the intent resolution fails catastrophically.

## Proposed Fix

Apply a safe intent resolution check before both `startActivity` calls. The fix will:
1. Create a helper function to safely launch intents with fallback handling
2. Use `PackageManager.resolveActivity()` to verify an Activity can handle the intent
3. If no handler exists, show a Snackbar to inform the user and optionally copy the URL to clipboard
4. Keep the change minimal — only modify `HomeScreen.kt`

## Files To Modify

Only one file needs modification:

**`app/src/main/java/com/ananinja/tms/ui/home/HomeScreen.kt`**

### Changes Summary:
1. Add imports for `SnackbarHostState`, `ClipboardManager`, `ClipData`, and `Context`
2. Add a private helper function `safeOpenUrl` in the HomeScreen composable scope
3. Replace the two unsafe `startActivity` calls with the safe helper

### Exact Code Changes

#### Change 1: Add Required Imports

**Before:**
```kotlin
package com.ananinja.tms.ui.home

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import coil.compose.AsyncImage
import com.ananinja.tms.ui.components.AppUpdateBanner
import com.ananinja.tms.ui.components.AppUpdateDialog
import com.ananinja.tms.ui.components.LoadingProgressIndicator
import com.ananinja.tms.ui.components.TopBarWithTitle
```

**After:**
```kotlin
package com.ananinja.tms.ui.home

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import coil.compose.AsyncImage
import com.ananinja.tms.ui.components.AppUpdateBanner
import com.ananinja.tms.ui.components.AppUpdateDialog
import com.ananinja.tms.ui.components.LoadingProgressIndicator
import com.ananinja.tms.ui.components.TopBarWithTitle
```

#### Change 2: Replace `startActivity` at Lines 270-271 (AppUpdateDialog onUpdate)

**Before:**
```kotlin
        sentAppUpdateDialogState?.let { event ->
            AppUpdateDialog(
                onDismiss = { viewModel.onDialogDismissed() },
                onUpdate = {
                    val url = state.appUpdate?.storeUrl ?: return@AppUpdateDialog
                    context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                },
                ...
            )
        }
```

**After:**
```kotlin
        sentAppUpdateDialogState?.let { event ->
            AppUpdateDialog(
                onDismiss = { viewModel.onDialogDismissed() },
                onUpdate = {
                    val url = state.appUpdate?.storeUrl ?: return@AppUpdateDialog
                    safeOpenUrl(context, url, snackbarHostState)
                },
                ...
            )
        }
```

#### Change 3: Replace `startActivity` at Lines 299-300 (AppUpdateBanner onUpdateClick)

**Before:**
```kotlin
                    AppUpdateBanner(
                        updateInfo = requireNotNull(state.appUpdate),
                        onUpdateClick = {
                            val url = state.appUpdate?.storeUrl ?: return@AppUpdateBanner
                            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                        },
                        onDismiss = { viewModel.onAppUpdateBannerDismissed() },
                    )
```

**After:**
```kotlin
                    AppUpdateBanner(
                        updateInfo = requireNotNull(state.appUpdate),
                        onUpdateClick = {
                            val url = state.appUpdate?.storeUrl ?: return@AppUpdateBanner
                            safeOpenUrl(context, url, snackbarHostState)
                        },
                        onDismiss = { viewModel.onAppUpdateBannerDismissed() },
                    )
```

#### Change 4: Update `snackbarHostState` Declaration (if not already present)

**If `snackbarHostState` is not already declared:**
Add this before the `Scaffold` call:
```kotlin
val snackbarHostState = remember { SnackbarHostState() }
```

**If `snackbarHostState` is already declared** (common in HomeScreen): Ensure it is passed to the scaffold and accessible in the lambda scopes.

#### Change 5: Add Helper Function and Update Scaffold

**Before (find the `Scaffold` call and its content area):**
```kotlin
@Composable
fun HomeScreen(
    ...
) {
    val context = LocalContext.current
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }
    
    Scaffold(
        snackbarHost = { SnackbarHost(hostState = snackbarHostState) },
        ...
    ) { paddingValues ->
        // Main content
    }
}
```

**After (add private helper function inside the composable, and update the snackbar host):**
```kotlin
@Composable
fun HomeScreen(
    ...
) {
    val context = LocalContext.current
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }
    
    Scaffold(
        snackbarHost = { SnackbarHost(hostState = snackbarHostState) },
        ...
    ) { paddingValues ->
        // Main content
    }
}

private fun safeOpenUrl(context: Context, url: String, snackbarHostState: SnackbarHostState) {
    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
    if (intent.resolveActivity(context.packageManager) != null) {
        context.startActivity(intent)
    } else {
        // Fallback: copy URL to clipboard and show snackbar
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val clip = ClipData.newPlainText("Update URL", url)
        clipboard.setPrimaryClip(clip)
        
        // Show snackbar with a coroutine scope
        kotlinx.coroutines.MainScope().launch {
            snackbarHostState.showSnackbar(
                message = "No browser found. Update URL copied to clipboard.",
                duration = SnackbarDuration.Long
            )
        }
    }
}
```

**IMPORTANT**: Add the required import for CoroutineScope at the top of the file:
```kotlin
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch
```

### Complete Modified Section (Lines 260-305, showing both fix sites)

Here is the complete Section showing the relevant area after modifications (providing context for clear parsing):

```kotlin
        sentAppUpdateDialogState?.let { event ->
            AppUpdateDialog(
                onDismiss = { viewModel.onDialogDismissed() },
                onUpdate = {
                    val url = state.appUpdate?.storeUrl ?: return@AppUpdateDialog
                    safeOpenUrl(context, url, snackbarHostState)
                },
                updateInfo = requireNotNull(state.appUpdate),
                packageName = context.packageName,
            )
        }

        // Handle app update banner
        sentAppUpdateBannerState?.let { event ->
            if (state.appUpdate != null) {
                // ... existing code around the banner ...
                    AppUpdateBanner(
                        updateInfo = requireNotNull(state.appUpdate),
                        onUpdateClick = {
                            val url = state.appUpdate?.storeUrl ?: return@AppUpdateBanner
                            safeOpenUrl(context, url, snackbarHostState)
                        },
                        onDismiss = { viewModel.onAppUpdateBannerDismissed() },
                    )
                // ... existing code after the banner ...
            }
        }
```

### Complete Helper Function (to be added after the HomeScreen composable but before any other top-level functions)

```kotlin
/**
 * Safely opens a URL in an external browser. If no browser is available,
 * copies the URL to the clipboard and shows a snackbar notification.
 *
 * @param context The Android context for starting activities
 * @param url The URL to open
 * @param snackbarHostState The snackbar host state for showing notifications
 */
private fun safeOpenUrl(context: Context, url: String, snackbarHostState: SnackbarHostState) {
    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
    if (intent.resolveActivity(context.packageManager) != null) {
        context.startActivity(intent)
    } else {
        // Copy URL to clipboard as fallback
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val clip = ClipData.newPlainText("Update URL", url)
        clipboard.setPrimaryClip(clip)
        
        // Show snackbar notification using a coroutine
        CoroutineScope(Dispatchers.Main).launch {
            snackbarHostState.showSnackbar(
                message = "No browser available. Update URL copied to clipboard.",
                duration = SnackbarDuration.Long
            )
        }
    }
}
```

**Additional Imports Needed for the Helper Function:**
```kotlin
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
```

## Validation Steps

### 1. Unit Testing
- **Test `safeOpenUrl` function isolation** (after extracting to utility class if desired)
- **Test with valid URL**: Verify `startActivity` is called when `resolveActivity` returns non-null
- **Test with no browser**: Verify snackbar is shown and URL is copied to clipboard
- **Test with null/short URL**: Verify no crash occurs with malformed URLs

### 2. Manual Testing
- **Normal Device with Browser**: Tap "Update" in dialog and banner → App should open browser with the S3 URL
- **Device with Browser Disabled**: 
  - Use Android Device Policy or test app to disable all browsers
  - Tap "Update" → Should see snackbar "No browser available. Update URL copied to clipboard."
  - Verify URL is in clipboard
- **Kiosk/Enterprise Mode**: Run in managed configuration → Should not crash
- **No Browser Installed**: 
  - Use emulator without browser (remove Chrome via ADB)
  - Tap "Update" → Should show snackbar fallback

### 3. Integration Testing
- **Verify SnackbarHostState is properly connected**: Ensure the snackbar actually displays
- **Verify ViewModel state flow**: Ensure the `state.appUpdate?.storeUrl` is not consumed incorrectly
- **Verify backward compatibility**: Test on Android API 24+ (minSdk likely)

### 4. Regression Testing
- **Verify existing MapUtil.kt functionality**: Ensure no regression in the existing `resolveActivity` usage
- **Verify ProfileTab.kt `startActivity`**: Ensure that unrelated `startActivity` in ProfileTab (line 544) is not affected
- **Full smoke test**: Navigate through HomeScreen, dialogs, banners, and ensure no new issues

### 5. Crashlytics Monitoring
- **Deploy fix and monitor**: Track issue `9b26cd77e392a55e6224dcfd78f509f7` for 1-2 weeks
- **Verify crash rate drops to zero**: The `ActivityNotFoundException` should no longer occur
- **Monitor new `snackbar` related crashes**: Ensure the coroutine scope doesn't leak or cause lifecycle issues

### 6. Edge Cases
- **Empty URL string**: Test if `storeUrl` returns `""` empty string (should still attempt to open, but `resolveActivity` will fail gracefully)
- **Non-HTTP URL**: Test with `market://` or custom scheme (should check for appropriate handlers)
- **Rapid multiple taps**: Test tapping "Update" rapidly → Only first tap should start activity (subsequent taps may fail `resolveActivity` but should not crash)
- **Configuration changes**: Rotate screen while snackbar is showing → Snackbar should survive (state is `remember`d)

### 7. Code Review Checklist
- [ ] Both `startActivity` calls replaced with `safeOpenUrl`
- [ ] `snackbarHostState` is properly `remember`ed and accessible
- [ ] `ClipboardManager` import and usage correct
- [ ] `CoroutineScope` not leaking (scope not tied to composable lifecycle could cause issues; consider using `rememberCoroutineScope()` instead of `MainScope()`)

### 8. Optimization Consideration (Secondary Improvement)

For a more robust solution, consider using `rememberCoroutineScope()` instead of `MainScope()` in the helper function to be lifecycle-aware:

**Alternative Helper (preferred for production):**
```kotlin
@Composable
private fun rememberSafeOpenUrl(): (String) -> Unit {
    val context = LocalContext.current
    val snackbarHostState = LocalSnackbarHostState.current
    val scope = rememberCoroutineScope()
    
    return { url ->
        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
        if (intent.resolveActivity(context.packageManager) != null) {
            context.startActivity(intent)
        } else {
            val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val clip = ClipData.newPlainText("Update URL", url)
            clipboard.setPrimaryClip(clip)
            
            scope.launch {
                snackbarHostState.showSnackbar(
                    message = "No browser available. Update URL copied to clipboard.",
                    duration = SnackbarDuration.Long
                )
            }
        }
    }
}
```

This alternative uses Compose lifecycle-aware coroutine scopes and local composition locals, but adds more complexity. The proposed minimal fix with `MainScope()` is acceptable for crash prevention, but the `rememberCoroutineScope()` approach is recommended for a production-grade solution in a subsequent iteration.