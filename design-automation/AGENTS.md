# AGENTS.md — Vault OS Design Automation

## Mission

Generate a Figma-ready and frontend-ready portfolio design for Vault OS.

Vault OS is a local AI workspace for long-term memory, knowledge retrieval, plugin execution, and observable AI collaboration. `design-automation/` is a documentation and generation-input boundary for that portfolio, not a second frontend.

## Non-negotiable constraints

- Create only four portfolio key frames. Do not add a fifth frame without an explicit product decision.
- Every key frame must use a 1440 × 900 px canvas. Do not create extra product screens.
- Do not implement Vue, CSS, Tauri, WebSocket clients, or backend services in this directory.
- Use WebSocket interaction semantics only. Do not use SSE or poll-only loading states.
- Do not add a second confirmation input after the existing decision.
- Low-confidence memory auto-adopts after three days unless the user rejects it.
- Permission confirmation is required for:
  - delete
  - uninstall
  - high-frequency create, update, or delete operations
  - local memory access
  - network access
  - system core configuration changes
- Do not include API keys, run tokens, local host details, user memory, chat history, or other runtime data in fixtures or Figma exports.
- Third-party plugin output is untrusted. A sensitive permission confirmation must visibly name the plugin, requested permissions, purpose and risk, plus a redacted parameter preview.
- Temporary sessions are isolated: they do not read main memory, do not write persistent state, and discard late results after the session ends.

## Trust principles

Every screen must visibly express at least one of:

- state visibility
- tool-call transparency
- permission confirmation
- user trust
- auditability
- sensitive-parameter detection
- redaction
- DAG precheck
- runtime interception
- third-party output isolation

## Figma output

Create these pages:

- 00 Cover
- 01 Keyframes
- 02 Components
- 03 Handoff

Create these frames. The Figma delivery names below coexist with the corresponding current specification themes:

- KF01 / Control Terminal Home / 1440x900 (Command Console)
- KF02 / Agent Running / 1440x900 (Agent execution and Trace)
- KF03 / Memory Review + Permission Gate / 1440x900 (Memory staging)
- KF04 / Plugin Center + Settings / 1440x900 (Third-party plugin permission)

## Source of truth

Do not manually encode arbitrary UI decisions in Figma scripts.

All layout, copy, states, and components must come from:

- `specs/frames/*.yaml`
- `specs/components.yaml`
- `specs/states.yaml`
- `specs/permission-model.yaml`
- `tokens/*.json`
- `fixtures/*.json`

Treat `product/` as the factual brief. Verify protocol, permission, and memory changes against the root code before changing product facts. `specs/` derives from `product/`; `tokens/` maps the existing design-token source and must not become a competing token system.

## Directory ownership

- `product/`: portfolio facts and interaction constraints.
- `specs/`: generation specifications derived from `product/`.
- `tokens/`: mappings to the existing design-token source; do not invent a competing token system.
- `fixtures/`: synthetic and redacted input data only.
- `figma/`: Figma metadata or export manifests, not UI source code.
- `prototype/`: interaction notes or Figma prototype contracts only.
- `qa/`: visual and behavior review criteria.
- `scripts/`: future non-UI automation scripts.

## Review rules

Before finalizing, check:

- all required product states exist
- all permission states exist
- all WebSocket states exist
- all four frames match 1440 × 900 px
- no additional key frames or product screens were created
- no unsafe high-risk action executes without permission
- no fixture or export exposes runtime data or unredacted sensitive values
- third-party output remains visibly isolated as untrusted data
- temporary-session artifacts preserve their isolated-memory and late-result-discard semantics

## Conditional QA remediation

When addressing the conditional QA pass, resolve the P0, P1, and selected P2 items documented in:

- `qa/review-report.md`
- `qa/fix-list.md`

Do not expand this work into production implementation. Review and update only the design-automation inputs and deliverables within these sources as needed:

- `specs/`
- `fixtures/`
- `prototype/`
- `figma/`

In addition to the non-negotiable constraints above:

- Keep exactly four keyframes and export exactly four 1440x900 images.
- Do not introduce SSE, EventSource, polling-only language, or a production WebSocket implementation.
- Do not add a second confirmation input.
- Use only synthetic, redacted fixture data; never expose a token, API key, host, URL, user memory, or runtime data.

Required QA fixes:

1. Add a compact, non-product Handoff / Acceptance strip to every keyframe and its export annotation. Each strip must include User Goal, Core Information, Primary Action, Risk State, Design Rationale, Required Components, States to Show, and Frontend / Codex Acceptance Criteria.
2. Add explicit Frontend / Codex acceptance criteria for KF01 through KF04, and use required component names rather than component counts.
3. Replace a label-only DAG preflight with a compact preflight sequence based on `perm_fixture_dag_001`.
4. Show runtime secondary interception as a concrete event with a pending/block decision.
5. Present third-party output as isolated, untrusted, data-only, non-executable content.
6. Render planned permission choices as a read-only, disabled decision row: Deny, Allow once, and Allow for session.
7. Add explicit user-goal lines to KF02 through KF04 and a named risk state to KF01.
8. Clarify KF02's primary running-state control with a non-destructive observation control.
9. Make KF04's permission decision row the visual primary action.
10. Normalize the three-day memory outcome term to `auto_adopted` across specs, states, fixtures, prototype copy, and the QA checklist.

After changes, regenerate the prototype and Figma-ready output, export the four required images, rerun QA against those exports, and update `qa/review-report.md` and `qa/fix-list.md`.
