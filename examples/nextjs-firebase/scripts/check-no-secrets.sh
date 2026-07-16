#!/usr/bin/env bash
# Pre-commit secret scanner for ExampleApp.
# Exits non-zero if staged files contain likely secrets.
# Usage: called from .claude/settings.json PreToolUse hook on `git commit`.

set -e

STAGED=$(git diff --cached --name-only --diff-filter=ACM)
if [ -z "$STAGED" ]; then
  exit 0
fi

# Patterns that indicate a likely secret leak.
# Each pattern is tuned to avoid false positives on placeholder values.
PATTERNS=(
  # Firebase private keys
  "BEGIN PRIVATE KEY"
  "BEGIN RSA PRIVATE KEY"
  # Generic API key patterns (long hex/b64 values assigned to suspicious var names)
  "(api[_-]?key|access[_-]?token|client[_-]?secret|refresh[_-]?token|private[_-]?key)[[:space:]]*[:=][[:space:]]*['\"][A-Za-z0-9_\\-]{32,}['\"]" 
  # AWS
  "AKIA[0-9A-Z]{16}"
  # Google OAuth
  "AIza[0-9A-Za-z_\\-]{35}"
  # Anthropic / OpenAI
  "sk-ant-[a-zA-Z0-9_\\-]{32,}"
  "sk-proj-[a-zA-Z0-9_\\-]{32,}"
  # Slack
  "xox[baprs]-[0-9]+-[0-9]+-[0-9]+-[a-fA-F0-9]{24,}"
  # Meta / Facebook long-lived tokens (rough)
  "EAA[A-Za-z0-9]{100,}"
)

FOUND=0
for file in $STAGED; do
  # Skip the scanner itself and .env.example
  case "$file" in
    scripts/check-no-secrets.sh|.env.example|.env.sample|**/*.md) continue;;
  esac

  # Only scan text files
  if ! file "$file" 2>/dev/null | grep -q text; then
    continue
  fi

  for pat in "${PATTERNS[@]}"; do
    if git diff --cached "$file" | grep -E "$pat" >/dev/null 2>&1; then
      echo "❌ Possible secret in $file (pattern: $pat)"
      FOUND=1
    fi
  done
done

if [ "$FOUND" -ne 0 ]; then
  echo ""
  echo "Commit blocked by check-no-secrets.sh"
  echo "If this is a false positive, commit with --no-verify (requires explicit user approval per CLAUDE.md)."
  exit 1
fi

exit 0
