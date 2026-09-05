#!/usr/bin/env python3
"""Validate the More Create packs before they are zipped.

Checks JSON syntax, manifest/UUID wiring, that every texture and geometry a
block or entity refers to actually resolves, and that everything with a display
name has a matching language key. Anything it cannot resolve inside More Create
is looked up in the Create addon, which is a hard dependency.
"""

import json
import os
import re
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "packs/behavior")
RP = os.path.join(ROOT, "packs/resource")

errors = []
warnings = []
notes = []


def fail(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def load(path):
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle, object_pairs_hook=OrderedDict)


def walk_json(root):
    for base, _, files in os.walk(root):
        for name in sorted(files):
            if name.endswith(".json"):
                yield os.path.join(base, name)


def rel(path):
    return os.path.relpath(path, ROOT)


# ---------------------------------------------------------------- JSON syntax
documents = {}
for root in (BP, RP):
    for path in walk_json(root):
        try:
            documents[path] = load(path)
        except Exception as exc:
            fail("%s: invalid JSON - %s" % (rel(path), exc))

# ------------------------------------------------------------------ manifests
bp_manifest = documents.get(os.path.join(BP, "manifest.json"))
rp_manifest = documents.get(os.path.join(RP, "manifest.json"))

CREATE_BP_UUID = "12cf12b5-b9b9-4d0e-987a-f22936bd0692"
CREATE_RP_UUID = "ae049fa3-1bcf-4906-afcd-f25c36885bff"

if bp_manifest and rp_manifest:
    uuids = []
    for manifest, label in ((bp_manifest, "behaviour"), (rp_manifest, "resource")):
        uuids.append(manifest["header"]["uuid"])
        uuids += [m["uuid"] for m in manifest["modules"]]
        engine = manifest["header"].get("min_engine_version")
        if engine != [1, 26, 13]:
            fail("%s manifest: min_engine_version is %s, expected [1, 26, 13]" % (label, engine))
    if len(set(uuids)) != len(uuids):
        fail("duplicate UUIDs across manifests: %s" % uuids)

    bp_deps = {d.get("uuid") for d in bp_manifest.get("dependencies", [])}
    rp_deps = {d.get("uuid") for d in rp_manifest.get("dependencies", [])}
    if rp_manifest["header"]["uuid"] not in bp_deps:
        fail("behaviour manifest does not depend on the More Create resource pack")
    if bp_manifest["header"]["uuid"] not in rp_deps:
        fail("resource manifest does not depend on the More Create behaviour pack")
    if CREATE_BP_UUID not in bp_deps:
        fail("behaviour manifest does not depend on the Create behaviour pack")
    if CREATE_RP_UUID not in rp_deps:
        fail("resource manifest does not depend on the Create resource pack")

    script_module = next((m for m in bp_manifest["modules"] if m["type"] == "script"), None)
    if not script_module:
        fail("behaviour manifest has no script module")
    else:
        entry = os.path.join(BP, script_module["entry"])
        if not os.path.isfile(entry):
            fail("script entry point missing: %s" % script_module["entry"])

# ------------------------------------------------------------------ our atlases
own_terrain, own_items = set(), set()
terrain_path = os.path.join(RP, "textures/terrain_texture.json")
if terrain_path in documents:
    for key, value in documents[terrain_path]["texture_data"].items():
        own_terrain.add(key)
        textures = value["textures"]
        for tex in ([textures] if isinstance(textures, str) else textures):
            tex = tex if isinstance(tex, str) else tex.get("path", "")
            if not os.path.isfile(os.path.join(RP, tex + ".png")):
                fail("terrain_texture %s -> missing file %s.png" % (key, tex))

items_path = os.path.join(RP, "textures/item_texture.json")
if items_path in documents:
    for key, value in documents[items_path]["texture_data"].items():
        own_items.add(key)
        tex = value["textures"]
        tex = tex if isinstance(tex, str) else tex[0]
        if not os.path.isfile(os.path.join(RP, tex + ".png")):
            fail("item_texture %s -> missing file %s.png" % (key, tex))

# --------------------------------------------------- Create's atlases (dependency)
create_terrain, create_items, create_geometry, create_textures = set(), set(), set(), set()
create_rp = os.environ.get("CREATE_RP")
if create_rp and os.path.isdir(create_rp):
    def relaxed(path):
        text = open(path, encoding="utf-8-sig").read()
        text = re.sub(r"//[^\n]*", "", text)          # the Create pack uses comments
        text = re.sub(r",(\s*[}\]])", r"\1", text)
        return json.loads(text)

    for name, bucket in (("terrain_texture.json", create_terrain), ("item_texture.json", create_items)):
        candidate = os.path.join(create_rp, "textures", name)
        if os.path.isfile(candidate):
            try:
                bucket.update(relaxed(candidate)["texture_data"].keys())
            except Exception as exc:
                warn("could not read Create %s: %s" % (name, exc))
    for base, _, files in os.walk(create_rp):
        for name in files:
            if name.endswith(".json"):
                try:
                    text = open(os.path.join(base, name), encoding="utf-8-sig").read()
                except Exception:
                    continue
                create_geometry.update(re.findall(r'"(geometry\.[A-Za-z0-9_.]+)"', text))
            elif name.endswith(".png"):
                p = os.path.relpath(os.path.join(base, name), create_rp)
                create_textures.add(p[:-4].replace(os.sep, "/"))
else:
    notes.append("CREATE_RP not set - references into the Create pack were not verified")

# --------------------------------------------------------------- our geometries
own_geometry = set()
for path, doc in documents.items():
    if not path.startswith(os.path.join(RP, "models")):
        continue
    for geo in doc.get("minecraft:geometry", []):
        ident = geo.get("description", {}).get("identifier")
        if ident:
            own_geometry.add(ident)

VANILLA_GEOMETRY_PREFIX = "minecraft:geometry."


def texture_known(key, atlas):
    if atlas == "terrain":
        return key in own_terrain or key in create_terrain or not create_terrain
    return key in own_items or key in create_items or not create_items


def geometry_known(ident):
    if ident.startswith(VANILLA_GEOMETRY_PREFIX):
        return True
    return ident in own_geometry or ident in create_geometry or not create_geometry


# ------------------------------------------------------------------- blocks
block_ids, item_ids, entity_ids = set(), set(), set()
for path, doc in documents.items():
    if not isinstance(doc, dict):
        continue
    block = doc.get("minecraft:block")
    if not block:
        continue
    ident = block["description"]["identifier"]
    block_ids.add(ident)

    def check_components(components, where):
        geo = components.get("minecraft:geometry")
        if isinstance(geo, str) and not geometry_known(geo):
            fail("%s: unknown geometry %s" % (where, geo))
        elif isinstance(geo, dict):
            gid = geo.get("identifier")
            if gid and not geometry_known(gid):
                fail("%s: unknown geometry %s" % (where, gid))
        materials = components.get("minecraft:material_instances", {})
        for face, spec in materials.items():
            tex = spec.get("texture") if isinstance(spec, dict) else None
            if tex and not texture_known(tex, "terrain"):
                fail("%s: material_instances[%s] -> unknown terrain texture %s" % (where, face, tex))
        particles = components.get("minecraft:destruction_particles", {})
        tex = particles.get("texture") if isinstance(particles, dict) else None
        if tex and not texture_known(tex, "terrain"):
            fail("%s: destruction_particles -> unknown terrain texture %s" % (where, tex))
        loot = components.get("minecraft:loot")
        if isinstance(loot, str) and not os.path.isfile(os.path.join(BP, loot)):
            fail("%s: loot table missing - %s" % (where, loot))

    check_components(block.get("components", {}), ident)
    for index, perm in enumerate(block.get("permutations", [])):
        check_components(perm.get("components", {}), "%s permutation[%d]" % (ident, index))

# -------------------------------------------------------------------- items
for path, doc in documents.items():
    if not isinstance(doc, dict):
        continue
    item = doc.get("minecraft:item")
    if not item:
        continue
    ident = item["description"]["identifier"]
    item_ids.add(ident)
    icon = item.get("components", {}).get("minecraft:icon")
    if isinstance(icon, dict):
        icon = icon.get("texture") or icon.get("textures")
    if isinstance(icon, str) and not texture_known(icon, "items"):
        fail("%s: icon -> unknown item texture %s" % (ident, icon))

# ----------------------------------------------------------------- entities
for path, doc in documents.items():
    if not isinstance(doc, dict):
        continue
    entity = doc.get("minecraft:entity")
    if entity:
        entity_ids.add(entity["description"]["identifier"])

client_entities = {}
for path, doc in documents.items():
    if not isinstance(doc, dict):
        continue
    client = doc.get("minecraft:client_entity")
    if not client:
        continue
    desc = client["description"]
    client_entities[desc["identifier"]] = desc
    for key, geo in desc.get("geometry", {}).items():
        if not geometry_known(geo):
            fail("client entity %s: unknown geometry %s" % (desc["identifier"], geo))
    for key, tex in desc.get("textures", {}).items():
        if create_textures and tex not in create_textures and \
                not os.path.isfile(os.path.join(RP, tex + ".png")):
            fail("client entity %s: missing texture %s.png" % (desc["identifier"], tex))

for ident in sorted(entity_ids):
    if ident not in client_entities:
        fail("entity %s has no client entity definition in the resource pack" % ident)
for ident in sorted(client_entities):
    if ident not in entity_ids:
        warn("client entity %s has no behaviour definition" % ident)

# ---------------------------------------------------------------- recipes
for path, doc in documents.items():
    if not isinstance(doc, dict):
        continue
    for key in ("minecraft:recipe_shaped", "minecraft:recipe_shapeless"):
        recipe = doc.get(key)
        if not recipe:
            continue
        result = recipe.get("result")
        results = result if isinstance(result, list) else [result]
        for entry in results:
            rid = entry.get("item")
            if rid and rid.startswith("morecreate:") and rid not in block_ids | item_ids:
                fail("%s: result %s is not defined by this pack" % (rel(path), rid))

# -------------------------------------------------------------- language keys
lang_path = os.path.join(RP, "texts/en_US.lang")
lang_keys = set()
if os.path.isfile(lang_path):
    for line in open(lang_path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        lang_keys.add(line.split("=", 1)[0].strip())
else:
    fail("resource pack has no texts/en_US.lang")

for ident in sorted(block_ids):
    key = "tile.%s.name" % ident
    if key not in lang_keys:
        fail("missing language key %s" % key)

for path, doc in documents.items():
    if not isinstance(doc, dict):
        continue
    item = doc.get("minecraft:item")
    if not item:
        continue
    ident = item["description"]["identifier"]
    display = item.get("components", {}).get("minecraft:display_name")
    key = display.get("value") if isinstance(display, dict) else None
    key = key or ("item.%s" % ident)
    if key not in lang_keys:
        fail("missing language key %s (for %s)" % (key, ident))

# ------------------------------------------------------------- script imports
script_root = os.path.join(BP, "scripts")
for base, _, files in os.walk(script_root):
    for name in files:
        if not name.endswith(".js"):
            continue
        path = os.path.join(base, name)
        text = open(path, encoding="utf-8").read()
        for match in re.finditer(r'from\s+["\'](\.[^"\']+)["\']|import\s+["\'](\.[^"\']+)["\']', text):
            target = match.group(1) or match.group(2)
            resolved = os.path.normpath(os.path.join(base, target))
            if not os.path.isfile(resolved) and not os.path.isfile(resolved + ".js"):
                fail("%s: unresolved import %s" % (rel(path), target))

# ------------------------------------------------------------------- summary
print("blocks: %d   items: %d   entities: %d   geometries: %d"
      % (len(block_ids), len(item_ids), len(entity_ids), len(own_geometry)))
print("json documents: %d" % len(documents))
for note in notes:
    print("note: " + note)
for w in warnings:
    print("warning: " + w)
for e in errors:
    print("ERROR: " + e)
print("\n%s" % ("FAILED (%d error(s))" % len(errors) if errors else "OK"))
sys.exit(1 if errors else 0)
