#!/usr/bin/env python3
"""Generate the visual geometry for encased cogwheels.

Create's casing does not paint the gap dark - it punches it transparent, so the
wheel turning inside is genuinely visible through the slot. That means the
encased wheel needs its *whole* disc, not just the teeth poking out: the hub and
web sit exactly at the height of the slot (y 6.55 to 9.45, against slot rows
6-9) and are what you see through it.

The one part that is dropped is the through-shaft, which spans the full block
and would poke out of the two axis faces where the casing is solid.

Derived from Create's own gear models so the teeth and UVs stay pixel-exact.

Usage: gen_cogwheel_geo.py <Create resource pack dir>
"""

import json
import os
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "packs/resource/models/blocks/morecreate")


def load(path):
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle, object_pairs_hook=OrderedDict)


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent="\t")
        handle.write("\n")


def build(source_geo, identifier, wheel_bone, spin_bone):
    """Everything from the wheel bone, hung off a bone the RPM animation drives."""
    description = OrderedDict(source_geo["description"])
    description["identifier"] = identifier
    cubes = next(b for b in source_geo["bones"] if b["name"] == wheel_bone).get("cubes", [])
    return OrderedDict([
        ("format_version", "1.12.0"),
        ("minecraft:geometry", [OrderedDict([
            ("description", description),
            ("bones", [
                OrderedDict([("name", "shaft_rotation"), ("pivot", [0, 8, 0])]),
                OrderedDict([
                    ("name", spin_bone),
                    ("parent", "shaft_rotation"),
                    ("pivot", [0, 8, 0]),
                    ("cubes", cubes),
                ]),
            ]),
        ])]),
    ]), len(cubes)


def main():
    create_rp = sys.argv[1]
    models = os.path.join(create_rp, "models/blocks/conductors")

    small = load(os.path.join(models, "gear.geo.json"))["minecraft:geometry"][0]
    # `rpm` is the bone Create's shared animation spins for a normal cogwheel.
    doc, count = build(small, "geometry.morecreate.encased_cogwheel", "cogwheel", "rpm")
    write(os.path.join(OUT, "encased_cogwheel.geo.json"), doc)
    print("encased_cogwheel:       %d cubes (teeth, web and hub; shaft dropped)" % count)

    large = load(os.path.join(models, "large_gear.geo.json"))["minecraft:geometry"][0]
    # The large wheel spins on its own `large_cogwheel` bone instead.
    doc, count = build(large, "geometry.morecreate.encased_large_cogwheel",
                       "adjust", "large_cogwheel")
    write(os.path.join(OUT, "encased_large_cogwheel.geo.json"), doc)
    print("encased_large_cogwheel: %d cubes (teeth, rim, spokes and hub; shaft dropped)" % count)


if __name__ == "__main__":
    main()
