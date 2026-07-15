# Vault OS Design Automation QA Fix List

Source review: [review-report.md](review-report.md)  
Scope: design inputs, static prototype presentation, and handoff criteria only. Do not turn this directory into a production Vue, Tauri, WebSocket, or backend implementation.

## Resolved P0 — 2026-07-14

1. [x] Add a compact, non-product “Handoff / acceptance” strip to each keyframe specification and export annotation.
   - Include: user goal, core information, primary action, risk state, design rationale, required components, states to show, and frontend/Codex acceptance criteria.
   - Keep it outside the product workspace hierarchy so it is clearly a portfolio/handoff annotation, not a fifth product screen or a user-facing “Required evidence” module.
   - Acceptance: each of `01`–`04` can be reviewed independently without inferring any of the eight fields from another file.

2. [x] Add explicit frontend/Codex acceptance criteria for every frame.
   - KF01: WebSocket connection state is visible without exposing token, port, or endpoint; command focus remains visible.
   - KF02: running/degraded/success trace states and one measurable outcome are distinguishable; no SSE/poll-only semantics are implied.
   - KF03: pending low-confidence candidate is not styled as durable fact; accept/reject and the three-day outcome are clear; no second confirmation field exists.
   - KF04: plugin identity, requested permissions, purpose/risk, redacted preview, deny/once/session scope, and untrusted-output treatment are all visible; it remains labelled planned/read-only.
   - Acceptance: criteria are checkable from a single exported frame plus linked spec/fixture data.

## P1 — make trust safeguards demonstrable

3. Replace label-only DAG preflight evidence with one compact preflight sequence.
   - Use the existing batched `perm_fixture_dag_001` fixture: show plugin/tool rows inspected before execution, the grouped sensitive request, and a `blocked` or `needs_permission` result before any tool stage runs.
   - Preserve WebSocket semantics and use only synthetic redacted data.

4. Show a concrete runtime secondary-interception event.
   - In KF02 or KF04, render an invocation whose runtime arguments trigger a new sensitive permission check; show the resulting block or pending decision.
   - Do not imply that the planned permission governance is already implemented.

5. Render third-party output as visibly isolated untrusted data.
   - Add a small bounded output card with an “untrusted third-party output” label and a non-executable/data-only treatment.
   - Do not present its content as a system instruction, tool instruction, or confirmed result.

6. Turn the planned permission decision model into a clear read-only decision row.
   - Render disabled/read-only buttons for deny, allow once, and allow for session, with scope text adjacent to each choice.
   - Keep the existing planned/read-only label and do not add a second confirmation input.

## P2 — improve per-frame clarity

7. Add an explicit user-goal line to KF02–KF04 and a named risk state to KF01.
   - KF02 should name the task objective, not only `message` as request type.
   - KF03 should state the review goal (for example, decide whether to retain a candidate preference).
   - KF04 should state the user’s intended plugin task before explaining the plugin’s own reason.
   - KF01 should show a neutral/no-current-risk or clearly bounded-risk state instead of relying on descriptive boundary copy.

8. Give KF02 a primary running-state control and clarify KF04’s primary action.
   - For KF02, use an existing navigation/return or a clearly non-destructive observation control; do not invent an unsupported cancel protocol.
   - For KF04, ensure the permission decision row—not settings/delete—is visually primary.

9. Display a short required-component list in each handoff annotation.
   - The source component arrays are already in `specs/frames/*.yaml`; expose their names in the annotation rather than only a count.

10. Normalize the three-day outcome terminology.
   - Choose one canonical result name for the policy (for example, `auto_adopted`) and align `specs/frames/03-memory-permission.yaml`, `specs/states.yaml`, and `fixtures/memory-events.json`.
   - Acceptance: the pending expiry policy and its historical outcome do not read as different memory behaviors.

## Re-review checklist

- Capture exactly four exports, each exactly 1440 × 900.
- Confirm WebSocket is visible and no SSE or second confirmation input appears.
- Confirm sensitive detection/redaction, DAG preflight, runtime interception, and untrusted-output isolation are shown as concrete states—not only labels.
- Confirm the three-day low-confidence memory policy and all eight handoff fields appear for every keyframe.
- Confirm no synthetic fixture reveals a token, API key, host, URL, user memory, or runtime data.
