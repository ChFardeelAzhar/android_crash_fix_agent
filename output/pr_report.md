# Add Manual Toss Winner Selection on Toss Screen

## Executive Summary

A user-facing enhancement was implemented to allow manual selection of the toss winner on the Toss screen, bypassing the virtual coin toss animation. The existing coin toss remains fully functional; both methods now coexist. The implementation adds two dynamic buttons (`"{Team A Name} Wins Toss"` and `"{Team B Name} Wins Toss"`) below the coin flip UI. When a manual button is tapped, the toss winner is recorded immediately and the user proceeds to the batting/bowling decision – exactly as after a coin toss. While a coin animation is running, the manual buttons are disabled to prevent conflicts.

All compilation and unit tests pass (including a new test for the manual path). The feature is isolated to three files, with minimal changes and no architectural refactoring. The branch `feat/manual-toss-winner` has been pushed and is ready for pull request review.

---

## Ticket Source

- **Source:** Raw Text (external description, no formal ticket number)
- **Resolved Source Tracker Type:** `raw_text`

---

## Ticket Type

**Feature**

---

## Branch Name

`feat/manual-toss-winner`

---

## Modifications Made

1. **`app/src/main/java/com/cricscore/app/ui/toss/TossScreen.kt`**  
   - Added two `OutlinedButton`s labelled with dynamic team names.  
   - Connected buttons to `onManualTossWinnerSelected` action.  
   - Disabled buttons when `isAnimating` is `true`.  
   - Preserved existing coin toss UI and navigation.

2. **`app/src/main/java/com/cricscore/app/ui/toss/TossViewModel.kt`**  
   - Introduced `TossSource` enum (`COIN`, `MANUAL`).  
   - Added `isAnimating` and `tossWinner` `StateFlow`s.  
   - Implemented `onManualTossWinnerSelected(teamName)` to set winner, cancel animation state, and track source.  
   - Kept existing `onCoinTossComplete` and `setAnimating` unchanged.

3. **`app/src/test/java/com/cricscore/app/ui/toss/TossViewModelTest.kt`**  
   - Added unit tests for manual selection, verifying the correct winner is set, animation state is cleared, and downstream behaviour matches the coin-toss path.

**Total:** 3 files changed, 132 insertions, 4 deletions.

---

## Git Branch & Commit Status

| Item | Detail |
|------|--------|
| **Branch name** | `feat/manual-toss-winner` |
| **Commit hash** | `4ef0dc1` |
| **Commit message** | `Add manual toss winner selection feature` |
| **Pushed to remote** | ✅ (`origin/feat/manual-toss-winner`) |
| **Working tree clean** | ✅ |
| **PR description available** | Yes, generated in `output/pr_description.md` |

---

## Test Plan & Verification Results

### Build & Unit Tests

| Task | Status |
|------|--------|
| `:app:compileDebugKotlin` | ✅ Passed (UP-TO-DATE) |
| `:app:compileDebugUnitTestKotlin` | ✅ Passed (UP-TO-DATE) |
| `:app:testDebugUnitTest` | ✅ Passed – all 32 tasks succeeded, including new manual‑toss tests |
| **New failures** | None |

### Device Verification

- **Screenshot and logcat captures** were taken after the feature installation.  
- The manual toss buttons appeared as expected on the Toss screen.  
- Tapping a manual button correctly set the toss winner and navigated to the batting/bowling selection screen.  
- The coin toss still works identically, and the manual buttons are disabled during the animation.  
- No crashes or UI glitches were observed.

---

## Manual QA Checklist

- [ ] Start a new match, complete setup, and proceed to the Toss screen.  
- [ ] Verify two manual buttons are visible and labelled with the correct team names.  
- [ ] Tap one manual button: confirm the toss winner is recorded and the batting/bowling decision bottom sheet appears.  
- [ ] Choose bat/bowl and ensure navigation to innings setup works.  
- [ ] Return to the Toss screen and verify the coin toss still functions (animated toss works, winner set correctly).  
- [ ] While the coin animation is playing, confirm the manual buttons are disabled (not clickable).  
- [ ] Test edge cases: rapid taps, screen rotation, back button handling, and resuming a partially completed toss.  
- [ ] (Optional) Confirm that analytics or logs differentiate manual vs. coin toss source.

---

## Risk Level

**Low**

- The change is additive and does not modify any existing logic or state machines.  
- Manual buttons are disabled during animation to eliminate state conflicts.  
- All existing unit tests pass, and new tests cover the manual path.  
- No architectural or dependency changes were introduced.

---

## Reviewer Checklist

- [ ] Code follows project conventions (MVVM, Compose, naming).  
- [ ] No unrelated refactors or dead code introduced.  
- [ ] Unit tests for the new functionality are present and meaningful.  
- [ ] No `TODO`, debug logs, or commented‑out code left in the diff.  
- [ ] UI layout looks correct on a standard phone screen; manual buttons do not overlap the coin toss area.  
- [ ] Manual QA steps (see above) can be repeated on the reviewer’s device.  
- [ ] Branch naming and commit message comply with team standards (`feat/`, imperative, kebab-case).  
- [ ] PR description is clear and references this report.