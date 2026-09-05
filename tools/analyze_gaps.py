#!/usr/bin/env python3
"""Diff Create (Java) against the Create Bedrock addon, for every recipe type.

Writes tools/data/gap_report_v2.json describing what Bedrock is missing, split
by where More Create can register it:

  compat/*   goes through Create's Compatibility API v2 script events
  native/*   ships as ordinary Bedrock recipe JSON (crafting and cooking)

Anything whose items do not exist on Bedrock is dropped, so every id in the
report is one the Create Bedrock addon actually defines (or vanilla Bedrock
already has).

Usage: analyze_gaps.py <extracted Create jar dir> <extracted Create BP dir>
"""

import glob
import json
import os
import re
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tools/data")

# Java item id -> Bedrock item id, for the handful that genuinely differ.
RENAME = {
    "minecraft:terracotta": "minecraft:hardened_clay",
    "minecraft:magma_block": "minecraft:magma",
    "minecraft:nether_quartz_ore": "minecraft:quartz_ore",
    "minecraft:snow_block": "minecraft:snow",
    "minecraft:cobweb": "minecraft:web",
    "minecraft:dead_bush": "minecraft:deadbush",
    "minecraft:lily_pad": "minecraft:waterlily",
    "minecraft:melon": "minecraft:melon_block",
}

# Java tag -> a concrete Bedrock item. Bedrock has no `c:` tags at all, and only
# a small set of `minecraft:` ones, so everything except the proven
# `minecraft:planks` is pinned to a representative item.
TAG_ITEM = {
    "c:nuggets/iron": "minecraft:iron_nugget",
    "c:nuggets/zinc": "create:zinc_nugget",
    "c:nuggets/gold": "minecraft:gold_nugget",
    "c:nuggets/brass": "create:brass_nugget",
    "c:ingots/iron": "minecraft:iron_ingot",
    "c:ingots/gold": "minecraft:gold_ingot",
    "c:ingots/copper": "minecraft:copper_ingot",
    "c:ingots/zinc": "create:zinc_ingot",
    "c:ingots/brass": "create:brass_ingot",
    "c:plates/iron": "create:iron_sheet",
    "c:plates/gold": "create:golden_sheet",
    "c:plates/copper": "create:copper_sheet",
    "c:plates/brass": "create:brass_sheet",
    "c:stones": "minecraft:stone",
    "c:cobblestones": "minecraft:cobblestone",
    "c:storage_blocks/iron": "minecraft:iron_block",
    "c:storage_blocks/gold": "minecraft:gold_block",
    "c:storage_blocks/copper": "minecraft:copper_block",
    "c:storage_blocks/zinc": "create:zinc_block",
    "c:raw_materials/iron": "minecraft:raw_iron",
    "c:raw_materials/gold": "minecraft:raw_gold",
    "c:raw_materials/copper": "minecraft:raw_copper",
    "c:raw_materials/zinc": "create:raw_zinc",
    "c:dusts/redstone": "minecraft:redstone",
    "c:gems/quartz": "minecraft:quartz",
    "c:dyes/white": "minecraft:white_dye",
    "c:strings": "minecraft:string",
    "c:leathers": "minecraft:leather",
    "c:eggs": "minecraft:egg",
    "c:crops/wheat": "minecraft:wheat",
    "c:seeds": "minecraft:wheat_seeds",
    "minecraft:wooden_slabs": "minecraft:oak_slab",
    "minecraft:logs": "minecraft:oak_log",
    "minecraft:logs_that_burn": "minecraft:oak_log",
    "c:stripped_logs": "minecraft:stripped_oak_log",
    "minecraft:wool": "minecraft:white_wool",
    "minecraft:stone_crafting_materials": "minecraft:cobblestone",
    "c:glass_blocks/colorless": "minecraft:glass",
    "c:glass_panes/colorless": "minecraft:glass_pane",
    "c:glass_blocks": "minecraft:glass",
    "c:glass_panes": "minecraft:glass_pane",
}
# Tags Bedrock understands directly in a recipe key.
TAG_PASSTHROUGH = {"minecraft:planks"}

# Fluids, as the Bedrock addon names them (bucket-style container ids).
FLUID_ITEM = {
    "minecraft:water": "minecraft:water_bucket",
    "minecraft:lava": "minecraft:lava_bucket",
    "minecraft:milk": "minecraft:milk_bucket",
    "create:honey": "create:honey_bucket",
    "create:chocolate": "create:chocolate_bucket",
}


def load(path):
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


def build_id_sets(be_dir):
    """`defined` = ids the Bedrock pack formally registers; `proven` = any id it mentions."""
    proven, defined = set(), set()
    for base, _, files in os.walk(be_dir):
        for name in files:
            path = os.path.join(base, name)
            if not name.endswith((".json", ".js", ".lang")):
                continue
            try:
                text = open(path, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            proven |= set(re.findall(r"\b(minecraft:[a-z0-9_]+)", text))
            proven |= set(re.findall(r"\b(create:[a-z0-9_.]+)", text))
            if not name.endswith(".json"):
                continue
            try:
                doc = load(path)
            except Exception:
                continue
            if not isinstance(doc, dict):
                continue
            for key in ("minecraft:item", "minecraft:block"):
                node = doc.get(key)
                if isinstance(node, dict):
                    ident = node.get("description", {}).get("identifier")
                    if ident:
                        defined.add(ident)
    return proven, defined


class World:
    def __init__(self, jar, be_dir):
        self.jar = jar
        self.recipe_root = os.path.join(jar, "data/create/recipe")
        self.proven, self.defined = build_id_sets(be_dir)
        self.tags = self._index_tags()

    def _index_tags(self):
        index = {}
        data = os.path.join(self.jar, "data")
        for ns in sorted(os.listdir(data)):
            base = os.path.join(data, ns, "tags")
            if not os.path.isdir(base):
                continue
            for kind in ("item", "block"):
                kb = os.path.join(base, kind)
                if not os.path.isdir(kb):
                    continue
                for b, _, files in os.walk(kb):
                    for n in files:
                        if n.endswith(".json"):
                            rel = os.path.relpath(os.path.join(b, n), kb)[:-5].replace(os.sep, "/")
                            index.setdefault("%s:%s" % (ns, rel), os.path.join(b, n))
        return index

    def resolve_tag(self, tag, seen=None):
        seen = seen or set()
        if tag in seen or tag not in self.tags:
            return []
        seen.add(tag)
        try:
            doc = load(self.tags[tag])
        except Exception:
            return []
        out = []
        for value in doc.get("values", []):
            vid = value.get("id") if isinstance(value, dict) else value
            if not isinstance(vid, str):
                continue
            stripped = vid.lstrip("#")
            if vid.startswith("#") or stripped in self.tags:
                out += self.resolve_tag(stripped, seen)
            else:
                out.append(stripped if ":" in stripped else "minecraft:" + stripped)
        return out

    def bedrock(self, item):
        return RENAME.get(item, item)

    def ok(self, item):
        item = self.bedrock(item)
        if item.startswith("create:"):
            return item in self.defined
        if item.startswith("minecraft:"):
            return item in self.proven
        return False

    def ingredient(self, node):
        """Resolve one ingredient slot to {'item': id} or {'tag': t}, or None."""
        if isinstance(node, list):
            for entry in node:
                got = self.ingredient(entry)
                if got:
                    return got
            return None
        if not isinstance(node, dict):
            return None
        if "item" in node:
            item = self.bedrock(node["item"])
            return {"item": item} if self.ok(item) else None
        if "tag" in node:
            tag = node["tag"]
            if tag in TAG_PASSTHROUGH:
                return {"tag": tag}
            pinned = TAG_ITEM.get(tag)
            if pinned and self.ok(pinned):
                return {"item": self.bedrock(pinned)}
            for candidate in self.resolve_tag(tag):
                candidate = self.bedrock(candidate)
                if self.ok(candidate):
                    return {"item": candidate}
            return None
        if node.get("type") == "neoforge:compound" or "ingredients" in node:
            return self.ingredient(node.get("ingredients", []))
        return None

    def read_dir(self, name):
        """All recipes under a category, including its subfolders.

        Create groups `crafting/` into appliances, kinetics, materials and so
        on, so this has to recurse - but `compat/` subfolders hold recipes for
        other Java mods and are skipped.
        """
        out = []
        root = os.path.join(self.recipe_root, name)
        for path in sorted(glob.glob(os.path.join(root, "**/*.json"), recursive=True)):
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            if rel.startswith("compat/") or "/compat/" in rel:
                continue
            try:
                doc = load(path)
            except Exception:
                continue
            conditions = doc.get("neoforge:conditions", [])
            if any(isinstance(c, dict) and c.get("type") == "neoforge:mod_loaded" for c in conditions):
                continue
            out.append((rel[:-5].replace("/", "_"), doc))
        return out

    def read_top_level(self):
        """Recipes sitting directly in `recipe/`, outside any category folder.

        Create keeps its stonecutting web and a large batch of crafting recipes
        here rather than in a named subfolder.
        """
        out = []
        for path in sorted(glob.glob(os.path.join(self.recipe_root, "*.json"))):
            try:
                doc = load(path)
            except Exception:
                continue
            conditions = doc.get("neoforge:conditions", [])
            if any(isinstance(c, dict) and c.get("type") == "neoforge:mod_loaded" for c in conditions):
                continue
            out.append((os.path.basename(path)[:-5], doc))
        return out

    def sources(self, node):
        """Every concrete Bedrock item an ingredient could be, for tag expansion."""
        if not isinstance(node, dict):
            return []
        if "item" in node:
            item = self.bedrock(node["item"])
            return [item] if self.ok(item) else []
        if "tag" in node:
            found = [self.bedrock(x) for x in self.resolve_tag(node["tag"])]
            found = [x for x in found if self.ok(x)]
            if found:
                return found
            pinned = TAG_ITEM.get(node["tag"])
            return [pinned] if pinned and self.ok(pinned) else []
        return []


def results_of(world, doc, key="results"):
    raw = doc.get(key)
    if raw is None and "result" in doc:
        raw = doc["result"]
    # Cooking and crafting recipes carry a single `result` object; the Create
    # machine types carry a `results` list.
    if isinstance(raw, dict):
        raw = [raw]
    rows = []
    for entry in raw or []:
        if not isinstance(entry, dict):
            continue
        rid = entry.get("id") or entry.get("item")
        if not rid:
            continue
        rid = world.bedrock(rid)
        if not world.ok(rid):
            return None
        row = OrderedDict([("item", rid), ("count", int(entry.get("count", 1)))])
        chance = float(entry.get("chance", 1.0))
        if chance < 1.0:
            row["chance"] = round(chance, 4)
        rows.append(row)
    return rows or None


# --------------------------------------------------------------------------- #
def analyse(world, be_tables):
    report = OrderedDict()

    # ---- compat: spouting, from Create's `filling` recipes -----------------
    have_spout = {(r.get("fluid"), r.get("input")) for r in be_tables.get("SPOUT_RECIPES", [])}
    spouting = []
    for name, doc in world.read_dir("filling"):
        item_slot, fluid_slot, amount = None, None, 250
        for node in doc.get("ingredients", []):
            if isinstance(node, dict) and "fluid" in node:
                fluid_slot = FLUID_ITEM.get(node["fluid"])
                amount = int(node.get("amount", 250))
            else:
                got = world.ingredient(node)
                if got and "item" in got:
                    item_slot = got["item"]
        results = results_of(world, doc)
        if not item_slot or not fluid_slot or not results:
            continue
        if (fluid_slot, item_slot) in have_spout:
            continue
        spouting.append(OrderedDict([
            ("name", name), ("fluid", fluid_slot), ("input", item_slot),
            ("output", results[0]["item"]), ("amount", amount),
        ]))
    report["compat_spouting"] = spouting

    # ---- compat: mechanical crafting --------------------------------------
    have_crafter = set()
    for table in ("ADDON_CRAFTING_RECIPES", "VANILLA_CRAFTING_RECIPES"):
        for recipe in be_tables.get(table, []) or []:
            rid = (recipe.get("result") or {}).get("id")
            if rid:
                have_crafter.add(rid)
    mech = []
    for name, doc in world.read_dir("mechanical_crafting"):
        results = results_of(world, doc)
        if not results or results[0]["item"] in have_crafter:
            continue
        key = OrderedDict()
        ok = True
        for symbol, node in (doc.get("key") or {}).items():
            got = world.ingredient(node)
            if not got:
                ok = False
                break
            key[symbol] = got
        if not ok or not doc.get("pattern"):
            continue
        mech.append(OrderedDict([
            ("name", name), ("pattern", doc["pattern"]), ("key", key),
            ("result", OrderedDict([("id", results[0]["item"]), ("amount", results[0]["count"])])),
        ]))
    report["compat_mechanical_crafting"] = mech

    # ---- compat: sequenced assembly ---------------------------------------
    # Match on the product, not the recipe id: Bedrock names its sequenced
    # recipes without a namespace, so comparing ids would miss the duplicate
    # and register a second recipe for the same item.
    have_seq = {r.get("result") for r in be_tables.get("SEQUENCED_RECIPES", []) or []}
    OPS = {"create:deploying": "deploy", "create:pressing": "press",
           "create:filling": "spout", "create:cutting": "cut"}
    sequenced = []
    for name, doc in world.read_dir("sequenced_assembly"):
        surface = world.ingredient(doc.get("ingredient"))
        results = results_of(world, doc)
        transitional = doc.get("transitional_item") or {}
        in_progress = world.bedrock(transitional.get("id") or transitional.get("item") or "")
        if not surface or "item" not in surface or not results:
            continue
        recipe_id = "morecreate:%s" % name
        if results[0]["item"] in have_seq or (in_progress and not world.ok(in_progress)):
            continue
        steps, ok = [], True
        for step in doc.get("sequence", []):
            operation = OPS.get(step.get("type"))
            if not operation:
                ok = False
                break
            held = None
            for node in step.get("ingredients", [])[1:] or []:
                got = world.ingredient(node)
                if got and "item" in got:
                    held = got["item"]
            steps.append(OrderedDict([("operation", operation)] + ([("held", held)] if held else [])))
        if not ok or not steps:
            continue
        sequenced.append(OrderedDict([
            ("id", recipe_id), ("input", surface["item"]),
            ("inProgress", in_progress or surface["item"]),
            ("passes", int(doc.get("loops", 1))),
            ("sequence", steps), ("output", results[0]["item"]),
        ]))
    report["compat_sequenced"] = sequenced

    # ---- native: cooking ---------------------------------------------------
    # Create's `blasting` / `smelting` folders are ordinary vanilla furnace
    # recipes; Bedrock expresses all of them with minecraft:recipe_furnace and
    # a `tags` list naming which appliance accepts them.
    # Bedrock recipes list every appliance that accepts them in one `tags`
    # array, so coverage has to be compared per appliance: an input already
    # smeltable in a furnace may still be missing from the smoker.
    be_cooking = {}
    for path in glob.glob(os.path.join(os.environ.get("BE_RECIPES", ""), "**/*.json"), recursive=True):
        try:
            doc = load(path)
        except Exception:
            continue
        node = doc.get("minecraft:recipe_furnace")
        if not isinstance(node, dict):
            continue
        ing = node.get("input")
        ing = ing.get("item") if isinstance(ing, dict) else ing
        if ing:
            be_cooking.setdefault(ing, set()).update(node.get("tags", []))

    COOK = [("smelting", ["furnace"]), ("blasting", ["blast_furnace"]),
            ("smoking", ["smoker"]), ("campfire_cooking", ["campfire", "soul_campfire"])]
    cooking = []
    for folder, tags in COOK:
        for name, doc in world.read_dir(folder):
            got = world.ingredient(doc.get("ingredient"))
            results = results_of(world, doc, "result")
            if not got or "item" not in got or not results:
                continue
            wanted = [t for t in tags if t not in be_cooking.get(got["item"], set())]
            if not wanted:
                continue
            be_cooking.setdefault(got["item"], set()).update(wanted)
            cooking.append(OrderedDict([
                ("name", "%s_%s" % (folder, name)), ("input", got["item"]),
                ("output", results[0]["item"]), ("count", results[0]["count"]),
                ("tags", wanted), ("time", float(doc.get("cookingtime", 200)) / 20.0),
            ]))
    report["native_cooking"] = cooking

    # ---- native: crafting --------------------------------------------------
    be_results = set()
    for path in glob.glob(os.path.join(os.environ.get("BE_RECIPES", ""), "**/*.json"), recursive=True):
        try:
            doc = load(path)
        except Exception:
            continue
        for key in ("minecraft:recipe_shaped", "minecraft:recipe_shapeless"):
            node = doc.get(key)
            if isinstance(node, dict):
                res = node.get("result")
                res = res[0] if isinstance(res, list) and res else res
                if isinstance(res, dict) and res.get("item"):
                    be_results.add(res["item"])

    # Create keeps a large batch of crafting recipes loose in `recipe/` as well
    # as under `recipe/crafting/`, so both are scanned.
    crafting = []
    top_level = [(n, d) for n, d in world.read_top_level()
                 if d.get("type", "").startswith("minecraft:crafting_")]
    for name, doc in world.read_dir("crafting") + top_level:
        kind = doc.get("type")
        results = results_of(world, doc, "result")
        if not results or results[0]["item"] in be_results:
            continue
        if kind == "minecraft:crafting_shaped":
            key, ok = OrderedDict(), True
            for symbol, node in (doc.get("key") or {}).items():
                got = world.ingredient(node)
                if not got:
                    ok = False
                    break
                key[symbol] = got
            if not ok or not doc.get("pattern"):
                continue
            crafting.append(OrderedDict([
                ("name", name), ("shape", "shaped"), ("pattern", doc["pattern"]),
                ("key", key), ("result", results[0]),
            ]))
        elif kind == "minecraft:crafting_shapeless":
            ingredients, ok = [], True
            for node in doc.get("ingredients", []):
                got = world.ingredient(node)
                if not got:
                    ok = False
                    break
                ingredients.append(got)
            if not ok or not ingredients or len(ingredients) > 9:
                continue
            crafting.append(OrderedDict([
                ("name", name), ("shape", "shapeless"),
                ("ingredients", ingredients), ("result", results[0]),
            ]))
    report["native_crafting"] = crafting

    # ---- native: stonecutting ---------------------------------------------
    # Create's stone families are wired as an any-to-any web through item tags.
    # Bedrock stonecutter recipes take one concrete ingredient, so each tag is
    # expanded into a recipe per source block.
    have_cut = set()
    for path in glob.glob(os.path.join(os.environ.get("BE_RECIPES", ""), "**/*.json"), recursive=True):
        try:
            doc = load(path)
        except Exception:
            continue
        for key in ("minecraft:recipe_shaped", "minecraft:recipe_shapeless"):
            node = doc.get(key)
            if not isinstance(node, dict) or "stonecutter" not in (node.get("tags") or []):
                continue
            res = node.get("result")
            res = res[0] if isinstance(res, list) and res else res
            rid = res.get("item") if isinstance(res, dict) else None
            slots = node.get("ingredients") or list((node.get("key") or {}).values())
            for slot in slots:
                iid = slot.get("item") if isinstance(slot, dict) else slot
                if iid and rid:
                    have_cut.add((iid, rid))

    seen, stonecutting = set(), []
    for name, doc in world.read_top_level():
        if doc.get("type") != "minecraft:stonecutting":
            continue
        res = doc.get("result") or {}
        rid = world.bedrock(res.get("id") or res.get("item") or "")
        if not world.ok(rid):
            continue
        count = int(res.get("count", 1))
        for source in world.sources(doc.get("ingredient") or {}):
            # A block cutting into itself is a no-op, and Bedrock shows it as a
            # confusing empty stonecutter entry.
            if source == rid or (source, rid) in have_cut or (source, rid) in seen:
                continue
            seen.add((source, rid))
            stonecutting.append(OrderedDict([
                ("input", source), ("output", rid), ("count", count),
            ]))
    report["native_stonecutting"] = stonecutting

    # ---- categories Create Bedrock offers no hook for ----------------------
    report["_unhookable"] = OrderedDict(
        (folder, len(world.read_dir(folder)))
        for folder in ("cutting", "deploying", "emptying", "item_application",
                       "sandpaper_polishing", "compacting")
    )
    return report


def main():
    jar, be_dir = sys.argv[1], sys.argv[2]
    os.environ.setdefault("BE_RECIPES", os.path.join(be_dir, "recipes"))
    world = World(jar, be_dir)
    be_tables = load(os.path.join(DATA, "be_recipes2.json"))
    report = analyse(world, be_tables)

    os.makedirs(DATA, exist_ok=True)
    out = os.path.join(DATA, "gap_report_v2.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1)

    print("ids: %d defined / %d proven" % (len(world.defined), len(world.proven)))
    for section, rows in report.items():
        if section.startswith("_"):
            continue
        print("%-28s %d" % (section, len(rows)))
    print("\nno hook available in Create Bedrock:")
    for folder, count in report["_unhookable"].items():
        print("   %-22s %d Java recipes" % (folder, count))
    print("\nwrote %s" % os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
