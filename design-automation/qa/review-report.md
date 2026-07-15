# Vault OS Design Automation QA Review

Reviewed: 2026-07-13  
Scope: the four static prototype routes and their generation inputs under `design-automation/`. This is a design-automation review, not a claim about production runtime availability.

## Verdict

**Conditional pass — 8 passed, 4 partial, 0 failed.** The portfolio obeys the four-frame, 1440 × 900, WebSocket-only, and no-second-confirmation constraints. Every route now renders a compact, export-only handoff annotation with independent frontend/Codex acceptance criteria. The execution safeguards are still mostly labels rather than evidence of a concrete preflight/interception/isolation flow.

## Review method and evidence boundary

- Reviewed the four routes declared in [prototype/app.js](../prototype/app.js): `#control-terminal`, `#agent-running`, `#memory-permission`, and `#plugin-center`.
- Reviewed all four frame specs in [specs/frames](../specs/frames), the common [layout contract](../specs/layout-contract.yaml), [permission model](../specs/permission-model.yaml), copy, and synthetic fixtures.
- Checked the fixed prototype canvas in [prototype/styles.css](../prototype/styles.css), where `.canvas` is `1440px × 900px`.
- No Figma export or separate image files are present. “Displayed” therefore means rendered by the static prototype source, not visually certified from a Figma export. Re-run this review against exported 1440 × 900 images before delivery.

## Required checks

| # | Check | Result | Evidence / judgement |
| --- | --- | --- | --- |
| 1 | Exactly four key-frame specs | Pass | [product/key-frames.md](../product/key-frames.md) names four frames; [specs/frames](../specs/frames) contains `01`–`04`; the route array has four entries. |
| 2 | Every key frame is 1440 × 900 | Pass | Every frame spec declares `canvas: { width: 1440, height: 900, unit: px }`; the static canvas is also fixed to `1440px × 900px`. |
| 3 | WebSocket is present | Pass | The global top bar displays a WebSocket connection label; frames 02–04 declare `transport: websocket`; the fixtures are synthetic WebSocket event streams. |
| 4 | SSE is absent | Pass | [layout-contract.yaml](../specs/layout-contract.yaml) prohibits SSE; the prototype uses fixture loading only and contains no `EventSource`/SSE client. |
| 5 | Permission confirmation is displayed | Partial | Frame 04 shows plugin identity, requested permissions, reason, redacted preview, and deny / once / session decision labels. It is correctly marked “planned / read-only”, but the choices are tags rather than a clearly pending decision action row. |
| 6 | Sensitive-parameter detection and redaction are displayed | Pass | Frame 04 displays the “sensitive parameter detection” control point and a preview with `api_key: ******` and `[URL_REDACTED]`; the fixture reason states that a sensitive argument was detected. |
| 7 | DAG preflight is displayed | Partial | Frames 02 and 04 render a “DAG preflight” label. The rendered plugin dialog uses the single-call fixture only, so it does not show the batched DAG preflight, inspected steps, or a before-start outcome. |
| 8 | Runtime secondary interception is displayed | Partial | Frames 02 and 04 render a “runtime secondary interception” label, but no intercepted invocation, re-evaluated permission, block, or pending-decision transition is shown. |
| 9 | Third-party output isolation is displayed | Partial | Frame 04 warns that third-party code and output are untrusted, and frames 02/04 label output isolation. No concrete third-party output is rendered in an isolated, non-instruction treatment. |
| 10 | Low-confidence memory auto-adopts after three days is displayed | Pass | Frame 03 renders low-confidence / pending risk, an explicit three-day policy, countdown, and accept / reject actions. |
| 11 | No second confirmation input appears | Pass | Memory review exposes only accept/reject; the plugin permission view has decision labels and no extra text or acknowledgement input. The constraints also explicitly prohibit one. |
| 12 | Every image includes the required handoff information | Pass | Every route reads an eight-field `handoff` block from its frame spec and renders the compact `Portfolio Handoff Annotation / Not product UI` export overlay. Each criterion names what is verifiable in the export and what is confirmed by linked spec/fixture data. |

## Per-keyframe handoff coverage

Legend: **Pass** = visibly represented in the prototype; **Partial** = only inferred, source-only, or not explicit enough for handoff; **Missing** = absent.

| Key frame | User goal | Core information | Primary action | Risk state | Design rationale | Required components | States to show | Frontend/Codex acceptance | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KF01 Control Terminal | Pass — annotation names the main-session goal | Pass | Pass | Pass — annotated review boundary | Pass | Pass — full list in annotation | Pass | Pass | Pass |
| KF02 Agent Running | Pass — annotation names the execution-tracking goal | Pass | Pass — inspect Trace / return via navigation | Pass | Pass | Pass — full list in annotation | Pass | Pass | Pass |
| KF03 Memory Review | Pass — annotation names the candidate-review goal | Pass | Pass | Pass | Pass | Pass — full list in annotation | Pass | Pass | Pass |
| KF04 Plugin Center | Pass — annotation names the permission-decision goal | Pass | Pass — read-only decision model is explicitly marked | Pass | Pass | Pass — full list in annotation | Pass | Pass | Pass |

## Consistency finding

The three-day policy terminology is inconsistent across sources: frame 03 uses `auto_adopted`, while [fixtures/memory-events.json](../fixtures/memory-events.json) and [specs/states.yaml](../specs/states.yaml) use `AUTO_OVERWRITTEN` / `auto_overwritten`. The visible pending countdown satisfies this review, but outcome terminology must be unified before an auto-adopted history state is designed or exported.

## Delivery gate

Do not mark the portfolio fully QA-approved until the remaining P1 items in [fix-list.md](fix-list.md) are resolved, the four rendered exports are captured at 1440 × 900, and the same checklist is re-run against those exports.
