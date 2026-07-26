# Engineering Brief: Fix `ActivityNotFoundException` on S3 Link Tap in HomeScreen

## 1. Objective

Fix the **fatal** `android.content.ActivityNotFoundException` crash that occurs when a user taps a clickable element in the `HomeScreen` composable that attempts to open an AWS S3 HTTPS link via implicit `ACTION_VIEW` intent. The fix must be **minimal**, **safe**, and **consistent** with the existing MVVM Compose/Kotlin architecture. Do **not** add unrelated refactors, change business logic, or break existing tests.

## 2. Crash Summary

- **Exception type**: `android.content.ActivityNotFoundException`
- **Failing class/method**: `HomeScreenKt.HomeScreen$lambda$38$0$0` at line 271 in `HomeScreen.kt`
- **Stack trace**: User tap → `startActivity(Intent.ACTION_VIEW, Uri.parse("https://bra-tools.s3.eu-west-1.amazonaws.com/..."))` → No Activity found to handle the intent → crash on main thread.
- **Root cause**: The implicit intent is launched without checking if the device has a browser capable of handling the `https` scheme.
- **Severity**: CRITICAL – app crashes immediately upon user interaction, rendering the feature unusable.

## 3. Investigation Instructions

1. **Navigate to the project directory**: `/Users/retailopakistan/Documents/tp-app`
2. **Find the source file**: Search for `HomeScreen.kt` in the codebase. Do **not** assume a fixed path.
3. **Locate line 271**: Using the file content, find the lambda that starts the `ACTION_VIEW` intent. Look for code similar to:
   ```kotlin
   val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://..."))
   context.startActivity(intent)
   ```
4. **Identify the context**: Determine which `Context` is used (e.g., `LocalContext.current`) and whether the intent is built inside a composable or a ViewModel.
5. **Inspect the URI source**: Check if the URL is hardcoded, from a string resource, from a network response, or from user input. This will affect the fix strategy.
6. **Check for existing handling**: Search for any existing `try-catch` blocks, `resolveActivity` calls, or fallback mechanisms in the codebase related to external link navigation.

## 4. Fix Constraints

- **Minimal change**: Only modify the lambda at line 271 (or its immediate surrounding logic). Do **not** refactor other parts of `HomeScreen.kt`.
- **Lifecycle-safe**: The fix must be safe to call from a Composable context (main thread). Use `DisposableEffect` or `LaunchedEffect` if needed, but a simple `try-catch` with a catch handler is preferred.
- **MVVM-consistent**: Keep the `Intent` launch logic in the UI layer (Composable). Do **not** move intent handling to the ViewModel unless that pattern is already established in the codebase.
- **No test breakage**: Existing unit tests must continue to pass. If there are instrumentation tests for the composable, ensure they still compile and pass.
- **Kotlin + Compose**: Use idiomatic Kotlin. Avoid Java pattern calls if possible. Prefer `ActivityResultContracts.StartActivityForResult` if the intent needs a result, but a simple fire-and-forget is acceptable here.
- **No dependency changes**: Do **not** add new libraries or modify `build.gradle` files.

## 5. Definition of Done

- [ ] The crash is **fixed** locally on the project at `/Users/retailopakistan/Documents/tp-app`.
- [ ] The change compiles with `./gradlew assembleDebug` (or equivalent).
- [ ] The existing test suite passes with `./gradlew test`.
- [ ] The working tree is left clean (no untracked files, no temporary files) and ready for compilation.
- [ ] The fix is **directly applied** to the source tree (not a patch file or diff).

## 6. FIX_INSTRUCTION

```
FIX_INSTRUCTION
You are an expert Android Kotlin/Compose engineer. Your task is to fix a crash in the project at `/Users/retailopakistan/Documents/tp-app`.

**Crash**: `android.content.ActivityNotFoundException` in `HomeScreenKt.HomeScreen$lambda$38$0$0` at line 271 of `HomeScreen.kt`. The crash happens because an implicit `ACTION_VIEW` intent is launched with an HTTPS URL (`https://bra-tools.s3.eu-west-1.amazonaws.com/...`) but the device has no Activity to handle it.

**Your goal**: Modify the lambda at line 271 (or nearby) to safely handle the case where no browser is available. The fix must:
1. Wrap `context.startActivity(intent)` in a `try-catch` block to catch `ActivityNotFoundException`.
2. In the catch block, provide a fallback: either show a `Toast` with a user-friendly message (e.g., "No browser available to open the link") or use `SnackbarHostState` if one is already available in the composable. Do **not** crash or swallow the exception silently.
3. Optionally, add a `PackageManager.resolveActivity()` check before starting the intent to avoid the exception entirely. Use `intent.resolveActivity(packageManager) != null` to guard the `startActivity` call. If the check fails, skip the intent and show the fallback.
4. Keep the change **minimal**: only modify the lambda at line 271. Do **not** change any other lines, refactor the composable, or add new files.
5. Ensure the change compiles and does not break existing tests. Use idiomatic Kotlin/Compose.

**Instructions**:
- First, search for `HomeScreen.kt` in the project directory.
- Read the file around line 271 to understand the exact context (e.g., which `Context` is used, how the URI is obtained).
- Apply the fix directly to the source file. Do **not** create a patch file.
- After applying, run `./gradlew assembleDebug` to verify compilation.
- Run `./gradlew test` to verify no tests break.
- Leave the working tree clean.

**Do**:
- Add `try-catch` or `resolveActivity` guard.
- Show a Toast or Snackbar on failure.
- Keep the intent creation and launch as-is (only add safety around `startActivity`).

**Do not**:
- Remove or modify the intent creation logic.
- Add new imports that are not already present.
- Change any other file.
- Add comments describing the fix (code clarity is fine, but no TODO or FIXME markers).
```