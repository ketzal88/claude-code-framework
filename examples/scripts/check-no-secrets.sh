#!/bin/bash
# Block commits containing secrets. Used by settings.json hook.
STAGED=$(git diff --cached --name-only)
for file in $STAGED; do
  if [[ "$file" == *.env* ]] || [[ "$file" == *credentials* ]]; then
    echo "BLOCKED: $file looks like it contains secrets."
    exit 1
  fi
done
exit 0
