#!/usr/bin/env python3
"""Generate the Encased Chain Drive by porting Create's own block models.

Earlier versions of this file guessed at the block's look: a plain full-block
cube with one texture per face, and hand-made mirrored copies of the end
texture. Both guesses were wrong in game, because Create's model does two things
a Bedrock `material_instances` cube cannot:

  * it rotates the texture per face (the casing's metal strip runs *around* the
    block, so the side faces use the side texture turned 90 and 270 degrees);
  * it distinguishes the two ends of a run by rotating the model 180 degrees,
    which is not the same as mirroring the texture - the frame's lit edge moves
    too.

So this reads `assets/create/models/block/encased_chain_drive/*.json` out of the
Create jar and converts them to Bedrock geometry, keeping every UV exactly as
Create authored it. Bedrock's per-face UV can express a 180 degree turn (negate
both `uv_size` components) but not 90 or 270, so those two are baked as rotated
copies of the texture and the UV rectangle is rotated to match.

Placement follows Create's blockstate: one geometry per part, positioned with
`minecraft:transformation`, whose rotations are the same x/y degrees the
blockstate uses.

Usage: gen_chain_drive.py <Create jar assets/create dir>
"""

import json
import os
import sys
from collections import OrderedDict

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOCK_OUT = os.path.join(ROOT, "packs/behavior/blocks/morecreate/encased_chain_drive.b.json")
GEO_OUT = os.path.join(ROOT, "packs/resource/models/blocks/morecreate/encased_chain_drive.geo.json")
TEX_OUT = os.path.join(ROOT, "packs/resource/textures/morecreate/blocks")

# Java model name -> the Bedrock geometry it becomes.
MODELS = ["single", "end_horizontal", "middle_horizontal",
          "end_vertical", "middle_vertical",
          # `item` is `single` with the shaft poking through, which is what the
          # inventory and the player's hand should show.
          "item"]

# Java texture name -> the key used in `minecraft:material_instances`. Bedrock
# material instance names have to be short identifiers, not paths.
TEXTURE_SLOTS = {
    "encased_chain_drive": "side",
    "encased_chain_drive_end": "end",
    "encased_chain_drive_middle": "middle",
    "gearbox": "hole",
    "axis": "shaft",
    "axis_top": "shafttop",
}

# Bedrock's cube faces do not all start from the same texture orientation Java's
# do, so a face can sample exactly the right pixels and still be turned. The
# east/west pair is 90 degrees out: on a lone drive Create's casing strip ran
# vertically there while running horizontally on the top and bottom, so the
# frame did not meet at the corners. Correcting those two makes it continuous.
FACE_ORIENTATION_FIX = {"east": 270, "west": 270}

TOOL_SPEEDS = [
    ("wooden_tier", 1.15), ("stone_tier", 0.6), ("copper_tier", 0.5),
    ("iron_tier", 0.4), ("golden_tier", 0.2), ("diamond_tier", 0.3),
    ("netherite_tier", 0.25),
]

# The block's own states. `part` mirrors Create's; `along` is Create's
# `axis_along_first`, which picks which of the two perpendicular directions a
# run travels in when a drive could belong to either.
PARTS = ["none", "start", "middle", "end"]

# The drive keeps `minecraft:facing_direction` as its orientation, because that
# is the state Create's rpm system already reads to find the shaft axis - the
# kinetics work and are not worth disturbing for a texture fix. The axis a
# permutation cares about is derived from it here instead.
AXIS_FACINGS = {"x": ("east", "west"), "y": ("up", "down"), "z": ("north", "south")}


def load(path):
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


# ------------------------------------------------------------------ textures

def bake_textures(source):
    """Copy Create's four textures, plus the 90/270 turns Bedrock cannot do."""
    os.makedirs(TEX_OUT, exist_ok=True)
    written = []
    for name in TEXTURE_SLOTS:
        image = Image.open(os.path.join(source, "textures/block", name + ".png")).convert("RGBA")
        if image.size != (16, 16):
            image = image.crop((0, 0, 16, 16))   # animated textures are strips
        for turn in (0, 90, 270):
            out = image if turn == 0 else image.rotate(-turn, expand=False)
            suffix = "" if turn == 0 else "_r%d" % turn
            path = os.path.join(TEX_OUT, name + suffix + ".png")
            out.save(path)
            written.append(os.path.basename(path))
    return written


def rotate_rect(x1, y1, x2, y2, turn):
    """Where a UV rectangle lands once the texture itself is turned.

    Turning the image moves the rectangle's *extent*, and the reading direction
    has to be restored separately: a rectangle Create wrote back-to-front (to
    flip the texture) must still read back-to-front afterwards, but about the
    other axis, because the turn swaps them. Deriving this by hand got it wrong
    twice, so the rule below was found by brute force and is locked in by
    `verify_chain_drive.py`.
    """
    low_x, high_x = sorted((x1, x2))
    low_y, high_y = sorted((y1, y2))
    flipped_x, flipped_y = x2 < x1, y2 < y1

    if turn == 90:
        ax, bx = 16 - high_y, 16 - low_y
        ay, by = low_x, high_x
    else:                                   # 270
        ax, bx = low_y, high_y
        ay, by = 16 - high_x, 16 - low_x

    if flipped_y:
        ax, bx = bx, ax
    if flipped_x:
        ay, by = by, ay
    return ax, ay, bx, by


def face_uv(java_face, slot_of, face=None):
    """One Java face -> Bedrock `uv` / `uv_size` / `material_instance`."""
    x1, y1, x2, y2 = java_face["uv"]
    rotation = (java_face.get("rotation", 0)
                + FACE_ORIENTATION_FIX.get(face, 0)) % 360
    name = java_face["texture"].lstrip("#")

    suffix = ""
    if rotation == 180:
        # Expressible directly: start from the far corner and walk backwards.
        x1, y1, x2, y2 = x2, y2, x1, y1
    elif rotation in (90, 270):
        # Not expressible - use the pre-turned texture and move the rectangle.
        x1, y1, x2, y2 = rotate_rect(x1, y1, x2, y2, rotation)
        suffix = "_r%d" % rotation

    return OrderedDict([
        ("uv", [x1, y1]),
        ("uv_size", [x2 - x1, y2 - y1]),
        ("material_instance", slot_of(name, suffix)),
    ])


def convert(model, slot_of):
    """A Java block model -> a Bedrock bone full of cubes."""
    cubes = []
    for element in model["elements"]:
        start, end = element["from"], element["to"]
        faces = OrderedDict()
        for face, spec in element["faces"].items():
            faces[face] = face_uv(spec, slot_of, face)
        cubes.append(OrderedDict([
            # Bedrock centres a block on the X/Z origin; Java corners it.
            ("origin", [start[0] - 8, start[1], start[2] - 8]),
            ("size", [end[0] - start[0], end[1] - start[1], end[2] - start[2]]),
            ("uv", faces),
        ]))
    return cubes


def geometry(source):
    """Every model Create draws the drive with, as one geometry file."""
    used = {}

    def slot_of(reference, suffix):
        """Java texture ref -> material instance name, remembering which we need."""
        texture = model_textures[reference].split("/")[-1]
        slot = TEXTURE_SLOTS[texture] + suffix.replace("_r", "")   # side, side90, ...
        used[slot] = texture + suffix
        return slot

    geometries = []
    for name in MODELS:
        model = load(os.path.join(source, "models/block/encased_chain_drive", name + ".json"))
        model_textures = model["textures"]
        geometries.append(OrderedDict([
            ("description", OrderedDict([
                ("identifier", "geometry.morecreate.chain_drive_" + name),
                ("texture_width", 16), ("texture_height", 16),
                ("visible_bounds_width", 2), ("visible_bounds_height", 2),
                ("visible_bounds_offset", [0, 1, 0]),
            ])),
            ("bones", [OrderedDict([
                ("name", "drive"), ("pivot", [0, 8, 0]),
                ("cubes", convert(model, slot_of)),
            ])]),
        ]))
    return OrderedDict([
        ("format_version", "1.16.0"),
        ("minecraft:geometry", geometries),
    ]), used


# -------------------------------------------------------------------- block

def materials(used):
    """One material instance per texture-and-turn the geometry asks for."""
    def instance(texture):
        return OrderedDict([
            ("texture", "morecreate:" + texture),
            ("render_method", "opaque"),
            ("ambient_occlusion", True),
        ])

    # `*` is the fallback Bedrock uses for any face that names nothing.
    instances = OrderedDict([("*", instance("encased_chain_drive"))])
    for slot, texture in sorted(used.items()):
        instances[slot] = instance(texture)
    return instances


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


def placements():
    """Create's blockstate, as (axis, along, part) -> (model, x, y) rotations.

    Copied straight from `blockstates/encased_chain_drive.json` so the two ends
    of a run are turned exactly the way Create turns them.
    """
    return {
        ("x", False, "end"): ("end_horizontal", 0, 0),
        ("x", False, "middle"): ("middle_horizontal", 0, 0),
        ("x", False, "none"): ("single", 0, 90),
        ("x", False, "start"): ("end_horizontal", 180, 0),
        ("x", True, "end"): ("end_horizontal", 90, 0),
        ("x", True, "middle"): ("middle_horizontal", 90, 0),
        ("x", True, "none"): ("single", 0, 90),
        ("x", True, "start"): ("end_horizontal", 270, 0),
        ("y", False, "end"): ("end_vertical", 0, 180),
        ("y", False, "middle"): ("middle_vertical", 0, 0),
        ("y", False, "none"): ("single", 90, 0),
        ("y", False, "start"): ("end_vertical", 0, 0),
        ("y", True, "end"): ("end_vertical", 0, 90),
        ("y", True, "middle"): ("middle_vertical", 0, 90),
        ("y", True, "none"): ("single", 90, 0),
        ("y", True, "start"): ("end_vertical", 0, 270),
        ("z", False, "end"): ("end_horizontal", 90, 90),
        ("z", False, "middle"): ("middle_horizontal", 90, 90),
        ("z", False, "none"): ("single", 0, 0),
        ("z", False, "start"): ("end_horizontal", 270, 90),
        ("z", True, "end"): ("end_horizontal", 0, 270),
        ("z", True, "middle"): ("middle_horizontal", 0, 90),
        ("z", True, "none"): ("single", 0, 0),
        ("z", True, "start"): ("end_horizontal", 0, 90),
    }


def condition(axis, along, part):
    facings = " || ".join("q.block_state('minecraft:facing_direction') == '%s'" % face
                          for face in AXIS_FACINGS[axis])
    return ("(%s) && q.block_state('morecreate:along') == %s && "
            "q.block_state('morecreate:part') == '%s'"
            % (facings, "true" if along else "false", part))


def block(used):
    permutations = []
    for (axis, along, part), (model, turn_x, turn_y) in sorted(placements().items()):
        # `minecraft:transformation` turns the opposite way about Y to Java's
        # blockstate. Left as-is it swapped the two ends of every horizontal
        # run - and left the middle looking fine, because the middle texture is
        # symmetric, which is exactly what showed up in game.
        turn_y = (360 - turn_y) % 360
        components = OrderedDict([
            ("minecraft:geometry", OrderedDict([
                ("identifier", "geometry.morecreate.chain_drive_" + model),
            ])),
        ])
        if turn_x or turn_y:
            components["minecraft:transformation"] = {"rotation": [turn_x, turn_y, 0]}
        permutations.append(OrderedDict([
            ("condition", condition(axis, along, part)),
            ("components", components),
        ]))

    return OrderedDict([
        ("format_version", "1.26.10"),
        ("minecraft:block", OrderedDict([
            ("description", OrderedDict([
                ("identifier", "morecreate:encased_chain_drive"),
                ("menu_category", {"category": "items"}),
                ("states", OrderedDict([
                    ("morecreate:along", [False, True]),
                    ("morecreate:part", PARTS),
                ])),
                ("traits", {"minecraft:placement_direction": {
                    "enabled_states": ["minecraft:facing_direction"]}}),
            ])),
            ("components", OrderedDict([
                ("create:rpm_system", {}),
                ("minecraft:map_color", "#8B6C4D"),
                ("minecraft:geometry", OrderedDict([
                    ("identifier", "geometry.morecreate.chain_drive_single"),
                ])),
                ("minecraft:material_instances", materials(used)),
                # A plain cube in the inventory showed no shaft at all, so the
                # item borrows Create's own item model, which has it.
                ("minecraft:item_visual", OrderedDict([
                    ("geometry", {"identifier": "geometry.morecreate.chain_drive_item"}),
                    ("material_instances", materials(used)),
                ])),
                ("minecraft:redstone_conductivity", {"redstone_conductor": True}),
                ("minecraft:destruction_particles", {"texture": "morecreate:encased_chain_drive"}),
                ("minecraft:destructible_by_mining", destructible()),
            ])),
            ("permutations", permutations),
        ])),
    ])


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4)
        handle.write("\n")


def main():
    source = sys.argv[1]
    written = bake_textures(source)
    geo, used = geometry(source)
    write(GEO_OUT, geo)
    write(BLOCK_OUT, block(used))

    print("chain drive, ported from Create's own models")
    print("  textures: %d (%s)" % (len(written), ", ".join(sorted(set(
        name.split(".")[0] for name in written))[:4]) + ", ..."))
    print("  geometries: %s" % ", ".join(MODELS))
    print("  material instances: %s" % ", ".join(sorted(used)))
    print("  permutations: %d" % len(placements()))


if __name__ == "__main__":
    main()
