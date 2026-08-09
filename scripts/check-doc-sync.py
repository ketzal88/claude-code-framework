#!/usr/bin/env python3
"""Doc-sync gate for the framework itself (the framework preaches doc-sync gates — it needs its own).

Checks, exit 1 on any failure:
  1. Every file in core/rules/ and core/commands/ is mentioned in README.md.
  2. Every hook script referenced by core/hooks/settings.template.json exists.
  3. No file leaks a private name, project name or developer path (this repo is
     public — the example must stay generic).
  4. stack.example.json and every examples/*/stack.json use only top-level keys
     declared in stack.schema.json.
  5. Every mirrored file under examples/<ex>/{rules,commands,scripts} is declared
     in that example's sync-manifest.json, either in "map" (synced from the source
     project) or in "unsynced" (deliberately example-only). Without this, a file
     can sit in the mirror for months without ever being synced or reviewed —
     which is exactly how the mirror drifted from its source.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Private/identifying strings that must never appear in this public repo.
# The sanitizer in sync-example.py strips these on the way in; this gate is the
# backstop for files it does not cover (anything outside a manifest "map").
RETIRED_NAMES = [
    r"worker-brain",
    r"Worker[ _-]?Brain",
    r"ai-analyzer",
    r"Users[\\/]gabri",
]

errors = []


def read(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


# 1. core/rules + core/commands mentioned in README
readme = read(os.path.join(REPO, "README.md"))
for sub in ("rules", "commands"):
    d = os.path.join(REPO, "core", sub)
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".md") and fn not in readme:
            errors.append(f"README.md does not mention core/{sub}/{fn}")

# 2. settings.template.json scripts exist
template = read(os.path.join(REPO, "core", "hooks", "settings.template.json"))
for m in re.finditer(r"core/hooks/scripts/([\w.-]+)", template):
    p = os.path.join(REPO, "core", "hooks", "scripts", m.group(1))
    if not os.path.isfile(p):
        errors.append(f"settings.template.json references missing script: {m.group(1)}")

# 3. retired names anywhere (text files only)
for dirpath, dirnames, filenames in os.walk(REPO):
    if ".git" in dirpath.split(os.sep):
        continue
    for fn in filenames:
        if not fn.endswith((".md", ".py", ".js", ".mjs", ".sh", ".json", ".yml", ".yaml", ".txt")):
            continue
        rel = os.path.relpath(os.path.join(dirpath, fn), REPO).replace("\\", "/")
        # Exempt: this checker, and sync manifests (they DECLARE the private
        # patterns precisely so the sanitizer can strip them).
        if rel == "scripts/check-doc-sync.py" or fn == "sync-manifest.json":
            continue
        content = read(os.path.join(dirpath, fn))
        for name in RETIRED_NAMES:
            if re.search(name, content, re.I):
                errors.append(f"{rel}: contains retired/private name matching '{name}'")

# 4. stack.json keys vs schema
schema = json.loads(read(os.path.join(REPO, "stack.schema.json")))
allowed = set(schema.get("properties", {}).keys())
stacks = [os.path.join(REPO, "stack.example.json")]
examples_dir = os.path.join(REPO, "examples")
if os.path.isdir(examples_dir):
    for ex in os.listdir(examples_dir):
        p = os.path.join(examples_dir, ex, "stack.json")
        if os.path.isfile(p):
            stacks.append(p)
for p in stacks:
    try:
        data = json.loads(read(p))
    except Exception as e:
        errors.append(f"{os.path.relpath(p, REPO)}: invalid JSON ({e})")
        continue
    extra = set(data.keys()) - allowed
    if extra:
        errors.append(f"{os.path.relpath(p, REPO)}: keys not in schema: {sorted(extra)}")

# 5. every mirrored file is declared in its example's sync-manifest
MIRRORED_DIRS = ("rules", "commands", "scripts")
if os.path.isdir(examples_dir):
    for ex in sorted(os.listdir(examples_dir)):
        manifest_path = os.path.join(examples_dir, ex, "sync-manifest.json")
        if not os.path.isfile(manifest_path):
            continue
        try:
            manifest = json.loads(read(manifest_path))
        except Exception as e:
            errors.append(f"examples/{ex}/sync-manifest.json: invalid JSON ({e})")
            continue
        declared = set(manifest.get("map", {}).keys()) | set(manifest.get("unsynced", []))
        for sub in MIRRORED_DIRS:
            d = os.path.join(examples_dir, ex, sub)
            if not os.path.isdir(d):
                continue
            for dirpath, _dirnames, filenames in os.walk(d):
                for fn in filenames:
                    rel = os.path.relpath(
                        os.path.join(dirpath, fn), os.path.join(examples_dir, ex)
                    ).replace("\\", "/")
                    if rel not in declared:
                        errors.append(
                            f"examples/{ex}/{rel} is not declared in sync-manifest.json "
                            f"(add it to \"map\" to sync it, or to \"unsynced\" if it is "
                            f"example-only on purpose)"
                        )

if errors:
    print("doc-sync FAILED:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
print("doc-sync OK — core files documented, template scripts exist, no retired names, stack keys valid.")
