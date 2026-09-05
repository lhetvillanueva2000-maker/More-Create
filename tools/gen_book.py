#!/usr/bin/env python3
"""Build the Recipe Book's data file.

Merges the recipe tables built into the Create Bedrock addon with the ones More
Create registers, so the book lists every processing recipe in the game rather
than only the additions. Entries are kept compact - `[input, [[item, count,
chance], ...]]` - because the whole table is bundled into the behaviour pack.

Usage: gen_book.py tools/data/be_recipes.json tools/data/gap_report.json
"""

import json
import os
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "packs/behavior/scripts/morecreate/book/recipes_data.js")

# machine key -> (book title, subtitle shown above the list)
MACHINES = OrderedDict([
    ("crushing", ("Crushing Wheels", "Two wheels facing each other, powered in opposite directions.")),
    ("milling", ("Millstone", "Drop items in from above. Slower than wheels, but one block.")),
    ("washing", ("Bulk Washing", "Encased Fan blowing through a water source onto the items.")),
    ("smelting", ("Bulk Smelting", "Encased Fan blowing through lava onto the items.")),
    ("smoking", ("Bulk Smoking", "Encased Fan blowing through fire or a campfire.")),
    ("haunting", ("Bulk Haunting", "Encased Fan blowing through soul fire.")),
    ("pressing", ("Mechanical Press", "Press over a depot or belt.")),
    ("mixing", ("Mechanical Mixer", "Mixer over a basin. Some recipes need a Blaze Burner.")),
    ("spouting", ("Spout", "Spout over a depot, filling the item with a fluid.")),
])


def normalise_outputs(rows):
    out = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        item = row.get("item") or row.get("id")
        if not item:
            continue
        entry = [item, int(row.get("count", 1))]
        chance = float(row.get("chance", 1))
        if chance < 1:
            entry.append(round(chance, 4))
        out.append(entry)
    return out


def from_map(table, key="output"):
    """Create's crushing/milling style tables: id -> {output: [...]}"""
    rows = []
    for item_id, recipe in (table or {}).items():
        outputs = recipe.get(key) if isinstance(recipe, dict) else recipe
        outputs = normalise_outputs(outputs)
        if outputs:
            rows.append([item_id, outputs])
    return rows


def main():
    be = json.load(open(sys.argv[1], encoding="utf-8"))
    gap = json.load(open(sys.argv[2], encoding="utf-8"))
    # Spout and Mechanical Crafter tables were extracted separately.
    be2 = json.load(open(sys.argv[3], encoding="utf-8")) if len(sys.argv) > 3 else {}

    data = OrderedDict((key, []) for key in MACHINES)

    # ---- Create's own tables ------------------------------------------
    data["crushing"] += from_map(be.get("CRUSHING_RECIPES"))
    data["milling"] += from_map(be.get("millstoneRecipes"))
    data["washing"] += from_map(be.get("SPLASHING_RECIPES"))
    data["smelting"] += from_map(be.get("BLASTING_RECIPES"))
    data["smoking"] += from_map(be.get("SMOKING_RECIPES"))
    data["haunting"] += from_map(be.get("HAUNTING_RECIPES"))
    for recipe in be.get("PRESS_RECIPES") or []:
        if isinstance(recipe, dict) and recipe.get("input") and recipe.get("result"):
            data["pressing"].append([recipe["input"], [[recipe["result"], 1]]])
    for recipe in be.get("MIXER_RECIPES") or []:
        if not isinstance(recipe, dict) or not isinstance(recipe.get("input"), dict):
            continue
        label = " + ".join("%s x%d" % (k, v) for k, v in recipe["input"].items())
        result = recipe.get("output") or {}
        if result.get("id"):
            note = " (needs heat)" if recipe.get("requiresHeat") or recipe.get("requiresSuperheat") else ""
            data["mixing"].append([label + note, [[result["id"], int(result.get("amount", 1))]]])

    for recipe in be2.get("SPOUT_RECIPES") or []:
        if not isinstance(recipe, dict) or not recipe.get("input") or not recipe.get("output"):
            continue
        fluid = str(recipe.get("fluid", "")).split(":")[-1].replace("_bucket", "")
        data["spouting"].append(["%s + %s" % (recipe["input"], fluid or "fluid"),
                                 [[recipe["output"], 1]]])

    # ---- More Create's additions --------------------------------------
    added = set()
    for entry in gap.get("crushing", []):
        data["crushing"].append([entry["input"], normalise_outputs(entry["outputs"])])
        added.add(("crushing", entry["input"]))
    for entry in gap.get("milling", []):
        data["milling"].append([entry["input"], normalise_outputs(entry["outputs"])])
        added.add(("milling", entry["input"]))
    for entry in gap.get("splashing", []):
        data["washing"].append([entry["input"], normalise_outputs(entry["outputs"])])
        added.add(("washing", entry["input"]))
    for entry in gap.get("pressing", []):
        data["pressing"].append([entry["input"], [[entry["outputs"][0]["item"], 1]]])
        added.add(("pressing", entry["input"]))

    # The washing fix replaces a broken entry rather than adding one.
    data["washing"] = [row for row in data["washing"] if row[0] != "create:crushed_raw_copper"]
    data["washing"].append(["create:crushed_raw_copper",
                            [["minecraft:copper_ingot", 1], ["minecraft:clay_ball", 1, 0.5]]])

    for key in data:
        # Stable order, and drop any duplicate input that slipped through.
        seen, unique = set(), []
        for row in sorted(data[key], key=lambda r: str(r[0])):
            if str(row[0]) in seen:
                continue
            seen.add(str(row[0]))
            unique.append(row)
        data[key] = unique

    lines = [
        "/**",
        " * Every processing recipe in the game, for the Recipe Book.",
        " *",
        " * Generated by tools/gen_book.py - do not edit by hand.",
        " *",
        " * Merges the tables built into the Create Bedrock addon with the recipes",
        " * More Create registers, so the book is a complete reference rather than a",
        " * list of additions. Each row is [input, [[item, count, chance?], ...]].",
        " */",
        "",
        "export const MACHINES = [",
    ]
    for key, (title, subtitle) in MACHINES.items():
        lines.append('    { key: %s, title: %s, subtitle: %s },'
                     % (json.dumps(key), json.dumps(title), json.dumps(subtitle)))
    lines.append("];")
    lines.append("")
    lines.append("export const RECIPES = {")
    for key in MACHINES:
        lines.append("    %s: [" % json.dumps(key))
        for row in data[key]:
            lines.append("        %s," % json.dumps(row, separators=(",", ":")))
        lines.append("    ],")
    lines.append("};")
    lines.append("")
    lines.append("/** Stonecutting is a large any-to-any web, summarised rather than listed. */")
    lines.append("export const STONECUTTING_NOTE =")
    lines.append('    "Every Create stone family cuts freely between its own variants on a\\n" +')
    lines.append('    "Stonecutter - andesite, asurine, calcite, crimsite, deepslate, diorite,\\n" +')
    lines.append('    "dripstone, granite, limestone, ochrum, scoria, scorchia, tuff and\\n" +')
    lines.append('    "veridium. Put any block of a family in to see all of its variants.";')
    lines.append("")
    total = sum(len(v) for v in data.values())
    lines.append("export const TOTAL = %d;" % total)
    lines.append("")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("\n".join(lines))

    print("wrote %s" % os.path.relpath(OUT, ROOT))
    for key, (title, _) in MACHINES.items():
        print("   %-26s %d" % (title, len(data[key])))
    print("   %-26s %d" % ("TOTAL", total))


if __name__ == "__main__":
    main()
