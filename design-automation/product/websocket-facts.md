# WebSocket Facts for Design Automation

## Connection boundary

- The backend exposes the WebSocket endpoint as `/ws/{client_token}`.
- A connection with a token that does not match the active security token is closed with code `1008`.
- The desktop client reads the dynamic port and run token from the Tauri layer, then connects to `ws://127.0.0.1:{port}/ws/{token}`.
- On connection, the server may send `{ "type": "history_all", "content": ... }` to synchronize chat history, and it forwards event-bus messages as JSON.

## Message envelope

Inbound requests are JSON objects. The core routing fields are:

```json
{
  "type": "command_name",
  "thread_id": "optional-thread-id",
  "session_mode": "main | temp",
  "session_id": "main-or-temp-session-id"
}
```

Chat requests additionally carry `message`. The server routes by `type`; events sent back to the client also use a `type` field and commonly carry `content`, `session_id`, or event-specific data.

## Design-relevant events

| Interaction | Client request type | Server event / response type | Figma implication |
| --- | --- | --- | --- |
| Start isolated exploration | `start_temp_session` | `temp_session_started` | Show that temporary work is a distinct, isolated mode. |
| End isolated exploration | `end_temp_session` | `temp_session_ended` | Show that ending it closes the temporary boundary. |
| Load memory review data | `fetch_memory` | `memory_data`, `profile_import_state` | Memory staging is stateful, not a static note list. |
| Resolve a memory candidate | `resolve_memory_conflict` | refreshed memory data plus system state/toast events | Acceptance and rejection have visible completion feedback. |
| Answer a permission request | `plugin_permission_response` | permission decision resolves a pending plugin action | Permission is an interrupting decision, not an automatic execution state. |
| Submit a chat task | request containing `message` | trace, task, and response events through the event bus | The Trace is driven by task events and can change while a task runs. |

## Constraints for generated designs

- This is a factual interaction reference, not a new protocol specification.
- Do not expose the run token, live port, user data, or raw event payloads in portfolio fixtures.
- Preserve temporary-session semantics: restricted management actions are unavailable in `temp` mode, and temporary sessions do not alter persistent memory or configuration.
