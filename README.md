# SentinelGate AI — Runtime Security MVP

A demo-only runtime security gateway for AI-agent tool calls. The project includes a React dashboard, FastAPI policy API, SQLite audit history, a local MCP server exposing sandbox tools, and an optional Hugging Face prompt-injection classifier.

> **Scope / safety notice:** This is a prototype, not production security software. All tool actions are simulated. The demo does not send email, access a real database, move money, or execute shell commands. Do not connect it to real customer data or production tools.

## What is implemented

- Intercepts a submitted tool-call request at the API boundary.
- Looks up each agent's allowed tools on the server (not from client-provided permissions).
- Applies deny-list rules for destructive / high-impact demo tools.
- Checks simple data-provenance signals and sensitive-data / external-recipient combinations.
- Scans prompt context with a deterministic heuristic by default.
- Optionally loads a Hugging Face text classifier when explicitly enabled.
- Allows, blocks, or sends requests to review; blocked/reviewed calls are never simulated as executed.
- Measures real gateway processing latency per request with a monotonic timer and reports `latency_ms`.
- Stops runaway agent loops with a deterministic, server-side iteration/token circuit breaker.
- Records every analyzed request in SQLite and displays recent events in the dashboard.
- Exposes three sandbox-only tools through an MCP server for local Claude/MCP testing.

## Architecture

```text
React + Vite Dashboard
        |
        | POST /api/analyze
        v
FastAPI Runtime Gateway
        |
        +--> Server-side agent capability policy
        +--> Provenance checks
        +--> Prompt / tool-argument scan (heuristics or optional HF classifier)
        +--> Sensitive-data and high-impact-action rules
        +--> ALLOW / BLOCK / REVIEW
        |
        +--> Mock tool adapter (ALLOW only; no external side effects)
        +--> SQLite audit log

Local MCP Host (Claude / MCP Inspector)
        |
        v
SentinelGate MCP Server --> same policy checks --> sandbox-only tool adapters
```

## Requirements

- Python 3.11 or newer (the official MCP Python SDK v2 requires Python 3.11+).
- Node.js 20.19+ or 22.12+ and npm (Vite 8 requirement).
- Ubuntu/Linux, macOS, or Windows.

## 1. Run locally

Open two terminal windows.

### Terminal A — backend

```bash
cd sentinelgate-ai-mvp/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend checks:

- API health: http://127.0.0.1:8000/api/health
- Interactive API docs: http://127.0.0.1:8000/docs

### Terminal B — frontend

```bash
cd sentinelgate-ai-mvp/frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173. Select a scenario and press **Analyze tool call**.

## 2. Demo scenarios

1. **Trusted invoice read** — should return `ALLOW`; only a mock invoice preview is returned.
2. **Indirect prompt injection** — should return `BLOCK`; the suspicious text attempts to redirect customer data to an external recipient.
3. **Unauthorized database action** — should return `BLOCK`; `delete_database` is not in the server-side capability list and is deny-listed.
4. **Unknown data provenance** — should return `REVIEW`; the action is not executed.

The dashboard begins with a few clearly tagged `DEMO` seed records. New records are persisted in `backend/data/sentinelgate.db` for local development.

### Runaway agent loop protection (circuit breaker)

The **Runaway agent loop protection** panel simulates an agent iterating in a loop
(mock execution only) under a deterministic circuit breaker. The breaker stops the
loop the moment it would exceed either the configured iteration budget or the
configured token budget, and records a `BLOCK` audit event:

1. **Runaway loop** — exceeds `MAX_AGENT_ITERATIONS` → `CIRCUIT_BREAKER_TRIGGERED` (reason `iteration_limit`).
2. **Token budget flood** — exceeds `MAX_TOKEN_BUDGET` → `CIRCUIT_BREAKER_TRIGGERED` (reason `token_budget`).
3. **Normal bounded task** — finishes inside both budgets → `COMPLETED`.

Budgets are read from server-side configuration only. Client-supplied request
values describe the simulated workload; they cannot raise a budget, and negative
values are rejected (HTTP `422`). Endpoint: `POST /api/simulate-loop`.

### Latency measurement

Every `/api/analyze` and `/api/simulate-loop` response includes a `latency_ms`
value measured with a monotonic high-resolution timer (`time.perf_counter`) and a
`latency_scope` of `gateway_processing`. **This measures server-side gateway
processing only (policy evaluation plus the mock-execution decision); it does not
include the network round trip.** The dashboard labels this as *Gateway latency*.
Measured on a developer laptop, gateway processing in heuristic-demo mode is
typically well under 1 ms; end-to-end HTTP round-trip latency over localhost is a
few milliseconds and depends entirely on your environment. Do not quote a fixed
figure without re-measuring on the presentation machine.

## 3. Optional model-backed classifier

The default app uses a small deterministic heuristic scanner so it boots quickly on a CPU-only laptop. The dashboard explicitly labels this mode **Heuristic demo scanner**; it is not an SLM.

#### What the heuristic-demo scanner actually does — and its limits

The default scanner (`backend/app/security/classifier.py`) matches the request context against a short, fixed list of English regular expressions for well-known injection phrasings (for example "ignore all previous instructions", "exfiltrate", "bypass the security policy"). When one matches, it raises a risk signal; it never makes the final allow/block decision on its own. Treat it as a tripwire for obvious, unobfuscated attacks, not as detection coverage. Concretely:

- **Pattern-bound and easily bypassed.** Paraphrases, obfuscation, encoding, translation, or novel attack phrasings that are not in the pattern list will not be flagged. It has no semantic understanding of the text.
- **English-only.** The patterns are English phrases; other languages are effectively invisible to it.
- **Keyword-based data checks.** The sensitive-data and external-recipient checks in `policy.py` are literal keyword/domain matches (for example `customer_data`, non-internal email domains). Renamed fields or unlisted indicators will not trigger them.
- **Signal only, never authority.** Even when it flags, the deterministic server-side capability and deny-list policies remain the authoritative control. A clean heuristic result does **not** mean a request is safe — it only means no known pattern matched.

This mode exists to keep the MVP fast and dependency-light and to demonstrate the policy flow. It is the intended place where a real SLM/classifier plugs in later (see below), replacing the heuristic signal without changing the authoritative policy engine.

To enable the optional Hugging Face classifier:

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-ml.txt
```

Then edit `backend/.env`:

```env
ENABLE_HF_CLASSIFIER=true
PROMPT_GUARD_MODEL_ID=protectai/deberta-v3-base-prompt-injection-v2
PROMPT_GUARD_THRESHOLD=0.80
```

Restart the backend. The first inference downloads model files and may be slow. The selected Protect AI model card states that it is English-focused and does not detect jailbreak attacks; it is also marked archived. Treat it as an experimental prompt-injection signal only. Review its model card, upstream dataset licences, and the terms for any alternative model before commercial use. A classifier must never be the authorization engine: server-side deterministic policies remain authoritative.

Model card: https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2

## 4. Local MCP server for Claude

The API dashboard and the MCP server are separate entry points. The MCP server exposes only sandbox tools and applies server-side policy checks before returning simulated results.

From the `backend` directory with its virtual environment active:

```bash
python -m app.mcp_server
```

This starts an MCP stdio server and waits for an MCP host. To inspect it interactively (requires Node.js / `npx`):

```bash
mcp dev app/mcp_server.py
```

For Claude Code, copy `.mcp.json.example` to `.mcp.json`, replace the placeholder with the absolute path to `backend/run_mcp.sh`, then open the repository in Claude Code. Alternatively, register it from the repository root:

```bash
claude mcp add --transport stdio sentinelgate -- /ABSOLUTE/PATH/TO/sentinelgate-ai-mvp/backend/run_mcp.sh
```

Restart or reload the Claude Code session and verify with `/mcp`. The MCP tools are demo-only and do not perform real email or database operations.

## 5. Run tests

```bash
cd backend
source .venv/bin/activate
pip install -r dev-requirements.txt
PYTHONPATH=. pytest -q
```

## 6. Deploy a public demo

Recommended split deployment: Vercel for the static Vite dashboard and Render for the FastAPI API.

### Deploy backend to Render

1. Push this repository to GitHub.
2. In Render, create **New → Web Service** and connect the repository.
3. Set **Root Directory** to `backend`.
4. Set **Build Command** to `pip install -r requirements.txt`.
5. Set **Start Command** to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
6. Add environment variables:
   - `CORS_ORIGINS=https://YOUR-FRONTEND.vercel.app`
   - `DATABASE_PATH=/tmp/sentinelgate.db` (demo-only ephemeral storage)
   - `ENABLE_HF_CLASSIFIER=false`
7. Deploy. Check `https://YOUR-API.onrender.com/api/health`.

### Deploy frontend to Vercel

1. Import the same GitHub repository into Vercel.
2. Set **Root Directory** to `frontend`.
3. Framework preset: **Vite** (or let Vercel detect it).
4. Build command: `npm run build`.
5. Output directory: `dist`.
6. Add environment variable `VITE_API_BASE_URL=https://YOUR-API.onrender.com`.
7. Deploy, then update Render's `CORS_ORIGINS` to the exact Vercel production URL and redeploy the API.

Free Render web services can sleep after inactivity and may take time to wake. The free-tier filesystem is not durable for production SQLite storage; use a managed persistent database for real deployments. For a short-lived pitch demo, use a warm-up request before presenting and verify the API health endpoint.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `CORS_ORIGINS` | localhost Vite origins | Allowed browser origins |
| `DATABASE_PATH` | `data/sentinelgate.db` | SQLite audit database |
| `ENABLE_HF_CLASSIFIER` | `false` | Enable optional transformer classifier |
| `PROMPT_GUARD_MODEL_ID` | Protect AI DeBERTa model | Hugging Face model identifier |
| `PROMPT_GUARD_THRESHOLD` | `0.80` | Model signal threshold |
| `MAX_AGENT_ITERATIONS` | `5` | Circuit-breaker iteration budget (server-enforced; non-positive values fall back to default) |
| `MAX_TOKEN_BUDGET` | `2000` | Circuit-breaker token budget (server-enforced; non-positive values fall back to default) |
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000` | Frontend API base URL |

## Known limitations — do not present as solved

- The default scanner is a heuristic demo, not an SLM and not comprehensive.
- Optional prompt classification is a signal only; it does not establish whether an action is authorized.
- The demo provenance field is caller-supplied. A production gateway must derive/cryptographically bind provenance from trusted connectors rather than trust a client label.
- The agent ID is a demo identity, not authenticated enterprise identity. Production needs authenticated principals and server-managed policies.
- The current SQLite event log is not tamper-proof. Production needs protected append-only logging, key management, retention rules, and audit review.
- The mock tool adapter has no real connectors. Production integrations need isolation, least privilege, secrets management, approvals, and tested rollback behavior.
- The code has not undergone an independent penetration test or formal security audit.

## Project structure

```text
sentinelgate-ai-mvp/
├── CLAUDE.md
├── README.md
├── .gitignore
├── .mcp.json.example
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── requirements-ml.txt
│   ├── dev-requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── mcp_server.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── schemas.py
│   │   └── security/
│   │       ├── circuit_breaker.py
│   │       ├── classifier.py
│   │       ├── mock_tools.py
│   │       └── policy.py
│   └── tests/
│       ├── test_circuit_breaker.py
│       └── test_policy.py
├── frontend/
│   ├── .env.example
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       └── styles.css
└── docs/
    └── MVP-architecture.md
```
