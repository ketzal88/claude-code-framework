#!/bin/bash
RULES_DIR="$(dirname "$0")/rules"
EXIT_CODE=0
for rule in "$RULES_DIR"/*.yml; do
  echo "-- $(basename "$rule" .yml) --"
  ast-grep scan --rule "$rule" 2>&1
  [ $? -ne 0 ] && EXIT_CODE=1
done
exit $EXIT_CODE
