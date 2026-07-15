# Vault OS Design Automation QA Fix List

Source review: [review-report.md](review-report.md)  
Scope: design inputs, static prototype presentation, Figma-ready exports, and handoff criteria only. No production Vue, Tauri, WebSocket, or backend implementation is included.

## Resolved P0 — handoff completeness

1. [x] Add the compact, non-product `Portfolio Handoff Annotation / Not product UI` strip to every keyframe specification and export.
2. [x] Add visible, independently checkable Frontend/Codex acceptance criteria for KF01–KF04.

## Resolved P1 — demonstrable trust safeguards

3. [x] Render a compact DAG preflight in KF02 from `perm_fixture_dag_001`, including inspected plugin/tool rows, grouped sensitive request, and a pre-execution `needs_permission` result.
4. [x] Render a runtime secondary-interception event in KF02 with an intercepted invocation, redacted runtime arguments, and `paused / waiting_permission`.
5. [x] Render a bounded KF04 `untrusted third-party output` card with `data-only / non-executable` treatment.
6. [x] Render the planned permission choices as a disabled, read-only decision row for deny, allow once, and allow session, with adjacent scope text and no second confirmation input.

## Resolved P2 — per-frame clarity

7. [x] Add explicit user-goal lines to KF02–KF04 and the bounded-idle named risk state to KF01.
8. [x] Add KF02's non-destructive `Inspect current step` observation control and make KF04's decision row visually primary.
9. [x] Show a short named required-component summary in every handoff annotation.
10. [x] Normalize the three-day historical outcome to `auto_adopted` across the frame spec, shared states, fixture, prototype copy, and this checklist.

## Re-review results — 2026-07-15

- [x] Exactly four exports exist, and each is 1440×900.
- [x] WebSocket is visible; no SSE or second confirmation input appears.
- [x] Sensitive detection/redaction, DAG preflight, runtime interception, and untrusted-output isolation are concrete export states.
- [x] Each frame shows all eight handoff fields, named required components, and Frontend/Codex acceptance criteria.
- [x] KF04 shows the planned/read-only deny / once / session decision row with scope text.
- [x] The low-confidence memory policy uses `auto_adopted` consistently.
- [x] Fixtures and exports remain synthetic and redacted; no token, API key, host, URL, user memory, or live runtime data is exposed.
