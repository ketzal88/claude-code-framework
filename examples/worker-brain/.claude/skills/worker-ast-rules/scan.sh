#!/usr/bin/env bash
# Worker Brain — AST rules scanner
# Runs all ast-grep rules against the repo. Non-zero exit if any `error` hits.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

if ! command -v ast-grep >/dev/null 2>&1; then
  echo "❌ ast-grep not found. Install with:"
  echo "   npm install -g @ast-grep/cli"
  exit 127
fi

cd "$REPO_ROOT"

echo "🔍 Running worker-ast-rules against $REPO_ROOT"
echo ""

# Run all rules via the sgconfig. ast-grep returns 0 if clean, non-zero otherwise.
# --error elevates warning rules too? No — we keep severity as declared in each rule.
ast-grep scan --config "$SCRIPT_DIR/sgconfig.yml" .

EXIT=$?

if [ $EXIT -eq 0 ]; then
  echo ""
  echo "✅ All worker-ast-rules passed."
else
  echo ""
  echo "⚠️  worker-ast-rules reported issues. See above."
  echo "   error-severity hits fail CI. Warnings are informational."
fi

exit $EXIT