#!/usr/bin/env python3
"""Build the in-game recipe browser: a JEI-style panel on the pause menu.

Bedrock has no recipe book for script-driven machines, and JSON UI cannot call
a script, so the browser is generated as static JSON UI - every recipe in the
game becomes a row of item slots laid out ahead of time. That is the same trick
Create's own pack uses for its pause-menu guide, except Create hand-draws one
image per recipe and this builds each row out of the real item textures.

Two files come out of here:

    ui/morecreate/browser.json      every control, in its own namespace
    ui/morecreate/pause_patch.json  the circular button on the pause menu

The patch declares `"namespace": "pause"` and is registered through
`ui/_ui_defs.json` rather than shipping a `ui/pause_screen.json`. That matters:
Create's pack owns `ui/pause_screen.json` and puts its entire guide in it, so a
file of ours at that path could hide theirs. Patching the namespace from our own
path cannot: worst case our button does not appear and Create is untouched.

Usage: gen_browser_ui.py <Create RP dir> <Create BP dir> [vanilla json dir]

The vanilla atlas references default to `tools/data/vanilla`, which is checked
in, so only the two Create pack directories are normally needed.
"""

import json
import math
import os
import re
import subprocess
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icons  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI_DIR = os.path.join(ROOT, "packs/resource/ui")
BROWSER_OUT = os.path.join(UI_DIR, "morecreate/browser.json")
PATCH_OUT = os.path.join(UI_DIR, "morecreate/pause_patch.json")
DEFS_OUT = os.path.join(UI_DIR, "_ui_defs.json")
BOOK = os.path.join(ROOT, "packs/behavior/scripts/morecreate/book/recipes_data.js")

NS = "morecreate_browser"
TEX = "textures/morecreate/ui"

ROWS_PER_PAGE = 40
MAX_INPUTS = 3
MAX_OUTPUTS = 5

ROW_HEIGHT = 28
SLOT_PITCH = 20
ARROW_X = 2 + MAX_INPUTS * SLOT_PITCH + 4      # just past the last input slot
OUTPUT_X = ARROW_X + 22

GOLD = [0.96, 0.78, 0.42]
CREAM = [0.90, 0.87, 0.80]
MUTED = [0.66, 0.62, 0.56]
GREEN = [0.62, 0.85, 0.55]

# Fan recipes and spout recipes name a fluid rather than an item.
FLUIDS = {
    "water": "textures/items/bucket_water",
    "lava": "textures/items/bucket_lava",
    "milk": "textures/items/bucket_milk",
    "honey": "textures/create/common/items/honey_bucket",
    "chocolate": "textures/create/common/items/chocolate_bucket",
}

# Machine key -> the icon on its tab. The four fan recipe types share one
# machine, so each takes the icon of what the fan has to blow through - that
# reads far better on a 22px tab than four identical Encased Fans.
MACHINE_ICONS = {
    "crushing": "textures/ui/crafters/misc/crush_ui",
    "milling": "textures/ui/crafters/misc/millstone_ui",
    "washing": "textures/items/bucket_water",
    "smelting": "textures/items/bucket_lava",
    "smoking": "textures/blocks/campfire",
    "haunting": "textures/blocks/soul_campfire",
    "pressing": "textures/ui/crafters/misc/press_ui",
    "mixing": "textures/ui/crafters/misc/mixer_ui",
    "spouting": "textures/ui/crafters/misc/spout_ui",
}


# ---------------------------------------------------------------- recipe data

def load_recipes():
    """Pull MACHINES/RECIPES straight out of the pack's own data module."""
    script = (
        "import(%s).then(m => process.stdout.write(JSON.stringify("
        "{machines: m.MACHINES, recipes: m.RECIPES, total: m.TOTAL, "
        "note: m.STONECUTTING_NOTE})))" % json.dumps("file://" + BOOK)
    )
    out = subprocess.run(["node", "-e", script], capture_output=True, check=True)
    return json.loads(out.stdout.decode())


def pretty(identifier):
    name = identifier.split(":")[-1]
    return name.replace("_", " ").title()


def parse_input(raw):
    """Split a book input into (item, count) pairs, fluids, and a note.

    Mixing and spouting inputs are written as human-readable strings such as
    `minecraft:copper_ingot x1 + create:zinc_ingot x1 (needs heat)`, because
    that is what the text book shows. The browser wants slots, so take the
    string apart again.
    """
    note = ""
    match = re.search(r"\(([^)]*)\)\s*$", raw)
    if match:
        note = match.group(1)
        raw = raw[:match.start()].strip()

    items, fluids = [], []
    for chunk in raw.split(" + "):
        chunk = chunk.strip()
        found = re.match(r"^([a-z0-9_.]+:[a-z0-9_.]+)(?:\s*x(\d+))?$", chunk)
        if found:
            items.append((found.group(1), int(found.group(2) or 1)))
        elif chunk in FLUIDS:
            fluids.append(chunk)
        elif chunk:
            note = (note + ", " + chunk).strip(", ") if note else chunk
    return items, fluids, note


def describe(inputs, fluids, note, outputs):
    """The plain-language line under each row's slots."""
    left = ", ".join(
        pretty(item) + (" x%d" % count if count > 1 else "") for item, count in inputs)
    if fluids:
        left = (left + " + " if left else "") + ", ".join(f.title() for f in fluids)
    right = []
    for item, count, chance in outputs:
        label = pretty(item)
        if count > 1:
            label += " x%d" % count
        if chance is not None:
            label += " %d%%" % round(chance * 100)
        right.append(label)
    line = "%s  ->  %s" % (left or "?", ", ".join(right) or "nothing")
    if note:
        line += "  (%s)" % note
    return line


def normalise(rows):
    """Book rows -> (inputs, fluids, note, outputs) with counts and chances."""
    out = []
    for raw_input, raw_outputs in rows:
        inputs, fluids, note = parse_input(raw_input)
        outputs = []
        for entry in raw_outputs:
            item = entry[0]
            count = entry[1] if len(entry) > 1 else 1
            chance = entry[2] if len(entry) > 2 else None
            outputs.append((item, count, chance))
        out.append((inputs, fluids, note, outputs))
    return out


# ------------------------------------------------------------------ ui pieces

def label(text, colour, offset, size=None, small=True, layer=3):
    control = OrderedDict([
        ("type", "label"),
        ("text", text),
        ("color", colour),
        ("layer", layer),
        ("anchor_from", "top_left"),
        ("anchor_to", "top_left"),
        ("offset", offset),
    ])
    if small:
        control["font_size"] = "small"
    if size:
        control["size"] = size
    return control


def slot(icon, offset, badge=""):
    instance = OrderedDict([
        ("$icon", icon),
        ("anchor_from", "top_left"),
        ("anchor_to", "top_left"),
        ("offset", offset),
    ])
    if badge:
        instance["$badge"] = badge
    return instance


def badge_for(count, chance):
    if count > 1 and chance is not None:
        return "%dx%d%%" % (count, round(chance * 100))
    if count > 1:
        return "%d" % count
    if chance is not None:
        return "%d%%" % round(chance * 100)
    return ""


def build_row(index, recipe, index_icon):
    """One recipe: input slots, an arrow, output slots, and a caption."""
    inputs, fluids, note, outputs = recipe
    controls = []

    if index % 2 == 1:
        controls.append({"stripe": OrderedDict([
            ("type", "image"), ("texture", "textures/ui/Black"),
            ("size", ["100%", "100%"]), ("alpha", 0.18), ("layer", 0),
        ])})

    slots = [(item, count, None) for item, count in inputs]
    slots += [("fluid:" + fluid, 1, None) for fluid in fluids]
    hidden_inputs = max(0, len(slots) - MAX_INPUTS)
    for position, (item, count, _chance) in enumerate(slots[:MAX_INPUTS]):
        icon = FLUIDS[item.split(":", 1)[1]] if item.startswith("fluid:") \
            else index_icon(item)
        controls.append({"i%d@%s.slot" % (position, NS):
                         slot(icon, [2 + position * SLOT_PITCH, 1],
                              badge_for(count, None))})

    controls.append({"arrow": OrderedDict([
        ("type", "image"),
        ("texture", TEX + "/browser_arrow"),
        ("size", [18, 12]),
        ("layer", 2),
        ("anchor_from", "top_left"),
        ("anchor_to", "top_left"),
        ("offset", [ARROW_X, 4]),
    ])})

    hidden_outputs = max(0, len(outputs) - MAX_OUTPUTS)
    for position, (item, count, chance) in enumerate(outputs[:MAX_OUTPUTS]):
        controls.append({"o%d@%s.slot" % (position, NS):
                         slot(index_icon(item),
                              [OUTPUT_X + position * SLOT_PITCH, 1],
                              badge_for(count, chance))})

    caption = describe(inputs, fluids, note, outputs)
    if hidden_inputs or hidden_outputs:
        caption += "  (+%d more)" % (hidden_inputs + hidden_outputs)
    controls.append({"cap": label(caption, MUTED, [3, 19], ["100% - 6px", 9])})

    return OrderedDict([
        ("type", "panel"),
        ("size", ["100%", ROW_HEIGHT]),
        ("controls", controls),
    ])


def build(data, index):
    """Every control in the browser's namespace."""
    resolve = index.resolve_or_fallback
    ui = OrderedDict([("namespace", NS)])

    # -- shared pieces -----------------------------------------------------
    ui["slot"] = OrderedDict([
        ("type", "image"),
        ("texture", TEX + "/browser_slot"),
        ("size", [18, 18]),
        ("layer", 2),
        ("$badge|default", ""),
        ("controls", [
            {"icon": OrderedDict([
                ("type", "image"), ("texture", "$icon"), ("size", [16, 16]),
                ("layer", 3), ("anchor_from", "center"), ("anchor_to", "center"),
            ])},
            {"badge": OrderedDict([
                ("type", "label"), ("text", "$badge"), ("font_size", "small"),
                ("color", CREAM), ("shadow", True), ("layer", 5),
                ("anchor_from", "bottom_right"), ("anchor_to", "bottom_right"),
                ("offset", [0, 2]),
            ])},
        ]),
    ])

    # `$tab_icon` is instantiated inside the tab body, which is how the icon
    # variable set on a tab button reaches the image. Same shape Create uses.
    ui["icon_image"] = OrderedDict([
        ("type", "image"),
        ("layer", 1),
        ("size", "$size_icon"),
        ("$size_icon|default", [16, 16]),
    ])
    ui["tab_body"] = OrderedDict([
        ("type", "panel"),
        ("size", ["100% + 1.5px", "100%x + 1px"]),
        ("controls", [{"img@$tab_icon": {}}]),
    ])
    ui["machine_icon@%s.icon_image" % NS] = OrderedDict([
        ("texture", "$machine_texture"),
        ("$size_icon", [16, 16]),
    ])
    # The pause button draws its own art, so its tab icon is a clear pixel.
    ui["button_icon@%s.icon_image" % NS] = OrderedDict([
        ("texture", TEX + "/blank"),
        ("$size_icon", [1, 1]),
    ])
    ui["page_icon"] = OrderedDict([
        ("type", "label"),
        ("text", "$page_label"),
        ("color", CREAM),
        ("layer", 2),
        ("anchor_from", "center"),
        ("anchor_to", "center"),
    ])

    def toggle_images(base, selected):
        return OrderedDict([
            ("$unchecked_default_image", base),
            ("$unchecked_hover_image", selected),
            ("$unchecked_locked_image", base),
            ("$unchecked_locked_hover_image", base),
            ("$checked_default_image", selected),
            ("$checked_hover_image", selected),
            ("$checked_locked_image", selected),
            ("$checked_locked_hover_image", selected),
        ])

    ui["machine_tab@common_tabs.tab_top"] = OrderedDict([
        ("size", [24, 24]),
        ("layer", 5),
        ("$radio_toggle_group", True),
        ("$toggle_name", "morecreate_machine_tabs"),
        # Without a default the browser opens on an empty content area, which
        # reads as broken rather than as "pick a machine".
        ("$toggle_group_default_selected", 0),
        ("$toggle_focus_enabled", True),
        ("$allow_controller_back_button_mapping", "$is_ps4"),
        ("$tab_content", "%s.tab_body" % NS),
        ("$tab_icon", "%s.machine_icon" % NS),
        ("$toggle_group_forced_index", "$machine_index"),
        ("$tab_view_binding_name", "$machine_binding"),
    ] + list(toggle_images(TEX + "/browser_tab", TEX + "/browser_tab_selected").items()))

    ui["page_tab@common_tabs.tab_top"] = OrderedDict([
        ("size", [18, 14]),
        ("layer", 5),
        ("$radio_toggle_group", True),
        ("$toggle_group_default_selected", 0),
        ("$toggle_focus_enabled", True),
        ("$allow_controller_back_button_mapping", "$is_ps4"),
        ("$tab_content", "%s.tab_body" % NS),
        ("$tab_icon", "%s.page_icon" % NS),
        ("$toggle_group_forced_index", "$page_index"),
        ("$tab_view_binding_name", "$page_binding"),
    ] + list(toggle_images(TEX + "/browser_tab", TEX + "/browser_tab_selected").items()))

    # -- one content panel per machine ------------------------------------
    machine_tabs = []
    content_panels = []
    for order, machine in enumerate(data["machines"]):
        key = machine["key"]
        rows = normalise(data["recipes"].get(key, []))
        pages = max(1, math.ceil(len(rows) / ROWS_PER_PAGE))
        binding = "mc_layout_%s" % key

        machine_tabs.append({"tab_%s@%s.machine_tab" % (key, NS): OrderedDict([
            ("$machine_texture", MACHINE_ICONS[key]),
            ("$machine_binding", binding),
            ("$machine_index", order),
        ])})

        body_top = 24 if pages == 1 else 40
        controls = [
            {"head": label("%s  -  %d recipes" % (machine["title"], len(rows)),
                           GOLD, [2, 0], small=False)},
            {"sub": label(machine["subtitle"], MUTED, [2, 12], ["100%", 10])},
        ]

        if pages > 1:
            page_tabs = []
            for page in range(pages):
                first = page * ROWS_PER_PAGE + 1
                last = min((page + 1) * ROWS_PER_PAGE, len(rows))
                page_tabs.append({"p%d@%s.page_tab" % (page, NS): OrderedDict([
                    ("$page_label", "%d-%d" % (first, last)),
                    ("$page_binding", "mc_page_%s_%d" % (key, page)),
                    ("$page_index", page),
                    ("$toggle_name", "mc_pages_%s" % key),
                    ("size", [34, 14]),
                    ("offset", [page * 36, 0]),
                ])})
            controls.append({"pages": OrderedDict([
                ("type", "panel"),
                ("size", ["100%", 14]),
                ("anchor_from", "top_left"),
                ("anchor_to", "top_left"),
                ("offset", [2, 24]),
                ("controls", page_tabs),
            ])})

        for page in range(pages):
            slice_rows = rows[page * ROWS_PER_PAGE:(page + 1) * ROWS_PER_PAGE]
            list_name = "list_%s_%d" % (key, page)
            ui[list_name] = OrderedDict([
                ("type", "stack_panel"),
                ("orientation", "vertical"),
                ("size", ["100%", "100%c"]),
                ("controls", [
                    {"r%d" % number: build_row(number, recipe, resolve)}
                    for number, recipe in enumerate(slice_rows)
                ]),
            ])
            ui["scroll_%s_%d@common.scrolling_panel" % (key, page)] = OrderedDict([
                ("size", ["100%", "100%"]),
                ("$show_background", False),
                ("$scrolling_content", "%s.%s" % (NS, list_name)),
            ])

            page_panel = OrderedDict([
                ("type", "panel"),
                ("size", ["100%", "100%% - %dpx" % body_top]),
                ("anchor_from", "top_left"),
                ("anchor_to", "top_left"),
                ("offset", [0, body_top]),
                ("controls", [{"s@%s.scroll_%s_%d" % (NS, key, page): {}}]),
            ])
            if pages > 1:
                page_panel["bindings"] = [OrderedDict([
                    ("binding_type", "view"),
                    ("source_control_name", "mc_page_%s_%d" % (key, page)),
                    ("source_property_name", "#toggle_state"),
                    ("target_property_name", "#visible"),
                ])]
            controls.append({"body%d" % page: page_panel})

        content_panels.append({"content_%s" % key: OrderedDict([
            ("type", "panel"),
            ("size", ["100%", "100%"]),
            ("bindings", [OrderedDict([
                ("binding_type", "view"),
                ("source_control_name", binding),
                ("source_property_name", "#toggle_state"),
                ("target_property_name", "#visible"),
            ])]),
            ("controls", controls),
        ])})

    # -- window ------------------------------------------------------------
    ui["window"] = OrderedDict([
        ("type", "panel"),
        ("size", ["94%", "84%"]),
        ("anchor_from", "center"),
        ("anchor_to", "center"),
        # Nudged down so the top row of pause-menu buttons - including the one
        # that opens this - stays clear of the window's title bar.
        ("offset", [0, 14]),
        ("controls", [
            {"bg": OrderedDict([
                ("type", "image"), ("texture", TEX + "/browser_bg"),
                ("size", ["100%", "100%"]), ("layer", 1),
            ])},
            {"title": label("More Create  -  Recipe Browser", GOLD, [10, 6],
                            small=False, layer=4)},
            {"total": OrderedDict([
                ("type", "label"),
                ("text", "%d recipes  -  press the button again to close"
                         % data["total"]),
                ("color", MUTED), ("font_size", "small"), ("layer", 4),
                ("anchor_from", "top_right"), ("anchor_to", "top_right"),
                ("offset", [-10, 8]),
                ("size", ["60%", 10]),
                ("text_alignment", "right"),
            ])},
            # The machine tabs run across the top rather than down the side:
            # nine 24px tabs stacked vertically need 216px of height, which a
            # phone-sized UI does not have, while every screen is wide enough
            # for them in a row.
            {"tabs": OrderedDict([
                ("type", "stack_panel"),
                ("orientation", "horizontal"),
                ("size", ["100%c", 24]),
                ("anchor_from", "top_left"),
                ("anchor_to", "top_left"),
                ("offset", [8, 20]),
                ("layer", 4),
                ("controls", machine_tabs),
            ])},
            {"content": OrderedDict([
                ("type", "panel"),
                ("size", ["100% - 16px", "100% - 58px"]),
                ("anchor_from", "top_left"),
                ("anchor_to", "top_left"),
                ("offset", [8, 48]),
                ("layer", 3),
                ("controls", content_panels),
            ])},
            {"note": OrderedDict([
                ("type", "label"),
                ("text", data["note"] or ""),
                ("color", MUTED), ("font_size", "small"), ("layer", 4),
                ("anchor_from", "bottom_left"), ("anchor_to", "bottom_left"),
                ("offset", [10, -6]),
                ("size", ["100% - 20px", 10]),
            ])},
        ]),
    ])

    # The pause button names this view binding; the root panel follows it, so
    # pressing the button once opens the browser and again closes it.
    ui["root"] = OrderedDict([
        ("type", "input_panel"),
        ("size", ["100%", "100%"]),
        ("layer", 31),
        ("bindings", [OrderedDict([
            ("binding_type", "view"),
            ("source_control_name", "morecreate_browser_layout"),
            ("source_property_name", "#toggle_state"),
            ("target_property_name", "#visible"),
        ])]),
        ("controls", [
            {"dim": OrderedDict([
                ("type", "image"), ("texture", "textures/ui/Black"),
                ("size", ["100%", "100%"]), ("alpha", 0.7), ("layer", 1),
            ])},
            {"win@%s.window" % NS: {"layer": 2}},
        ]),
    ])
    return ui


def build_patch():
    """The circular pack-icon button, inserted into the pause menu."""
    def images(state):
        return "%s/browser_button%s" % (TEX, state)

    return OrderedDict([
        ("namespace", "pause"),
        ("morecreate_browser_button@common_tabs.tab_top", OrderedDict([
            ("size", [25, 25]),
            ("anchor_from", "top_left"),
            ("anchor_to", "top_left"),
            # Create's own guide button sits at [5, 5]; this one goes beside it.
            ("offset", [35, 5]),
            ("layer", 41),
            ("$toggle_name", "morecreate_browser_toggle"),
            ("$toggle_focus_enabled", True),
            ("$allow_controller_back_button_mapping", "$is_ps4"),
            ("$tab_content", "%s.tab_body" % NS),
            ("$tab_icon", "%s.button_icon" % NS),
            ("$tab_view_binding_name", "morecreate_browser_layout"),
            ("$unchecked_default_image", images("")),
            ("$unchecked_hover_image", images("_hover")),
            ("$unchecked_locked_image", images("")),
            ("$unchecked_locked_hover_image", images("")),
            ("$checked_default_image", images("_pressed")),
            ("$checked_hover_image", images("_pressed")),
            ("$checked_locked_image", images("_pressed")),
            ("$checked_locked_hover_image", images("_pressed")),
        ])),
        ("pause_screen_content", {
            "modifications": [{
                "array_name": "controls",
                "operation": "insert_front",
                "value": [
                    {"morecreate_browser_tab@pause.morecreate_browser_button": {
                        "layer": 41}},
                    {"morecreate_browser_root@%s.root" % NS: {"layer": 31}},
                ],
            }],
        }),
    ])


def write(path, data, compact=False):
    """The browser file is written compactly - it is machine-made and large,
    and every byte of indentation is a byte the game has to parse at load."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        if compact:
            json.dump(data, handle, separators=(",", ":"))
        else:
            json.dump(data, handle, indent=4)
        handle.write("\n")
    return os.path.getsize(path)


def register():
    """Add the two files to `_ui_defs.json`, keeping what is already there."""
    defs = icons.load_json(DEFS_OUT) if os.path.exists(DEFS_OUT) else {"ui_defs": []}
    wanted = ["ui/morecreate/browser.json", "ui/morecreate/pause_patch.json"]
    listed = [entry for entry in defs.get("ui_defs", []) if entry not in wanted]
    defs["ui_defs"] = listed + wanted
    write(DEFS_OUT, defs)
    return defs["ui_defs"]


def main():
    if len(sys.argv) < 3:
        print(__doc__.strip().splitlines()[-3], file=sys.stderr)
        return 2
    create_rp, create_bp = sys.argv[1:3]
    vanilla = sys.argv[3] if len(sys.argv) > 3 \
        else os.path.join(ROOT, "tools/data/vanilla")
    index = icons.build(create_rp, create_bp, vanilla,
                        extra_packs=[(os.path.join(ROOT, "packs/resource"),
                                      os.path.join(ROOT, "packs/behavior"))])
    data = load_recipes()

    missing = set()
    counted = [0, 0]
    for key, rows in data["recipes"].items():
        for inputs, fluids, _note, outputs in normalise(rows):
            counted[0] = max(counted[0], len(inputs) + len(fluids))
            counted[1] = max(counted[1], len(outputs))
            for item, _count in inputs:
                if index.resolve(item) is None:
                    missing.add(item)
            for item, _count, _chance in outputs:
                if index.resolve(item) is None:
                    missing.add(item)

    browser_size = write(BROWSER_OUT, build(data, index), compact=True)
    patch_size = write(PATCH_OUT, build_patch())
    listed = register()

    print("recipe browser")
    print("  %-42s %6.1f KB" % (os.path.relpath(BROWSER_OUT, ROOT), browser_size / 1024))
    print("  %-42s %6.1f KB" % (os.path.relpath(PATCH_OUT, ROOT), patch_size / 1024))
    print("  machines %d, recipes %d, widest row %d in / %d out"
          % (len(data["machines"]), data["total"], counted[0], counted[1]))
    print("  slots shown per row: %d in / %d out" % (MAX_INPUTS, MAX_OUTPUTS))
    print("  ui_defs: %s" % ", ".join(listed))
    if missing:
        print("  WARNING unresolved icons: %s" % ", ".join(sorted(missing)))
    else:
        print("  every item icon resolved")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
