# SentinelGate AI — Claude Code Instructions

## Goal
Build and improve a small, demonstrable runtime-security MVP for AI-agent tool calls. Keep the implementation simple, auditable, and easy to run on Ubuntu CPU-only machines.

## Non-negotiable engineering rules
- Do not over-engineer. Prefer small, focused modules and readable code.
- Do not replace the current architecture or redesign the UI without a specific reason.
- Never claim this MVP is production-grade or provides complete prompt-injection protection.
- Never execute real email, payment, shell, or database-destructive operations. All demo tools must remain simulated.
- Never trust client-supplied permissions. Agent capabilities must be defined and checked server-side.
- The deterministic policy engine is authoritative. A model score may add a risk signal but must never grant permission.
- Preserve the `DEMO` seed tags and the notice that external side effects are disabled.
- Do not commit `.env`, API tokens, customer data, model cache, SQLite files, or secrets.

## Current architecture
- `backend/`: FastAPI API, SQLite audit log, security policy, optional Hugging Face classifier, local MCP server.
- `frontend/`: React + Vite professional security dashboard.
- Backend API: `GET /api/health`, `GET /api/dashboard`, `GET /api/events`, `POST /api/analyze`.
- Local MCP server: `backend/app/mcp_server.py`.

## Before changing code
1. Inspect the existing files and current behavior.
2. Identify the exact failing or requested area.
3. Make the smallest complete change.
4. Add or update tests for security behavior.
5. Run backend tests and frontend production build.
6. Report changed files, tests run, results, and remaining limitations.

## Security test cases that must continue to pass
- A trusted invoice `read_file` request from `finance-assistant-01` is allowed and only returns mock content.
- `delete_database` is blocked.
- An untrusted prompt injection attempting to send customer data externally is blocked.
- A request with unknown provenance requires review and is not executed.
- An unknown agent has least-privilege capabilities (read-only by default).

## Local commands
Backend:
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm run dev
```

Tests/build:
```bash
cd backend && PYTHONPATH=. pytest -q
cd frontend && npm run build
```
