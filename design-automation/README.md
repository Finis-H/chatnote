# Vault OS Figma Design Automation

This directory is the source-of-truth workspace for generating and reviewing the Vault OS Figma portfolio. It captures validated product facts, generation inputs, and QA criteria; it does **not** contain application UI implementations.

## Scope

- Product narrative and interaction facts live in `product/`.
- The Figma canvas baseline is **1440 × 900 px**.
- The portfolio is limited to **four key frames**. Their exact scope is in [product/key-frames.md](product/key-frames.md).
- `tokens/`, `fixtures/`, `figma/`, `prototype/`, `qa/`, and `scripts/` are reserved for future automation assets. Do not place production Vue, CSS, or Tauri code here.

## Working order

1. Keep the product facts in `product/` aligned with the repository implementation.
2. Add design-token mappings and safe fixture data without copying secrets or real runtime data.
3. Generate the four Figma frames from the documented canvas and facts.
4. Run the QA checklist before presenting the portfolio.

## Source boundaries

The current implementation remains authoritative for WebSocket events, memory semantics, and plugin security. These design documents summarize the facts for Figma work; they do not redefine the protocol or permission model.
