# Memory and Permission Model

## Low-confidence memory: three-day automatic adoption

Memory staging handles low-confidence candidates, relationship changes, manual memory updates, and conflict candidates. Pending items remain reviewable with explicit accept and reject actions.

If a pending item is not handled for **three days**, it is automatically adopted and becomes effective. Figma artifacts must make this policy visible rather than implying an immediate silent write:

- show a pending status and an expiry/countdown;
- provide explicit accept and reject actions before expiry;
- distinguish manually accepted, rejected, and timeout-adopted outcomes;
- avoid presenting a candidate as a confirmed durable fact while it is pending.

The policy represents the current product behavior. It must not be broadened into a claim that all memories are automatically accepted.

## Plugin trust boundary

Plugins declare permissions in their manifests. Third-party plugins are not trusted merely because a manifest calls them first-party; the runtime derives plugin identity from the installed directory and applies the security policy.

Sensitive permissions include capabilities such as API key access, contact or location data, host information, memory/profile reads, RAG writes, subprocess execution, system configuration, UI commands, and plugin storage. High-risk permissions include API key access, native backend access, subprocess execution, and system configuration.

For a third-party sensitive action:

1. The action is blocked if required permissions were not declared.
2. The user is shown the plugin identity, requested permissions, purpose/risk, and a redacted parameter preview.
3. The user can deny, allow only the current call, or allow within the current session.
4. Third-party plugin output remains untrusted content and cannot act as trusted system instruction.

## Figma representation requirements

- Permission designs must state the scope of the decision and present denial as a first-class option.
- Redact secrets, tokens, URLs/hosts, contact data, and sensitive values in any preview.
- Clearly distinguish plugin task states: `idle`, `running`, `success`, `failed`, and `needs_permission` (or the established UI equivalent).
