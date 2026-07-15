# Static Portfolio Prototype

This is a fixture-only static prototype with exactly four hash routes:

- `#control-terminal`
- `#agent-running`
- `#memory-permission`
- `#plugin-center`

Run it from the `design-automation/` directory with a static HTTP server, for example:

```powershell
python -m http.server 4173
```

Then open `http://127.0.0.1:4173/prototype/#control-terminal`.

The prototype loads its frame copy from `specs/frames/*.yaml`, component names from `specs/components.yaml`, and state data from `fixtures/*.json`. It does not connect to a Vault OS backend and does not implement SSE.
