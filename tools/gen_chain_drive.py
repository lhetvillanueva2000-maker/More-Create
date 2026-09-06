#!/usr/bin/env python3
"""Generate the Encased Chain Drive block and its item geometry.

Create draws a chain run on the drive's *axis* faces - the ones showing the
sprocket - not on the faces where two drives touch, because those are hidden
between solid blocks. Which texture a face uses depends on the neighbours:

    no neighbours   plain shaft hole
    one neighbour   end texture, chain leaving toward that neighbour
    both sides      middle texture, chain straight through

The end texture is asymmetric, and the drive's two axis faces look at each other
from opposite sides, so each takes the variant that points the chain at the same
world neighbour. `FACE_TOWARD` is that mapping: for every axis face, which end
variant sends the chain toward a given world direction.

Placement uses `facing_direction` rather than the clicked block face, so the
shaft points at the player the way Create's own cogwheel does - putting one down
on the ground gives a horizontal drive, not one standing on end.
"""

import json
import os
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOCK_OUT = os.path.join(ROOT, "packs/behavior/blocks/morecreate/encased_chain_drive.b.json")
GEO_OUT = os.path.join(ROOT, "packs/resource/models/blocks/morecreate/encased_chain_drive_item.geo.json")

SIDE = "morecreate:encased_chain_drive"
HOLE = "morecreate:chain_drive_face"
LINK_H = "morecreate:chain_drive_link_h"
LINK_V = "morecreate:chain_drive_link_v"
END = {d: "morecreate:chain_drive_end_%s" % d for d in ("right", "left", "up", "down")}

OPPOSITE = {"north": "south", "south": "north", "east": "west",
            "west": "east", "up": "down", "down": "up"}

# Drive axis -> its two axis faces, and the two perpendicular run axes.
# `a` always reads across an axis face and `b` always reads up it, which is why
# a-runs take the horizontal middle texture and b-runs the vertical one.
AXES = OrderedDict([
    ("z", {"faces": ("north", "south"), "a": ("east", "west"), "b": ("up", "down")}),
    ("x", {"faces": ("east", "west"), "a": ("south", "north"), "b": ("up", "down")}),
    ("y", {"faces": ("up", "down"), "a": ("east", "west"), "b": ("south", "north")}),
])
AXIS_FACING = {
    "z": ("north", "south"),
    "x": ("east", "west"),
    "y": ("up", "down"),
}

# For each axis face, which end variant runs the chain toward a world direction.
# Derived from which way each face is seen from: the north face shows +X to the
# right, the south face - looking at it from the other side - shows +X to the
# left, and so on. If a chain ever points away from its neighbour in game, these
# are the only lines that need flipping.
FACE_TOWARD = {
    "north": {"east": "right", "west": "left", "up": "up", "down": "down"},
    "south": {"east": "left", "west": "right", "up": "up", "down": "down"},
    "east": {"south": "right", "north": "left", "up": "up", "down": "down"},
    "west": {"north": "right", "south": "left", "up": "up", "down": "down"},
    "up": {"east": "right", "west": "left", "south": "down", "north": "up"},
    "down": {"east": "right", "west": "left", "north": "down", "south": "up"},
}

TOOL_SPEEDS = [
    ("wooden_tier", 1.15), ("stone_tier", 0.6), ("copper_tier", 0.5),
    ("iron_tier", 0.4), ("golden_tier", 0.2), ("diamond_tier", 0.3),
    ("netherite_tier", 0.25),
]

# none, chain through on either run axis, or an end pointing each of four ways.
STATES = ["none", "mid_a", "mid_b", "end_a1", "end_a2", "end_b1", "end_b2"]


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


def opaque(texture):
    return {"texture": texture, "render_method": "opaque"}


def materials(axis, state):
    spec = AXES[axis]
    faces = OrderedDict([("*", opaque(SIDE))])

    if state == "none":
        for face in spec["faces"]:
            faces[face] = opaque(HOLE)
        return faces

    if state.startswith("mid"):
        link = LINK_H if state.endswith("a") else LINK_V
        for face in spec["faces"]:
            faces[face] = opaque(link)
        return faces

    run_axis, which = state[4], state[5]
    toward = spec[run_axis][0 if which == "1" else 1]
    for face in spec["faces"]:
        faces[face] = opaque(END[FACE_TOWARD[face][toward]])
    return faces


def condition(axis, state):
    facings = " || ".join("q.block_state('minecraft:facing_direction') == '%s'" % f
                          for f in AXIS_FACING[axis])
    return "(%s) && q.block_state('morecreate:chain') == '%s'" % (facings, state)


def block():
    return OrderedDict([
        ("format_version", "1.26.10"),
        ("minecraft:block", OrderedDict([
            ("description", OrderedDict([
                ("identifier", "morecreate:encased_chain_drive"),
                ("menu_category", {"category": "items"}),
                ("states", {"morecreate:chain": STATES}),
                ("traits", {"minecraft:placement_direction": {
                    "enabled_states": ["minecraft:facing_direction"]}}),
            ])),
            ("components", OrderedDict([
                ("create:rpm_system", {}),
                ("minecraft:map_color", "#8B6C4D"),
                ("minecraft:geometry", "minecraft:geometry.full_block"),
                ("minecraft:redstone_conductivity", {"redstone_conductor": True}),
                ("minecraft:destruction_particles", {"texture": SIDE}),
                ("minecraft:material_instances", materials("z", "none")),
                # In the inventory the plain cube showed no shaft at all, so the
                # item gets its own model with the stubs on, lying on the Z axis
                # the way the block does when you place it facing you.
                ("minecraft:item_visual", OrderedDict([
                    ("geometry", {"identifier": "geometry.morecreate.encased_chain_drive_item"}),
                    ("material_instances", OrderedDict([
                        ("*", {"texture": SIDE, "render_method": "opaque",
                               "ambient_occlusion": False}),
                        ("hole", {"texture": HOLE, "render_method": "opaque",
                                  "ambient_occlusion": False}),
                        ("shaft", {"texture": "create:shaft", "render_method": "alpha_test",
                                   "ambient_occlusion": False}),
                    ])),
                ])),
                ("minecraft:destructible_by_mining", destructible()),
            ])),
            ("permutations", [
                OrderedDict([
                    ("condition", condition(axis, state)),
                    ("components", {"minecraft:material_instances": materials(axis, state)}),
                ])
                for axis in AXES
                for state in STATES
            ]),
        ])),
    ])


def face(uv, instance):
    return OrderedDict([("uv", uv), ("uv_size", [16, 16]), ("material_instance", instance)])


def item_geometry():
    """A full cube with the shaft stubs on, for the inventory and hand."""
    body = OrderedDict([
        ("origin", [-8, 0, -8]), ("size", [16, 16, 16]),
        ("uv", OrderedDict([
            ("north", face([0, 0], "hole")),
            ("south", face([0, 0], "hole")),
            ("east", face([0, 0], "side")),
            ("west", face([0, 0], "side")),
            ("up", face([0, 0], "side")),
            ("down", face([0, 0], "side")),
        ])),
    ])
    stub = lambda z: OrderedDict([
        ("origin", [-2, 6, z]), ("size", [4, 4, 2]),
        ("uv", OrderedDict([
            (name, OrderedDict([("uv", [0, 0]), ("uv_size", [4, 4]),
                                ("material_instance", "shaft")]))
            for name in ("north", "south", "east", "west", "up", "down")
        ])),
    ])
    return OrderedDict([
        ("format_version", "1.16.0"),
        ("minecraft:geometry", [OrderedDict([
            ("description", OrderedDict([
                ("identifier", "geometry.morecreate.encased_chain_drive_item"),
                ("texture_width", 16), ("texture_height", 16),
                ("visible_bounds_width", 3), ("visible_bounds_height", 3),
                ("visible_bounds_offset", [0, 1, 0]),
            ])),
            ("bones", [OrderedDict([
                ("name", "drive"), ("pivot", [0, 8, 0]),
                ("cubes", [body, stub(-10), stub(8)]),
            ])]),
        ])]),
    ])


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4)
        handle.write("\n")


def main():
    doc = block()
    write(BLOCK_OUT, doc)
    write(GEO_OUT, item_geometry())
    print("wrote %s (%d permutations, %d states)"
          % (os.path.relpath(BLOCK_OUT, ROOT),
             len(doc["minecraft:block"]["permutations"]), len(STATES)))
    print("wrote %s" % os.path.relpath(GEO_OUT, ROOT))
    for axis in AXES:
        pair = AXES[axis]["faces"]
        got = materials(axis, "end_a1")
        print("  axis %s, neighbour %-5s -> %s=%s  %s=%s"
              % (axis, AXES[axis]["a"][0],
                 pair[0], got[pair[0]]["texture"].split(":")[1],
                 pair[1], got[pair[1]]["texture"].split(":")[1]))


if __name__ == "__main__":
    main()
