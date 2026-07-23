# Fix ActivityNotFoundException Crash When Opening App Update URL on HomeScreen

## Summary
Fixes a fatal ActivityNotFoundException crash on the HomeScreen when the user taps the Update button. The crash occurs because context.startActivity is called without checking if any installed app can handle the https URL.

## Changes
- Added import for ActivityNotFoundException
- Added resolveActivity check before both startActivity calls
- Wrapped startActivity in try-catch for ActivityNotFoundException
- Shows user-friendly Snackbar on failure

## Files Modified
- app/src/main/java/com/ananinja/tms/ui/home/HomeScreen.kt

## Testing
- Compilation: PENDING
- Unit tests: PENDING