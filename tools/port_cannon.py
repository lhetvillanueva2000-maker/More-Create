#!/usr/bin/env python3
"""Port the Create Cannon / Schematic addon into More Create.

The original ships as its own behaviour + resource pack under the `cannon_rp`
namespace, with un-namespaced texture keys and generic geometry names that
would collide with other packs. This moves every asset into More Create,
renames it under `morecreate`, and relocates textures out of the vanilla
`textures/items` and `textures/blocks` folders.

Scripts are ported separately - they need Portuguese/Spanish text translated and
the `@minecraft/server-ui` 1.x form calls updated for 2.x.

Usage: port_cannon.py <extracted cannon addon dir>
"""

import json
import os
import re
import shutil
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "packs/behavior")
RP = os.path.join(ROOT, "packs/resource")

# Longest first so `geometry.cannon_item_block` is not eaten by `geometry.cannon`.
TEXT_RENAMES = [
    ("geometry.cannon_item_block", "geometry.morecreate.cannon_item_block"),
    ("geometry.schematic_cube_3d", "geometry.morecreate.schematic_cube"),
    ("geometry.schematic_table", "geometry.morecreate.schematic_table"),
    ("geometry.cannon", "geometry.morecreate.cannon"),
    ("geometry.base", "geometry.morecreate.cannon_base"),
    ("create:create_canon", "morecreate:cannon_entity"),
    ("cannon_rp:projectile_mob", "morecreate:cannon_projectile"),
    ("cannon_rp:", "morecreate:"),
    ("loot_tables/blocks/cannon_drop.json", "loot_tables/morecreate/cannon_drop.json"),
    ("textures/items/", "textures/morecreate/items/"),
    ("textures/blocks/base", "textures/morecreate/blocks/cannon_base"),
    ("textures/blocks/", "textures/morecreate/blocks/"),
    ("textures/particle/schematic_box", "textures/morecreate/particle/schematic_box"),
    ("textures/particle/schematic_cube", "textures/morecreate/particle/schematic_cube"),
    ("textures/ui/custom/", "textures/morecreate/ui/"),
]

# Bare atlas keys -> namespaced ones. Applied only where a texture key is
# actually expected, so ordinary words in prose are never touched.
ITEM_TEXTURE_KEYS = [
    "clipboard_and_quill", "clipboard_button", "empty_clipboard", "clipboard",
    "start_button", "reset_button", "stop_button", "confirm_button",
    "configures_button", "schematic_and_quill", "empty_schematic", "schematic",
    "cannon_guide", "cannon",
]
TERRAIN_TEXTURE_KEYS = ["cannon_block", "schematic_table", "base"]

# The two item-atlas entries in the original point at files that do not exist.
ITEM_TEXTURE_FILE_FIXES = {
    "cannon": "cannon_imagem",
    "schematic_table": "schematic_table_imagem",
}


def rename_text(text):
    for old, new in TEXT_RENAMES:
        text = text.replace(old, new)
    return text


def read(path):
    with open(path, encoding="utf-8-sig") as handle:
        return handle.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def load_json(path):
    return json.loads(read(path), object_pairs_hook=OrderedDict)


def dump_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4)
        handle.write("\n")


def namespace_texture_refs(text):
    """Namespace atlas keys in `"texture": "x"` and `"minecraft:icon": "x"`."""
    def repl(match):
        prefix, key = match.group(1), match.group(2)
        if key in ITEM_TEXTURE_KEYS or key in TERRAIN_TEXTURE_KEYS:
            mapped = {"base": "cannon_base"}.get(key, key)
            return '%s"morecreate:%s"' % (prefix, mapped)
        return match.group(0)

    text = re.sub(r'("texture"\s*:\s*)"([a-z_0-9]+)"', repl, text)
    text = re.sub(r'("minecraft:icon"\s*:\s*)"([a-z_0-9]+)"', repl, text)
    return text


def port_json_tree(src_dir, dst_dir, texture_refs=True):
    moved = []
    if not os.path.isdir(src_dir):
        return moved
    for root, _, files in os.walk(src_dir):
        for name in sorted(files):
            if not name.endswith(".json"):
                continue
            src = os.path.join(root, name)
            text = rename_text(read(src))
            if texture_refs:
                text = namespace_texture_refs(text)
            rel = os.path.relpath(src, src_dir)
            dst = os.path.join(dst_dir, rel)
            write(dst, text)
            moved.append(rel)
    return moved


def copy_textures(src_root, mapping):
    copied = []
    for rel_src, rel_dst in mapping.items():
        src = os.path.join(src_root, rel_src)
        if not os.path.isfile(src):
            continue
        dst = os.path.join(RP, rel_dst)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel_dst)
    return copied


def main():
    source = sys.argv[1]
    bp_src = os.path.join(source, "CreateCannB")
    rp_src = os.path.join(source, "Createcann")

    report = OrderedDict()

    # ---------------- behaviour pack ----------------
    report["blocks"] = port_json_tree(os.path.join(bp_src, "blocks"),
                                      os.path.join(BP, "blocks/morecreate/cannon"))
    report["items"] = port_json_tree(os.path.join(bp_src, "items"),
                                     os.path.join(BP, "items/morecreate"))
    report["entities"] = port_json_tree(os.path.join(bp_src, "entities"),
                                        os.path.join(BP, "entities/morecreate"))
    report["recipes"] = port_json_tree(os.path.join(bp_src, "recipes"),
                                       os.path.join(BP, "recipes/morecreate/cannon"))

    loot_src = os.path.join(bp_src, "loot_tables/blocks/cannon_drop.json")
    if os.path.isfile(loot_src):
        write(os.path.join(BP, "loot_tables/morecreate/cannon_drop.json"),
              rename_text(read(loot_src)))
        report["loot"] = ["cannon_drop.json"]

    # ---------------- resource pack ----------------
    rp_entity_src = os.path.join(rp_src, "entity/create_canon.json")
    if os.path.isfile(rp_entity_src):
        text = namespace_texture_refs(rename_text(read(rp_entity_src)))
        write(os.path.join(RP, "entity/morecreate/cannon_entity.rpe.json"), text)
        report["client_entity"] = ["cannon_entity.rpe.json"]

    report["models"] = port_json_tree(os.path.join(rp_src, "models"),
                                      os.path.join(RP, "models"))
    report["particles"] = port_json_tree(os.path.join(rp_src, "particles"),
                                         os.path.join(RP, "particles/morecreate"))

    # UI: `criative_inventory.json` is dead - nothing references it and it
    # extends a `ryQC_main` namespace that does not exist in this addon.
    for name in ("custom_chest_ui.json", "chest_screen.json"):
        src = os.path.join(rp_src, "ui", name)
        if os.path.isfile(src):
            write(os.path.join(RP, "ui", name), rename_text(read(src)))
    report["ui"] = ["custom_chest_ui.json", "chest_screen.json"]
    report["ui_dropped"] = ["criative_inventory.json (orphaned, references a missing pack)"]

    # ---------------- textures ----------------
    texture_map = {}
    items_dir = os.path.join(rp_src, "textures/items")
    if os.path.isdir(items_dir):
        for name in sorted(os.listdir(items_dir)):
            if name.endswith(".png"):
                texture_map["textures/items/" + name] = "textures/morecreate/items/" + name
    blocks_dir = os.path.join(rp_src, "textures/blocks")
    if os.path.isdir(blocks_dir):
        for name in sorted(os.listdir(blocks_dir)):
            if not name.endswith(".png"):
                continue
            out = "cannon_base.png" if name == "base.png" else name
            texture_map["textures/blocks/" + name] = "textures/morecreate/blocks/" + out
    for name in ("schematic_box.png", "schematic_cube.png"):
        texture_map["textures/particle/" + name] = "textures/morecreate/particle/" + name
    for name in ("background.png", "nada.png"):
        texture_map["textures/ui/custom/" + name] = "textures/morecreate/ui/" + name
    report["textures"] = copy_textures(rp_src, texture_map)

    # ---------------- atlases ----------------
    item_atlas = OrderedDict([
        ("resource_pack_name", "morecreate"),
        ("texture_name", "atlas.items"),
        ("texture_data", OrderedDict()),
    ])
    src_items = load_json(os.path.join(rp_src, "textures/item_texture.json"))
    for key, value in src_items["texture_data"].items():
        file_stem = ITEM_TEXTURE_FILE_FIXES.get(key, key)
        item_atlas["texture_data"]["morecreate:" + key] = {
            "textures": "textures/morecreate/items/" + file_stem
        }
    dump_json(os.path.join(RP, "textures/item_texture.json"), item_atlas)
    report["item_atlas_fixes"] = ["%s -> %s.png" % (k, v) for k, v in ITEM_TEXTURE_FILE_FIXES.items()]

    terrain_path = os.path.join(RP, "textures/terrain_texture.json")
    terrain = load_json(terrain_path)
    src_terrain = load_json(os.path.join(rp_src, "textures/terrain_texture.json"))
    for key, value in src_terrain["texture_data"].items():
        stem = "cannon_base" if key == "base" else key
        terrain["texture_data"]["morecreate:" + stem] = {
            "textures": "textures/morecreate/blocks/" + stem
        }
    dump_json(terrain_path, terrain)

    dump_json(os.path.join(RP, "textures/particle/particles.json"), OrderedDict([
        ("texture_name", "atlas.particles"),
        ("texture_data", {
            "textures/morecreate/particle/schematic_box": {
                "textures": "textures/morecreate/particle/schematic_box"
            }
        }),
    ]))

    dump_json(os.path.join(RP, "ui/_ui_defs.json"), {
        "ui_defs": ["ui/custom_chest_ui.json", "ui/chest_screen.json"]
    })

    # ---------------- report ----------------
    for section, entries in report.items():
        print("%s: %d" % (section, len(entries)))
        for entry in entries:
            print("    " + entry)


if __name__ == "__main__":
    main()
