# Ticket Intake Report

## Ticket Type
**Feature**

## Summary
The Toss screen currently only supports a virtual coin toss to determine which team wins the toss. Users are requesting an additional **manual system** so they can directly select the toss winner without performing the coin toss. This enhancement will give users the flexibility to skip the animated toss and manually assign the winner, streamlining the match setup process.

## Confirmed Facts
- In the current Toss screen, the only available interaction is a coin toss simulation; there is no option for manual winner selection.
- Steps to reproduce the missing functionality:
  1. Click “Start New Match”
  2. Complete match setup and tap “Proceed to Toss”
  3. Observe that no manual system exists to choose the toss winner
- The user explicitly states, “currently user have to do the toss with coin on the toss screen” and wants a “manuall [sic] system also”
- The requested feature is to add an alternative way to declare the toss winner, overriding or bypassing the coin toss.

## Assumptions
- The manual selection should coexist with the existing coin toss (i.e., both methods remain available).
- The manual system will likely include UI controls (e.g., buttons or a dropdown) to choose which team won the toss.
- The winner chosen manually will proceed to the same next step (e.g., choosing to bat or bowl) as when determined by the coin toss.
- No backend changes are required beyond those already used for coin toss results; the selection can be handled locally until the match is saved.

## Expected Output
- A new user interface element on the Toss screen (e.g., two buttons labelled “Team A Wins Toss” and “Team B Wins Toss” or a toggle).
- When the user taps one, the toss winner is set immediately, skipping the coin animation.
- The match flow continues exactly as it would after a successful coin toss (user can choose batting/bowling etc.).
- No impact on data consistency; the final toss outcome is logged the same way.

## Required Steps
1. **Analyze** existing Toss screen UI component and coin toss logic.
2. **Design** the manual selection UI (placement, style, labels) and get UX approval.
3. **Implement** the new UI element(s) in the Toss screen layout.
4. **Integrate** the manual selection with the toss decision handler – the same function that records the toss winner should be called regardless of method.
5. **Update** any state management/view model to recognise when a manual winner is chosen and disable/omit the coin animation.
6. **Add analytics** tracking to differentiate manual toss vs. coin toss (optional but recommended).
7. **Write unit and UI tests** for manual selection path, including edge cases (e.g., rapid clicks, screen rotation).
8. **Perform QA** on various devices to ensure the new option is accessible and the flow is seamless.

## Acceptance Criteria
- On the Toss screen, the user can manually declare which team won the toss without initiating a virtual coin toss.
- After manual selection, the toss winner is correctly reflected (e.g., team name, toss decision prompt).
- The manual selection is visually clear and does not interfere with the existing coin toss option; both must remain functional.
- The chosen team advances to the next step (batting/bowling selection) as normal.
- No data corruption or state inconsistencies occur when manual selection and coin toss are used interchangeably.

## Severity
Not applicable – this is a feature request, not a bug or crash.

## Missing Information
- **Manual selection scope:** Should the manual system allow the user to also choose whether the toss winner will bat or bowl immediately, or only the winner itself? The description mentions only “who won the toss”. Clarification needed.
- **UI / UX specifications:** No design mockups or guidelines on placement of the manual button(s). Need to define whether it’s a toggle, dropdown, or dedicated buttons, and how it coexists with the animated coin.
- **Edge cases:** What happens if the user starts a coin toss animation and then mid‑animation manually selects a winner? Should the coin toss be cancellable?
- **Accessibility:** Requirements for screen reader labels, tap target sizes, etc., are missing.
- **User permissions / game state:** Are there any match states where manual toss should be disabled (e.g., after toss already completed, in a resumed match)?
- **Analytics / tracking:** Is there a need to log manual vs. coin toss usage for business metrics?