# fix: Add missing rememberCoroutineScope to HomeScreen

## Summary

Added a missing `rememberCoroutineScope()` declaration in `HomeScreen.kt` to enable coroutine launch capabilities within the composable scope.

## Changes

- **File:** `app/src/main/java/com/ananinja/tms/ui/home/HomeScreen.kt`
- **Modification:** Added `val scope = rememberCoroutineScope()` after `snackbarHostState` declaration.
- **Purpose:** Provides the required `CoroutineScope` for launching coroutines (e.g., showing snackbars, performing async operations) from user action callbacks like button clicks, without relying on `LaunchedEffect`.

## Build Verification

| Check | Status |
|---|---|
| Compilation | ✅ SUCCESS |
| Warnings | 0 (minor cosmetic warning unrelated to change) |
| Errors | 0 |

## Related

- No breaking changes, no API modifications.
- Single insertion, backward compatible.