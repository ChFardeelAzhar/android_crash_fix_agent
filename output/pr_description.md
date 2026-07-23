# Fix unresolved reference safeOpenUrl in HomeScreen.kt

## Summary

Fixed the **safeOpenUrl** unresolved reference errors in `HomeScreen.kt` that caused the `:app:compileDevDebugKotlin` build to fail.

## Changes

- **app/src/main/java/com/ananinja/tms/ui/home/HomeScreen.kt**
  - Added the missing import for `safeOpenUrl` utility function
  - Resolved compilation errors at lines 277 and 306

## Root Cause

The function `safeOpenUrl` was called on lines 277 and 306 but was neither imported nor defined in the file scope, leading to two **Unresolved reference** errors during Kotlin compilation.

## Build Verification

- ✅ `:app:compileDevDebugKotlin` passes
- ✅ All unit tests green

## Related Issue

Fixes the build failure reported in the Android Build Verification Report.