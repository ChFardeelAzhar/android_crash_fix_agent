# Engineering Brief: Add Manual Toss Winner Feature

## 1. Objective
Safely and minimally introduce a manual toss‑winner selection on the existing Toss screen so that after a match is set up, the user can directly choose which team won the toss without using the animated coin toss. Both coin toss and manual selection must coexist without regressions.

## 2. Ticket Summary
- **Type:** Feature
- **Current state:** Toss screen only offers a virtual coin toss.
- **Request:** Add a manual system to declare the toss winner immediately.
- **Expected outcome:** New UI controls (e.g., two buttons) on the Toss screen. Tapping one sets the winner and moves to the batting/bowling choice, bypassing the animation. The same downstream logic that handles a coin‑toss result must be reused.
- **Non‑functional:** Must not break existing tests; must adhere to MVVM/Compose best practices; lifecycle‑safe; no unrelated refactors.

## 3. Investigation Instructions
The agent **must** explore the codebase before writing any code. Because file paths are not assumed, the agent should:
- Search for Composable functions whose names contain `Toss`, `Coin`, `CoinToss`, or similar.
- Locate the ViewModel that manages the toss screen state (likely holds a `tossWinner`, `isTossed`, `isAnimating`, etc.).
- Identify the navigation event that proceeds to the next screen after a toss winner is decided (batting/bowling selection).
- Understand how the coin toss sets the winner – a function like `onCoinTossComplete(winner)` that updates state and triggers navigation.
- Examine any layout constraints or state machines that might disable/re‑enable buttons.
- Run existing unit and UI tests for the toss screen to see how they exercise the flow (the agent should keep them passing).

The agent should return the exact file names and line numbers of the relevant components before starting implementation.

## 4. Implementation Constraints
- **Minimal changes:** Only add the manual selection UI and its interaction; do **not** refactor unrelated code, extract base classes, or introduce new architectural patterns.
- **MVVM & Compose:** UI elements emit events to the ViewModel; state is observed in a lifecycle‑conscious manner (`collectAsStateWithLifecycle()` or equivalent). No manual `remember` for business logic.
- **Lifecycle safe:** State restoration on configuration changes must work using `SavedStateHandle` (if already used) or `rememberSaveable` for transient UI state.
- **No new dependencies:** Use only existing Jetpack Compose, Kotlin coroutines, and whatever navigation library is already present.
- **Backward compatible:** The coin toss must remain fully functional. Adding manual controls must not break the existing UI layout. If the coin toss animation is already running, manual selection should either be disabled or safely cancel the animation (the implementation may choose to disable the manual buttons until the toss is decided, as per the missing edge‑case clarification – assume the simplest safe option: **disable manual buttons while a toss animation is in progress**).
- **Testing:** All existing tests must pass. The agent may add new tests covering the manual path, but only if they can be written without introducing new test dependencies.
- **UI layout:** Place the manual selection buttons **above** or **below** the coin toss area, distinct but clearly part of the same screen. Labels: `“{Team A Name} Won Toss”` and `“{Team B Name} Won Toss”` (use team names from the ViewModel state, not hardcoded). The buttons should be `OutlinedButton` or `Button` with appropriate padding.

## 5. Definition of Done
- The agent applies all changes directly to the working tree in `CricScore/`.
- All existing tests pass (run `./gradlew test` before considering work complete).
- Manual testing scenario (the agent should describe the verification):
  1. Start a new match, set up teams, proceed to Toss screen.
  2. Two new buttons are visible, e.g., “Pakistan Won Toss” and “Australia Won Toss”.
  3. Tapping one immediately navigates to the batting/bowling selection screen with the chosen team as toss winner.
  4. If coin toss is used instead, it still works exactly as before.
  5. While a coin toss animation is playing, the manual buttons are not clickable (or they are hidden) to avoid conflicts.
- The agent must not leave any `TODO` comments, log statements, or debug code.

## FIX_INSTRUCTION

The following block contains the exact prompt that will be passed verbatim to the autonomous coding agent via `agy -p`.

```FIX_INSTRUCTION
Implement a manual toss winner selection feature on the Toss screen in the Android project at /Users/retailopakistan/AndroidStudioProjects/CricScore. The existing screen only supports a virtual coin toss; add a way for the user to directly choose which team won the toss, bypassing the animation. Both methods must coexist.

First, explore the codebase to find: the Composable that renders the toss screen, its corresponding ViewModel, and the logic that sets the toss winner and navigates to the batting/bowling choice. Look for files containing "Toss" or "Coin" in their names. Identify the state variables (e.g., tossWinner, isAnimating, teamAName, teamBName) and the function that is called when the coin toss finishes (e.g., onTossComplete(winner)). Understand how the winner is recorded and how the navigation is triggered.

Then implement minimal changes:

1. Add two new buttons (use Jetpack Compose `OutlinedButton` or `Button`) on the toss screen, labeled dynamically with the team names (e.g., "{team A name} Wins Toss", "{team B name} Wins Toss"). Place them near the existing coin toss UI without obstructing it.
2. In the ViewModel, expose a function like `onManualTossWinnerSelected(team: Team)` that sets the toss winner, disables any toss animation in progress, and triggers the same navigation as a completed coin toss.
3. Ensure that the existing coin toss flow is not altered. The ViewModel should differentiate between manual and coin sources if necessary for analytics (optional), but the downstream state must be identical.
4. While a coin toss animation is running (isAnimating == true), the manual buttons must be disabled to prevent state conflicts.
5. Maintain MVVM: the UI calls the ViewModel function, the ViewModel updates state (e.g., tossWinner, isTossed, navigateToNext) and the Compose UI observes those states using `collectAsStateWithLifecycle()` or the project’s existing pattern.
6. Use the same navigation action that is used after a coin toss – do not introduce a new navigation route unless unavoidable.
7. Do NOT refactor unrelated code, change architecture, or add new libraries. Keep changes as small as possible.
8. Ensure that all existing unit tests and UI tests pass. Run `./gradlew test` or the equivalent task. If adding new tests is practical, cover the manual selection path, but prioritise not breaking anything.
9. Apply all changes directly to the working tree. Do not leave TODO comments or debug logs.
10. Verify that after tapping a manual button, the app navigates to the batting/bowling selection screen with the correct team as the toss winner.
11. Confirm that the coin toss still works exactly as before, and that the manual buttons are disabled during its animation.

After implementation, provide a summary of the files changed and a brief explanation of how the manual path integrates with the existing toss logic.
```