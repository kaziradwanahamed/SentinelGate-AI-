#!/usr/bin/env bash
set -euo pipefail
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BACKEND_DIR"
if [[ ! -x "$BACKEND_DIR/.venv/bin/python" ]]; then
  echo "SentinelGate backend venv not found. Create it and install requirements first." >&2
  exit 1
fi
exec "$BACKEND_DIR/.venv/bin/python" -m app.mcp_server
