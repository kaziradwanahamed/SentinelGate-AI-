# MVP Architecture Notes

## Request lifecycle

1. Frontend / MCP host submits a tool name, arguments, agent ID, and provenance hint.
2. Backend resolves capabilities from its own `AGENT_CAPABILITIES` map. Client requests cannot expand capabilities.
3. Policy engine checks tool authorization and deny-listed high-impact actions.
4. Prompt scanner examines goal, retrieved content, tool name, and arguments.
5. Provenance and sensitive-data rules adjust risk / review requirements.
6. Decision is `ALLOW`, `BLOCK`, or `REVIEW`.
7. Only `ALLOW` reaches the mock adapter. The mock adapter has no external side effects.
8. The event is written to SQLite.

## Important distinction

This MVP demonstrates the control flow. It does not yet provide cryptographically verified provenance, authentication, tamper-proof logs, a production tool sandbox, a fully trained SLM, or a complete security policy language. Those are separate engineering milestones.
