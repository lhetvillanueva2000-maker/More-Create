#!/usr/bin/env python3
"""Generate the Encased Chain Drive block.

Create draws a chain run on the drive's *axis* faces - the ones showing the
sprocket - not on the faces where the blocks touch, because those are hidden
between two solid blocks. A lone drive shows a plain shaft hole; a drive with a
neighbour shows the chain wrapping its sprocket and heading off toward that
neighbour.

Which way the chain runs across an axis face depends on both the drive's own
axis and the direction of the run, so the state `morecreate:chain` names the
run as one of the two axes perpendicular to the drive:

    drive axis Z (facing north/south)  ->  a = X, b = Y
    drive axis X (facing east/west)    ->  a = Z, b = Y
    drive axis Y (facing up/down)      ->  a = X, b = Z

In every one of those, run `a` reads across the face and run `b` reads up it,
so `a` takes the horizontal chain texture and `b` the vertical one.
"""

import json
import os
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "packs/behavior/blocks/morecreate/encased_chain_drive.b.json")

SIDE = "morecreate:encased_chain_drive"
HOLE = "morecreate:chain_drive_face"
LINK_H = "morecreate:chain_drive_link_h"
LINK_V = "morecreate:chain_drive_link_v"

# drive axis -> the two block faces along it
AXIS_FACES = OrderedDict([
    ("z", ("north", "south")),
    ("x", ("east", "west")),
    ("y", ("up", "down")),
])
AXIS_CONDITION = {
    "z": "q.block_state('minecraft:block_face') == 'north' || q.block_state('minecraft:block_face') == 'south'",
    "x": "q.block_state('minecraft:block_face') == 'east' || q.block_state('minecraft:block_face') == 'west'",
    "y": "q.block_state('minecraft:block_face') == 'up' || q.block_state('minecraft:block_face') == 'down'",
}

TOOL_SPEEDS = [
    ("wooden_tier", 1.15), ("stone_tier", 0.6), ("copper_tier", 0.5),
    ("iron_tier", 0.4), ("golden_tier", 0.2), ("diamond_tier", 0.3),
    ("netherite_tier", 0.25),
]


def destructible():
    return OrderedDict([
        ("seconds_to_destroy", 7.5),
        ("item_specific_speeds", [
            OrderedDict([
                ("item", {"tags": "(q.all_tags('minecraft:is_axe', 'minecraft:%s') "
                                  "|| q.all_tags('minecraft:is_pickaxe', 'minecraft:%s'))" % (tier, tier)}),
                ("destroy_speed", speed),
            ])
            for tier, speed in TOOL_SPEEDS
        ]),
    ])


def face_materials(axis, chain):
    """Texture for every face of a drive on `axis` with run state `chain`."""
    texture = {"none": HOLE, "a": LINK_H, "b": LINK_V}[chain]
    materials = OrderedDict([("*", {"texture": SIDE, "render_method": "opaque"})])
    for face in AXIS_FACES[axis]:
        materials[face] = {"texture": texture, "render_method": "opaque"}
    return materials


def main():
    doc = OrderedDict([
        ("format_version", "1.26.10"),
        ("minecraft:block", OrderedDict([
            ("description", OrderedDict([
                ("identifier", "morecreate:encased_chain_drive"),
                ("menu_category", {"category": "items"}),
                ("states", {"morecreate:chain": ["none", "a", "b"]}),
                ("traits", {"minecraft:placement_position": {
                    "enabled_states": ["minecraft:block_face"]}}),
            ])),
            ("components", OrderedDict([
                ("create:rpm_system", {}),
                ("minecraft:map_color", "#8B6C4D"),
                ("minecraft:geometry", "minecraft:geometry.full_block"),
                ("minecraft:redstone_conductivity", {"redstone_conductor": True}),
                ("minecraft:destruction_particles", {"texture": SIDE}),
                ("minecraft:material_instances", face_materials("y", "none")),
                ("minecraft:destructible_by_mining", destructible()),
            ])),
            ("permutations", [
                OrderedDict([
                    ("condition", "(%s) && q.block_state('morecreate:chain') == '%s'"
                                  % (AXIS_CONDITION[axis], chain)),
                    ("components", {"minecraft:material_instances": face_materials(axis, chain)}),
                ])
                for axis in AXIS_FACES
                for chain in ("none", "a", "b")
            ]),
        ])),
    ])

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(doc, handle, indent=4)
        handle.write("\n")
    count = len(doc["minecraft:block"]["permutations"])
    print("wrote %s with %d permutations" % (os.path.relpath(OUT, ROOT), count))


if __name__ == "__main__":
    main()
