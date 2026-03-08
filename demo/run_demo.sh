#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== RuneGard Demo ==="
echo ""

echo "Step 1: Parse the runbook"
uv run python -m runegard parse "$SCRIPT_DIR/assets/runbooks/crashloop.md"

echo ""
echo "Step 2: Execute (interactive mode)"
uv run python -m runegard run "$SCRIPT_DIR/assets/runbooks/crashloop.md" --trace-dir "$SCRIPT_DIR"

echo ""
echo "Step 3: Analyze and improve"
uv run python -m runegard improve "$SCRIPT_DIR/trace_log.json" \
  --runbook "$SCRIPT_DIR/assets/runbooks/crashloop.md" \
  --patterns "$SCRIPT_DIR/references/learned_patterns.md"
