# Add manual toss winner selection feature

## Summary

Implements a manual toss winner selection feature on the Toss screen, allowing users to directly choose which team won the toss without performing the virtual coin toss animation. Both methods coexist — users can use either the existing coin toss or the new manual buttons.

## Changes

### `TossViewModel.kt`
- Added `TossSource` enum (`COIN`, `MANUAL`) for optional source tracking
- Added `isAnimating`, `tossWinner`, and `tossSource` state flows
- Exposed `onManualTossWinnerSelected(teamName: String)` — records the manual toss winner, clears any active toss animation state, and updates the selected winner
- Exposed `onCoinTossComplete(winner: String)` and `setAnimating(animating: Boolean)` for clean animation state tracking

### `TossScreen.kt`
- Collected `isAnimating` and `tossWinner` using `collectAsStateWithLifecycle()`
- Added two dynamic `OutlinedButton`s (e.g., "Team A Wins Toss" / "Team B Wins Toss") below the coin flip UI
- Manual buttons are **disabled** while a coin toss animation is running to prevent state conflicts
- Manual selection reuses the exact same downstream logic (batting/bowling bottom sheet → `saveTossResult` → navigation)

### `TossViewModelTest.kt`
- Added unit tests for the `onManualTossWinnerSelected` path:
  - Manual selection sets the correct toss winner
  - Manual selection clears animation state
  - Downstream state is identical to coin-toss path

## Verification

| Check | Status |
|-------|--------|
| `:app:compileDebugKotlin` | ✅ PASSED |
| `:app:compileDebugUnitTestKotlin` | ✅ PASSED |
| `:app:testDebugUnitTest` | ✅ PASSED (all 32 tasks) |

## Acceptance Criteria

- [x] User can manually declare which team won the toss without initiating a virtual coin toss
- [x] Manual selection correctly reflects the toss winner and shows the batting/bowling decision prompt
- [x] Both manual selection and coin toss remain functional
- [x] Manual buttons are disabled during coin toss animation
- [x] No data corruption or state inconsistencies
- [x] All existing tests pass