#!/usr/bin/env python3
"""Generate the encased shaft / cogwheel / large cogwheel blocks.

Create's kinetic blocks (shaft, cogwheel, large cogwheel) render as *invisible*
blocks; the part you actually see is a visual entity that the RPM system spawns
on top of them.  That is what lets More Create hide a shaft: the encased shaft
is a full, opaque casing block registered with ``noEntity``, so no visual entity
is ever spawned and the shaft is gone from view while the kinetic network still
runs straight through it.

Encased cogwheels keep a visual entity, but its geometry only contains the outer
tooth ring - the hub and the through-shaft are sliced away because the casing
block already occupies that space.

One block id per (casing, kind) pair keeps the casing material intact when the
block is broken: each variant carries its own static loot table, so no script is
involved in dropping the parts back.
"""

import json
import os
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOCK_DIR = os.path.join(ROOT, "packs/behavior/blocks/morecreate/encased")
LOOT_DIR = os.path.join(ROOT, "packs/behavior/loot_tables/morecreate")

CASINGS = OrderedDict([
    # name        casing block id             terrain texture key        map colour
    ("andesite", ("create:andesite_casing", "create:andesite_casing", "#8B6C4D")),
    ("brass",    ("create:brass_casing",    "create:brass_casing",    "#C7A44A")),
    ("copper",   ("create:copper_casing",   "create:copper_casing",   "#5E9E7E")),
    ("creative", ("create:creative_casing", "create:creative_casing", "#A44FA8")),
])

KINDS = OrderedDict([
    # kind             kinetic block dropped     placement trait
    ("shaft",          ("create:shaft",          "position")),
    ("cogwheel",       ("create:cogwheel",       "direction")),
    ("large_cogwheel", ("create:large_cogwheel", "direction")),
])

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


def materials(casing, kind):
    """Face textures for one encased block.

    A shaft is hidden completely, so its casing is blank on all six sides. A
    cogwheel is only sliced in half by the casing - Create draws the gap it
    shows through with a dedicated `*_encased_cogwheel_side` texture, a dark
    slot across the middle of the casing.

    The base orientation here is a cogwheel spinning on the north-south axis,
    the same one Create's own cogwheel block is authored in, so the two are
    rotated by the identical transformation table below. North and south are
    the axis faces and stay plain; the other four are cut by the wheel. On the
    top and bottom the slot runs across X, and on east and west it runs across
    Y, which is why there are separate `_h` and `_v` textures.
    """
    _, plain, _ = CASINGS[casing]
    if kind == "shaft":
        return {"*": {"texture": plain, "render_method": "opaque"}}
    return OrderedDict([
        ("*", {"texture": plain, "render_method": "opaque"}),
        ("north", {"texture": plain, "render_method": "opaque"}),
        ("south", {"texture": plain, "render_method": "opaque"}),
        ("up", {"texture": "morecreate:%s_encased_cogwheel_h" % casing, "render_method": "opaque"}),
        ("down", {"texture": "morecreate:%s_encased_cogwheel_h" % casing, "render_method": "opaque"}),
        ("east", {"texture": "morecreate:%s_encased_cogwheel_v" % casing, "render_method": "opaque"}),
        ("west", {"texture": "morecreate:%s_encased_cogwheel_v" % casing, "render_method": "opaque"}),
    ])


def block(casing, kind):
    casing_block, texture, map_color = CASINGS[casing]
    _, trait = KINDS[kind]
    identifier = "morecreate:%s_encased_%s" % (casing, kind)

    if trait == "position":
        traits = {"minecraft:placement_position": {"enabled_states": ["minecraft:block_face"]}}
    else:
        traits = {"minecraft:placement_direction": {"enabled_states": ["minecraft:facing_direction"]}}

    components = OrderedDict([
        ("create:rpm_system", {}),
        ("minecraft:map_color", map_color),
        ("minecraft:geometry", "minecraft:geometry.full_block"),
        ("minecraft:material_instances", materials(casing, kind)),
        ("minecraft:destruction_particles", {"texture": texture}),
        ("minecraft:redstone_conductivity", {"redstone_conductor": True}),
        ("minecraft:loot", "loot_tables/morecreate/%s_encased_%s.json" % (casing, kind)),
        ("minecraft:destructible_by_mining", destructible()),
    ])

    doc = OrderedDict([
        ("format_version", "1.26.10"),
        ("minecraft:block", OrderedDict([
            ("description", OrderedDict([
                ("identifier", identifier),
                ("traits", traits),
            ])),
            ("components", components),
        ])),
    ])

    if kind != "shaft":
        # Same rotation table Create uses for its own cogwheel, so an encased
        # wheel lines up with the plain one it was made from. The cube is
        # rotated bodily, which carries the slot textures round with it.
        components["minecraft:transformation"] = {"rotation": [90, 0, 0]}
        doc["minecraft:block"]["permutations"] = [
            OrderedDict([
                ("condition", "q.block_state('minecraft:facing_direction') == 'north' "
                              "|| q.block_state('minecraft:facing_direction') == 'south'"),
                ("components", {"minecraft:transformation": {"rotation": [0, 0, 0]}}),
            ]),
            OrderedDict([
                ("condition", "q.block_state('minecraft:facing_direction') == 'west' "
                              "|| q.block_state('minecraft:facing_direction') == 'east'"),
                ("components", {"minecraft:transformation": {"rotation": [0, 90, 0]}}),
            ]),
        ]
    return doc


def loot(casing, kind):
    casing_block, _, _ = CASINGS[casing]
    kinetic, _ = KINDS[kind]
    return OrderedDict([
        ("pools", [
            {"rolls": 1, "entries": [{"type": "item", "name": kinetic, "weight": 1}]},
            {"rolls": 1, "entries": [{"type": "item", "name": casing_block, "weight": 1}]},
        ])
    ])


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4)
        handle.write("\n")


def main():
    written = []
    for casing in CASINGS:
        for kind in KINDS:
            stem = "%s_encased_%s" % (casing, kind)
            write(os.path.join(BLOCK_DIR, stem + ".b.json"), block(casing, kind))
            write(os.path.join(LOOT_DIR, stem + ".json"), loot(casing, kind))
            written.append(stem)
    print("generated %d encased blocks + loot tables" % len(written))
    for stem in written:
        print("   morecreate:" + stem)


if __name__ == "__main__":
    main()
