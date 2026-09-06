#!/usr/bin/env python3
"""Package the two packs into dist/MoreCreate.mcaddon.

An .mcaddon is a plain zip holding one folder per pack, each with its own
manifest. Minecraft imports both when the file is opened.
"""

import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")

# Release numbering: v<major>.<minor>, minor rolling into major at 10
# (v1.9 is followed by v2.0). Bump this when cutting a release.
VERSION = "1.6"
OUTPUT = os.path.join(DIST, "MoreCreate-v%s.mcaddon" % VERSION)

PACKS = [
    (os.path.join(ROOT, "packs/behavior"), "More Create BP"),
    (os.path.join(ROOT, "packs/resource"), "More Create RP"),
]

SKIP_NAMES = {".DS_Store", "Thumbs.db"}
SKIP_SUFFIXES = (".pyc",)


def main():
    os.makedirs(DIST, exist_ok=True)
    if os.path.exists(OUTPUT):
        os.remove(OUTPUT)

    count = 0
    total = 0
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for source, folder in PACKS:
            if not os.path.isdir(source):
                print("missing pack directory: %s" % source, file=sys.stderr)
                return 1
            for base, dirs, files in os.walk(source):
                dirs[:] = sorted(d for d in dirs if not d.startswith("."))
                for name in sorted(files):
                    if name in SKIP_NAMES or name.endswith(SKIP_SUFFIXES):
                        continue
                    path = os.path.join(base, name)
                    arc = os.path.join(folder, os.path.relpath(path, source))
                    bundle.write(path, arc.replace(os.sep, "/"))
                    count += 1
                    total += os.path.getsize(path)

    size = os.path.getsize(OUTPUT)
    print("wrote %s" % os.path.relpath(OUTPUT, ROOT))
    print("   %d files, %.1f KiB raw -> %.1f KiB packed" % (count, total / 1024, size / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
