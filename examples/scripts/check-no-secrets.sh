#!/bin/bash
# Pre-commit secret scanner. Invoked by settings.json PreToolUse on `git commit`.
#
# IMPORTANT: Must run as PreToolUse, NOT PostToolUse.
# After a commit completes, `git diff --cached` is empty — PostToolUse would never catch anything.
#
# Scans both:
#   1. Filenames — blocks .env*, *credentials*, *secret* files
#   2. File contents — blocks known secret patterns in staged diffs

set -euo pipefail

STAGED=$(git diff --cached --name-only 2>/dev/null || true)

if [ -z "$STAGED" ]; then
    exit 0
fi

# ── 1. Filename check ──────────────────────────────────────────────────────────
for file in $STAGED; do
    if [[ "$file" == *.env ]] || [[ "$file" == *.env.* ]] || \
       [[ "$file" == *credentials* ]] || [[ "$file" == *secret* && "$file" != *secret*.md ]]; then
        echo "BLOCKED: $file looks like a secrets file. Use environment variables instead."
        exit 1
    fi
done

# ── 2. Content patterns check ──────────────────────────────────────────────────
# Scan the staged diff for known secret patterns.
DIFF=$(git diff --cached -U0 2>/dev/null || true)

if [ -z "$DIFF" ]; then
    exit 0
fi

PATTERNS=(
    # PEM private keys
    'BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY'
    # AWS
    'AKIA[0-9A-Z]{16}'
    # Google OAuth client secrets
    '"client_secret"\s*:\s*"[A-Za-z0-9_\-]+'
    # Slack tokens
    'xox[baprs]-[0-9A-Za-z\-]+'
    # Anthropic / OpenAI API keys
    'sk-ant-[A-Za-z0-9\-_]+'
    'sk-[A-Za-z0-9]{32,}'
    # Generic high-entropy assignments (api_key=, apiKey=, ACCESS_TOKEN=)
    '(api[_-]?key|apikey|access[_-]?token|auth[_-]?token)\s*[=:]\s*["\x27][A-Za-z0-9_\-\.]{16,}'
    # Meta long-lived tokens
    'EAAl[A-Za-z0-9]+'
)

FOUND=0
for pattern in "${PATTERNS[@]}"; do
    if echo "$DIFF" | grep -qiE "$pattern" 2>/dev/null; then
        echo "BLOCKED: staged diff matches secret pattern: $pattern"
        FOUND=1
    fi
done

if [ "$FOUND" -eq 1 ]; then
    echo "Remove the secret, add the file to .gitignore, and use environment variables."
    exit 1
fi

exit 0
