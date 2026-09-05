#!/usr/bin/env python3
"""Write the Bedrock recipe JSON files for recipes that need no Create hook.

Crafting-table and cooking recipes are plain Bedrock data, so More Create ships
them as ordinary recipe files rather than registering them through Create's
Compatibility API.

Usage: gen_native_recipes.py tools/data/gap_report_v2.json
"""

import json
import os
import shutil
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "packs/behavior/recipes/morecreate/create")


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4)
        handle.write("\n")


def cooking(entry):
    return OrderedDict([
        ("format_version", "1.20.10"),
        ("minecraft:recipe_furnace", OrderedDict([
            ("description", {"identifier": "morecreate:%s" % entry["name"]}),
            ("tags", entry["tags"]),
            ("input", entry["input"]),
            ("output", entry["output"]),
        ])),
    ])


def crafting(entry):
    identifier = "morecreate:%s" % entry["name"]
    result = OrderedDict([("item", entry["result"]["item"]),
                          ("count", entry["result"]["count"])])
    if entry["shape"] == "shaped":
        return OrderedDict([
            ("format_version", "1.12"),
            ("minecraft:recipe_shaped", OrderedDict([
                ("description", {"identifier": identifier}),
                ("tags", ["crafting_table"]),
                ("pattern", entry["pattern"]),
                ("key", entry["key"]),
                ("result", result),
            ])),
        ])
    return OrderedDict([
        ("format_version", "1.12"),
        ("minecraft:recipe_shapeless", OrderedDict([
            ("description", {"identifier": identifier}),
            ("tags", ["crafting_table"]),
            ("ingredients", entry["ingredients"]),
            ("result", result),
        ])),
    ])


def main():
    report = json.load(open(sys.argv[1], encoding="utf-8"))

    # Regenerated wholesale so removing a recipe upstream removes the file too.
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)

    written = []
    for entry in report.get("native_cooking", []):
        path = os.path.join(OUT, "cooking", entry["name"] + ".json")
        write(path, cooking(entry))
        written.append(("cooking", entry["name"], "%s -> %s %s"
                        % (entry["input"], entry["output"], entry["tags"])))
    for entry in report.get("native_crafting", []):
        path = os.path.join(OUT, "crafting", entry["name"] + ".json")
        write(path, crafting(entry))
        written.append(("crafting", entry["name"], "-> %s x%d"
                        % (entry["result"]["item"], entry["result"]["count"])))

    print("wrote %d native recipe files into %s"
          % (len(written), os.path.relpath(OUT, ROOT)))
    for kind, name, detail in written:
        print("   %-9s %-38s %s" % (kind, name, detail))


if __name__ == "__main__":
    main()
