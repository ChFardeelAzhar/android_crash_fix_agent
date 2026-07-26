# fix: Prevent ActivityNotFoundException crash in HomeScreen.kt by wrapping startActivity in try-catch

## Description

This PR fixes an `ActivityNotFoundException` crash in `HomeScreen.kt` that occurs when the user taps on an S3 HTTPS link and no browser activity is available to handle the `Intent.ACTION_VIEW` intent.

## Changes Made

- **File:** `app/src/main/java/com/ananinja/tms/ui/home/HomeScreen.kt`
- Wrapped the `startActivity(intent)` call in a `try-catch (ActivityNotFoundException e)` block
- Added a `Toast` fallback message informing the user that no browser is available
- 9 insertions, 1 deletion

## Verification

| Check | Status |
|---|---|
| Compilation | ✅ Passed (`:app:compileDevDebugKotlin` — UP-TO-DATE, zero errors) |
| Unit Tests | ⚠️ No unit tests found for `devDebug` variant |
| Build Exit Code | ✅ `0` (SUCCESS) |

## Testing

- Build compiles successfully with zero errors
- The change is minimal and follows the existing MVVM Compose architecture
- No regression expected as the intent creation logic remains unchanged
