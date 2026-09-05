#!/usr/bin/env python3
"""Emit the recipe tables More Create registers with Create.

Input is the gap report produced by comparing Create 1.21.1's own recipe data
against the tables already built into the Create Bedrock addon, so every recipe
written here is one that exists in Create but was missing on Bedrock, and every
item id it mentions is one the Bedrock addon actually defines.
"""

import json
import os
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "packs/behavior/scripts/morecreate/recipes/missing.js")

# Particle colours, chosen from the dominant product so the machine's
# processing particles match what Create shows.
PALETTE = {
    "create:crushed_raw_zinc": (0.78, 0.80, 0.83),
    "create:zinc_nugget": (0.78, 0.80, 0.83),
    "create:crushed_raw_iron": (0.70, 0.40, 0.30),
    "minecraft:iron_nugget": (0.70, 0.40, 0.30),
    "create:crushed_raw_gold": (0.95, 0.80, 0.15),
    "minecraft:gold_nugget": (0.95, 0.80, 0.15),
    "create:crushed_raw_copper": (0.85, 0.50, 0.30),
    "minecraft:quartz": (0.93, 0.90, 0.86),
    "minecraft:flint": (0.35, 0.33, 0.32),
    "minecraft:nether_wart": (0.45, 0.10, 0.12),
    "minecraft:glowstone_dust": (0.98, 0.90, 0.55),
    "minecraft:red_sand": (0.76, 0.40, 0.20),
    "minecraft:pink_dye": (0.95, 0.55, 0.74),
    "minecraft:cyan_dye": (0.09, 0.61, 0.61),
    "minecraft:orange_dye": (0.98, 0.50, 0.11),
    "create:weathered_iron_block": (0.45, 0.55, 0.48),
    "minecraft:dirt_path": (0.55, 0.45, 0.30),
    "minecraft:copper_ingot": (0.85, 0.50, 0.30),
    "minecraft:ice": (0.72, 0.85, 0.98),
}
DEFAULT_RGB = (0.60, 0.58, 0.55)


def rgb_for(outputs):
    for out in outputs:
        if out["item"] in PALETTE:
            return PALETTE[out["item"]]
    return DEFAULT_RGB


def js(value, indent=0):
    """Render a Python value as readable JavaScript."""
    pad = "    " * indent
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        text = repr(round(value, 4))
        return text.rstrip("0").rstrip(".") if "." in text else text
    if isinstance(value, list):
        if not value:
            return "[]"
        inner = ",\n".join(pad + "    " + js(v, indent + 1) for v in value)
        return "[\n" + inner + "\n" + pad + "]"
    if isinstance(value, (dict, OrderedDict)):
        if not value:
            return "{}"
        parts = []
        for key, val in value.items():
            safe = key if key.replace("_", "a").isalnum() and not key[0].isdigit() else json.dumps(key)
            parts.append(pad + "    " + safe + ": " + js(val, indent + 1))
        return "{\n" + ",\n".join(parts) + "\n" + pad + "}"
    raise TypeError(type(value))


def outputs_of(entry):
    return [OrderedDict([("item", o["item"]), ("count", o["count"])] +
                        ([("chance", o["chance"])] if o["chance"] < 1 else []))
            for o in entry["outputs"]]


def main():
    report_path = sys.argv[1]
    be_path = sys.argv[2]
    report = json.load(open(report_path))
    be = json.load(open(be_path))

    blocks = []

    # ---- crushing wheels ------------------------------------------------
    crushing = []
    for entry in report["crushing"]:
        outs = outputs_of(entry)
        r, g, b = rgb_for(entry["outputs"])
        crushing.append(OrderedDict([
            ("input", entry["input"]),
            ("duration", entry["duration"]),
            ("particleRGB", OrderedDict([("red", r), ("green", g), ("blue", b), ("alpha", 1)])),
            ("outputs", outs),
        ]))
    blocks.append(("CRUSHING", crushing,
                   "Crushing Wheel recipes Create has but Bedrock was missing -\n"
                   "mostly the decorative stone family, which the addon ships as blocks\n"
                   "but could not crush, plus zinc ore and a few vanilla oddities."))

    # ---- millstone ------------------------------------------------------
    millstone = []
    for entry in report["milling"]:
        outs = outputs_of(entry)
        r, g, b = rgb_for(entry["outputs"])
        millstone.append(OrderedDict([
            ("input", entry["input"]),
            ("duration", entry["duration"]),
            ("particleRGB", OrderedDict([("red", r), ("green", g), ("blue", b), ("alpha", 1)])),
            ("outputs", outs),
        ]))
    blocks.append(("MILLSTONE", millstone, "Millstone recipes missing from the Bedrock tables."))

    # ---- milling recipes that Crushing Wheels should also accept --------
    # In Create, a Crushing Wheel falls back to the milling recipe when no
    # crushing recipe exists for an item. Bedrock's wheel only ever looked at
    # crushing recipes, so every millstone recipe without a crushing
    # counterpart was silently unusable in a wheel.
    have_crushing = set(be["CRUSHING_RECIPES"].keys()) | {e["input"] for e in report["crushing"]}
    fallback = []
    source = dict(be["millstoneRecipes"])
    for entry in report["milling"]:
        source[entry["input"]] = {
            "duration": entry["duration"],
            "output": entry["outputs"],
        }
    for item_id in sorted(source):
        if item_id in have_crushing:
            continue
        recipe = source[item_id]
        outs = []
        for o in recipe.get("output", []):
            item = o.get("item")
            if not item:
                continue
            row = OrderedDict([("item", item), ("count", int(o.get("count", 1)))])
            chance = float(o.get("chance", 1))
            if chance < 1:
                row["chance"] = round(chance, 4)
            outs.append(row)
        if not outs:
            continue
        particle = recipe.get("particleRGB")
        if not particle:
            r, g, b = rgb_for([{"item": outs[0]["item"]}])
            particle = OrderedDict([("red", r), ("green", g), ("blue", b), ("alpha", 1)])
        else:
            particle = OrderedDict([(k, round(float(particle[k]), 4)) for k in ("red", "green", "blue", "alpha")
                                    if k in particle])
        fallback.append(OrderedDict([
            ("input", item_id),
            ("duration", int(recipe.get("duration", 100))),
            ("particleRGB", particle),
            ("outputs", outs),
        ]))
    blocks.append(("CRUSHING_FROM_MILLING", fallback,
                   "Create lets a Crushing Wheel run a milling recipe when the item has\n"
                   "no dedicated crushing recipe. Bedrock's wheel never did, so these\n"
                   "mirror the Millstone table into the wheel."))

    # ---- fan processing -------------------------------------------------
    for key, const, note in [
        ("splashing", "SPLASHING", "Bulk Washing (fan + water)."),
        ("haunting", "HAUNTING", "Bulk Haunting (fan + soul fire)."),
        ("blasting", "BLASTING", "Bulk Smelting / melting (fan + lava or fire)."),
        ("smoking", "SMOKING", "Bulk Smoking (fan + campfire)."),
    ]:
        rows = [OrderedDict([("input", e["input"]), ("outputs", outputs_of(e))])
                for e in report[key]]
        blocks.append((const, rows, note))

    # ---- pressing -------------------------------------------------------
    pressing = [OrderedDict([("input", e["input"]), ("output", e["outputs"][0]["item"])])
                for e in report["pressing"]]
    blocks.append(("PRESSING", pressing, "Mechanical Press recipes missing on Bedrock."))

    # ---- mixing ---------------------------------------------------------
    # Only genuinely absent recipes. Where the Bedrock addon already mixes the
    # same set of ingredients at a different ratio (andesite + zinc nugget, for
    # one) that is a deliberate balance choice, not a gap - registering ours
    # would shadow theirs, because compatibility recipes are matched first.
    existing_sets = set()
    for recipe in be["MIXER_RECIPES"]:
        if isinstance(recipe, dict) and isinstance(recipe.get("input"), dict):
            existing_sets.add(frozenset(recipe["input"].keys()))

    mixing = []
    for entry in report["mixing"]:
        if frozenset(entry["input"].keys()) in existing_sets:
            continue
        out = entry["outputs"][0]
        r, g, b = rgb_for(entry["outputs"])
        row = OrderedDict([
            ("input", OrderedDict(sorted(entry["input"].items()))),
            ("output", OrderedDict([("id", out["item"]), ("amount", out["count"])])),
        ])
        if entry.get("heated"):
            row["requiresHeat"] = True
        row["particleColor"] = OrderedDict([("red", r), ("green", g), ("blue", b), ("alpha", 1)])
        mixing.append(row)
    blocks.append(("MIXING", mixing, "Mechanical Mixer recipes missing on Bedrock."))

    # ---- corrections ----------------------------------------------------
    # The Bedrock addon washes Crushed Raw Copper into `create:copper_nugget`,
    # but that item is never defined anywhere in the pack (only the zinc, brass
    # and experience nuggets exist), so the recipe yields nothing. Bedrock has
    # no vanilla copper nugget either, so the nine nuggets Create would give
    # are returned as the single ingot they are worth.
    corrections = [OrderedDict([
        ("input", "create:crushed_raw_copper"),
        ("outputs", [
            OrderedDict([("item", "minecraft:copper_ingot"), ("count", 1)]),
            OrderedDict([("item", "minecraft:clay_ball"), ("count", 1), ("chance", 0.5)]),
        ]),
    ])]
    blocks.append(("SPLASHING_FIXES", corrections,
                   "Corrections to existing Bedrock recipes that referenced items which\n"
                   "do not exist. Compatibility recipes are matched before the built-in\n"
                   "tables, so registering these replaces the broken ones."))

    # ---- second pass: the remaining compat hooks -------------------------
    v2 = {}
    if len(sys.argv) > 3 and os.path.isfile(sys.argv[3]):
        v2 = json.load(open(sys.argv[3]))

    mech = []
    for entry in v2.get("compat_mechanical_crafting", []):
        mech.append(OrderedDict([
            ("pattern", entry["pattern"]),
            ("key", entry["key"]),
            ("result", entry["result"]),
        ]))
    blocks.append(("MECHANICAL_CRAFTING", mech,
                   "Mechanical Crafter recipes. The Crushing Wheel is the important one:\n"
                   "the Bedrock addon's crafter already knows how to match a 5x5 pattern\n"
                   "(its own code comments mention the wheel) but the recipe was never\n"
                   "registered, leaving Crushing Wheels uncraftable."))

    spouting = []
    for entry in v2.get("compat_spouting", []):
        spouting.append(OrderedDict([
            ("fluid", entry["fluid"]), ("input", entry["input"]),
            ("output", entry["output"]), ("amount", entry["amount"]),
        ]))
    blocks.append(("SPOUTING", spouting, "Spout filling recipes missing on Bedrock."))

    sequenced = []
    for entry in v2.get("compat_sequenced", []):
        sequenced.append(OrderedDict([
            ("id", entry["id"]), ("input", entry["input"]),
            ("inProgress", entry["inProgress"]), ("passes", entry["passes"]),
            ("sequence", entry["sequence"]), ("output", entry["output"]),
        ]))
    blocks.append(("SEQUENCED", sequenced, "Sequenced assembly recipes missing on Bedrock."))

    header = '''/**
 * Recipes that exist in Create but were missing from the Create Bedrock addon.
 *
 * Generated by tools/gen_recipes.py - do not edit by hand.
 *
 * The list was produced by diffing Create 1.21.1's recipe data against the
 * tables built into the Bedrock addon, then dropping anything whose items do
 * not exist on Bedrock. Every id below is one the Bedrock addon defines.
 */

'''
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write(header)
        for const, rows, note in blocks:
            handle.write("/**\n * %s\n */\n" % note.replace("\n", "\n * "))
            handle.write("export const %s = %s;\n\n" % (const, js(rows)))
        total = sum(len(rows) for _, rows, _ in blocks)
        handle.write("/** Total recipes added by More Create. */\nexport const TOTAL = %d;\n" % total)

    print("wrote", OUT)
    for const, rows, _ in blocks:
        print("   %-24s %d" % (const, len(rows)))
    print("   %-24s %d" % ("TOTAL", sum(len(r) for _, r, _ in blocks)))


if __name__ == "__main__":
    main()
