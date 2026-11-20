# First prompt for Claude Code

Open the `sentinelgate-ai-mvp` repository and read `CLAUDE.md` and `README.md` first.

You are continuing an existing SentinelGate AI MVP. Do not recreate the project or replace the current UI. Inspect the current code, verify the backend API and React dashboard, and keep the scope limited to this MVP.

Tasks:
1. Check Python and Node versions and install the dependencies from the existing requirements/package files.
2. Run the backend tests and frontend production build. Fix only errors that are reproducible.
3. Start the FastAPI backend and Vite frontend and verify the four dashboard scenarios:
   - trusted invoice read -> ALLOW;
   - indirect prompt injection + sensitive external email -> BLOCK;
   - unauthorized `delete_database` -> BLOCK;
   - unknown provenance -> REVIEW.
4. Verify that BLOCK and REVIEW never execute a tool and that every tool remains a sandbox/mock action.
5. Verify the backend—not the frontend—owns agent capabilities. Do not accept client-provided permissions as authority.
6. Review the optional prompt-classifier configuration. Do not call the default heuristic scanner an SLM. If the optional model is unavailable, keep the app working and accurately label the fallback.
7. Report exact commands, tests, build status, screenshots/URLs available locally, changed files, and remaining limitations.

Do not connect real email, banking, payment, file-system, shell, or database integrations. Do not claim production readiness, security certification, or benchmark performance without measured evidence.
