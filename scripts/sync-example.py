#!/usr/bin/env python3
"""Sync an example dir from a real project, with sanitization built in.

Usage:
    python scripts/sync-example.py <project-root> <example-dir>
    python scripts/sync-example.py ~/code/my-app examples/nextjs-firebase

Reads <example-dir>/sync-manifest.json:

    {
      "map": { "<dest relative to example-dir>": "<source relative to project-root>" },
      "replacements": [ { "pattern": "<regex>", "replace": "<text>" } ]
    }

For each map entry: copy source -> dest, then apply every replacement
(regex, in order) so private names/domains never reach the public repo.
Exits 1 if any source file is missing (the mirror would silently rot).

This encodes the "distillation rule": the mirror update is 1 command,
not a hand-run session workflow that re-discovers the file list each time.
"""
import io
import json
import os
import re
import sys


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    project_root, example_dir = sys.argv[1], sys.argv[2]
    manifest_path = os.path.join(example_dir, "sync-manifest.json")
    if not os.path.isfile(manifest_path):
        print(f"sync-example: no {manifest_path} — create it first (see examples/nextjs-firebase/sync-manifest.json)")
        return 1

    manifest = json.load(io.open(manifest_path, encoding="utf-8"))
    mapping = manifest.get("map", {})
    replacements = [(re.compile(r["pattern"]), r["replace"]) for r in manifest.get("replacements", [])]

    missing, synced = [], 0
    for dest_rel, src_rel in sorted(mapping.items()):
        src = os.path.join(project_root, src_rel)
        dest = os.path.join(example_dir, dest_rel)
        if not os.path.isfile(src):
            missing.append(src_rel)
            continue
        content = io.open(src, encoding="utf-8", errors="replace").read()
        for pat, rep in replacements:
            content = pat.sub(rep, content)
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
        io.open(dest, "w", encoding="utf-8", newline="\n").write(content)
        synced += 1
        print(f"  synced {dest_rel}")

    print(f"\nsync-example: {synced} file(s) synced, {len(missing)} missing")
    if missing:
        print("MISSING sources (mirror would rot — fix the manifest or the project):")
        for m in missing:
            print(f"  {m}")
        return 1

    # Post-sync leak check: no private identifier may survive a replacement pass.
    leak_patterns = manifest.get("leakCheck", [])
    if leak_patterns:
        leak_re = re.compile("|".join(leak_patterns), re.I)
        leaks = []
        for dest_rel in mapping:
            p = os.path.join(example_dir, dest_rel)
            for i, line in enumerate(io.open(p, encoding="utf-8", errors="replace")):
                if leak_re.search(line):
                    leaks.append(f"{dest_rel}:{i + 1}: {line.strip()[:100]}")
        if leaks:
            print("\nLEAK CHECK FAILED — private references survived sanitization:")
            for leak in leaks[:20]:
                print(f"  {leak}")
            return 1
        print("leak check: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
