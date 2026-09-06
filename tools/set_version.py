#!/usr/bin/env python3
"""Stamp the release number into both manifests.

Every release up to v1.7 shipped `"version": [1, 0, 0]` in both manifests.
Minecraft identifies an installed pack by UUID *and* version, so importing a new
`.mcaddon` whose packs claim the version already installed does not reliably
replace them - the world keeps running the copy it already has. That is why a
fix could be built, published and downloaded and still not show up in game.

The pack version now follows the release: v1.8 becomes `[1, 8, 0]`. Run this
after bumping `VERSION` in `build.py` and before building, or just run
`build.py`, which calls it.

Usage: set_version.py [version]      (defaults to build.py's VERSION)
"""

import json
import os
import re
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFESTS = [
    os.path.join(ROOT, "packs/behavior/manifest.json"),
    os.path.join(ROOT, "packs/resource/manifest.json"),
]


def build_version():
    text = open(os.path.join(ROOT, "tools/build.py"), encoding="utf-8").read()
    found = re.search(r'^VERSION\s*=\s*"([\d.]+)"', text, re.M)
    if not found:
        raise SystemExit("could not find VERSION in build.py")
    return found.group(1)


def as_triple(version):
    parts = [int(piece) for piece in version.split(".")]
    while len(parts) < 3:
        parts.append(0)
    return parts[:3]


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else build_version()
    triple = as_triple(version)

    for path in MANIFESTS:
        with open(path, encoding="utf-8-sig") as handle:
            manifest = json.load(handle, object_pairs_hook=OrderedDict)
        manifest["header"]["version"] = triple
        for module in manifest.get("modules", []):
            module["version"] = triple
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=4)
            handle.write("\n")
        print("  %-28s version -> %s" % (os.path.relpath(path, ROOT), triple))
    return 0


if __name__ == "__main__":
    sys.exit(main())
