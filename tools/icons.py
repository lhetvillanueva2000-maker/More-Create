#!/usr/bin/env python3
"""Resolve an item or block identifier to the texture path the UI can draw.

Bedrock's JSON UI can only draw a texture path - there is no "render this item
id" control outside a real container screen - so the recipe browser needs a
lookup from `create:zinc_ingot` to `textures/create/common/items/zinc_ingot`.

Four sources, tried in order:

    1. `item_texture.json` keyed by the full identifier (Create's own items,
       and More Create's).
    2. The block definition's `material_instances`, resolved through
       `terrain_texture.json` (block items draw their block's texture).
    3. Vanilla `blocks.json` -> `terrain_texture.json` (vanilla blocks).
    4. Vanilla `item_texture.json` keyed by the short name, with the handful of
       names where the texture key and the item id disagree patched by hand.

Anything still unresolved falls back to a neutral slot texture, so a missing
entry shows an empty slot rather than the pink "missing texture" checkerboard.
"""

import json
import os
import re

FALLBACK = "textures/morecreate/ui/unknown_item"

# Item ids whose vanilla texture key is not simply the id.
VANILLA_ALIASES = {
    "cobweb": "web",
    "sugar_cane": "reeds",
    "gunpowder": "sulphur",
    "lily_pad": "waterlily",
    "melon_slice": "melon",
    "dye": "dye_powder",
    "cooked_porkchop": "porkchop_cooked",
    "porkchop": "porkchop_raw",
    "cooked_beef": "beef_cooked",
    "beef": "beef_raw",
    "cooked_chicken": "chicken_cooked",
    "chicken": "chicken_raw",
    "cooked_mutton": "mutton_cooked",
    "mutton": "mutton_raw",
    "cooked_rabbit": "rabbit_cooked",
    "rabbit": "rabbit_raw",
    "cooked_cod": "fish_cooked",
    "cod": "fish_raw",
    "cooked_salmon": "salmon_cooked",
    "salmon": "salmon_raw",
    "tropical_fish": "clownfish_raw",
    "pufferfish": "pufferfish_raw",
    "golden_apple": "apple_golden",
    "enchanted_golden_apple": "apple_golden",
    "poisonous_potato": "potato_poisonous",
    "baked_potato": "potato_baked",
    "nether_wart": "nether_wart",
    "glistering_melon_slice": "melon_speckled",
    "ender_eye": "ender_eye",
    "ender_pearl": "ender_pearl",
    "blaze_powder": "blaze_powder",
    "brick": "brick",
    "nether_brick": "netherbrick",
    "clay_ball": "clay_ball",
    "snowball": "snowball",
    "slime_ball": "slimeball",
    "raw_iron": "raw_iron",
    "raw_gold": "raw_gold",
    "raw_copper": "raw_copper",
    "experience_bottle": "experience_bottle",
    "glass_bottle": "potion_bottle_empty",
    "potion": "potion_bottle_drinkable",
    "wheat": "wheat",
    "beetroot": "beetroot",
    "short_grass": "tallgrass",
    "grass": "tallgrass",
    "tall_grass": "double_plant_grass_carried",
    "large_fern": "double_plant_fern_carried",
    "fern": "fern_carried",
    "sweet_berries": "sweet_berries",
    "glow_berries": "glow_berries",
    "cocoa_beans": "dye_powder_brown",
    "ink_sac": "dye_powder_black",
    "lapis_lazuli": "dye_powder_blue",
    "bone_meal": "dye_powder_white",
}

# Identifiers with no usable atlas entry, or whose atlas entry is a frame list
# JSON UI cannot index. Straight to the file, which is what the UI wants anyway.
DIRECT = {
    "minecraft:bone_meal": "textures/items/dye_powder_white",
    "minecraft:cocoa_beans": "textures/items/dye_powder_brown",
    "minecraft:ink_sac": "textures/items/dye_powder_black",
    "minecraft:glow_ink_sac": "textures/items/dye_powder_glow",
    "minecraft:lapis_lazuli": "textures/items/dye_powder_blue",
    "minecraft:redstone": "textures/items/redstone_dust",
    "minecraft:water_bucket": "textures/items/bucket_water",
    "minecraft:lava_bucket": "textures/items/bucket_lava",
    "minecraft:milk_bucket": "textures/items/bucket_milk",
    "minecraft:beetroot_seeds": "textures/items/seeds_beetroot",
    "minecraft:wheat_seeds": "textures/items/seeds_wheat",
    "minecraft:cod": "textures/items/fish_raw",
    "minecraft:cooked_cod": "textures/items/fish_cooked",
    "minecraft:popped_chorus_fruit": "textures/items/chorus_fruit_popped",
    "minecraft:grass_block": "textures/blocks/grass_side_carried",
    "minecraft:dirt_path": "textures/blocks/grass_path_top",
    "minecraft:rooted_dirt": "textures/blocks/dirt_with_roots",
    "minecraft:terracotta": "textures/blocks/hardened_clay",
    "minecraft:nether_bricks": "textures/blocks/nether_brick",
    # Create's own item, which More Create redirects to a copper ingot; the
    # nugget art is vanilla's.
    "create:copper_nugget": "textures/items/copper_nugget",
    # Haunting outputs Create carried over from Java without adding the items.
    # Nothing can drop them in Bedrock, but they still show in the table.
    "create:haunted_bell": "textures/blocks/bell_side",
    "create:peculiar_bell": "textures/blocks/bell_side",
}

# Colour-indexed vanilla dyes: the atlas key is one entry with 16 frames, which
# JSON UI cannot index, so each dye gets its own explicit texture path.
DYE_TEXTURES = {
    "white": "dye_powder_white", "orange": "dye_powder_orange",
    "magenta": "dye_powder_magenta", "light_blue": "dye_powder_light_blue",
    "yellow": "dye_powder_yellow", "lime": "dye_powder_lime",
    "pink": "dye_powder_pink", "gray": "dye_powder_gray",
    "light_gray": "dye_powder_silver", "cyan": "dye_powder_cyan",
    "purple": "dye_powder_purple", "blue": "dye_powder_blue",
    "brown": "dye_powder_brown", "green": "dye_powder_green",
    "red": "dye_powder_red", "black": "dye_powder_black",
}


def load_json(path):
    """Read Bedrock JSON: BOM, // comments and trailing commas all appear."""
    raw = open(path, encoding="utf-8-sig").read()
    raw = re.sub(r'^\s*//[^\n]*', '', raw, flags=re.M)
    raw = re.sub(r',(\s*[}\]])', r'\1', raw)
    return json.loads(raw)


def _first_texture(value):
    """`textures` may be a string, a list of frames, or a per-face map."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # Tinted terrain entries are {"path": ..., "overlay_color": ...}.
        if "path" in value:
            return value["path"]
        for face in ("up", "side", "north", "*", "down"):
            if face in value:
                return _first_texture(value[face])
        for nested in value.values():
            found = _first_texture(nested)
            if found:
                return found
        return None
    if isinstance(value, list) and value:
        return _first_texture(value[0])
    return None


class IconIndex:
    """Every identifier -> texture path lookup the browser needs."""

    def __init__(self):
        self.items = {}       # full identifier -> path
        self.terrain = {}     # terrain key -> path
        self.blocks = {}      # block identifier -> terrain key
        self.short_items = {} # short texture key -> path
        self.roots = []       # pack roots, for checking a texture's real size

    # -- loading -----------------------------------------------------------

    def add_item_texture(self, path, short=False):
        data = load_json(path).get("texture_data", {})
        for key, entry in data.items():
            texture = _first_texture(entry.get("textures"))
            if not texture:
                continue
            self.items[key] = texture
            if short:
                self.short_items[key] = texture

    def add_terrain_texture(self, path):
        data = load_json(path).get("texture_data", {})
        for key, entry in data.items():
            texture = _first_texture(entry.get("textures"))
            if texture:
                self.terrain[key] = texture

    def add_vanilla_blocks(self, path):
        for key, entry in load_json(path).items():
            if not isinstance(entry, dict):
                continue
            textures = entry.get("textures")
            picked = _first_texture(textures)
            if picked:
                self.blocks["minecraft:" + key] = picked

    def add_custom_blocks(self, root):
        """Read `material_instances` out of every custom block in a pack."""
        for base, _dirs, files in os.walk(root):
            for name in files:
                if not name.endswith(".json"):
                    continue
                try:
                    doc = load_json(os.path.join(base, name))
                except Exception:
                    continue
                block = doc.get("minecraft:block") if isinstance(doc, dict) else None
                if not isinstance(block, dict):
                    continue
                identifier = block.get("description", {}).get("identifier")
                if not identifier:
                    continue
                components = block.get("components", {})
                instances = components.get("minecraft:material_instances")
                picked = None
                if isinstance(instances, dict):
                    for face in ("up", "*", "north", "side", "down"):
                        entry = instances.get(face)
                        if isinstance(entry, dict) and entry.get("texture"):
                            picked = entry["texture"]
                            break
                    if picked is None:
                        for entry in instances.values():
                            if isinstance(entry, dict) and entry.get("texture"):
                                picked = entry["texture"]
                                break
                if picked:
                    self.blocks.setdefault(identifier, picked)

    # -- lookup ------------------------------------------------------------

    def _on_disk(self, path):
        for root in self.roots:
            candidate = os.path.join(root, path + ".png")
            if os.path.exists(candidate):
                return candidate
        return None

    def _is_single_tile(self, path):
        """True unless the file is clearly a sheet rather than one icon.

        Connected-texture blocks point at a 64x64 sheet of sixteen corner
        pieces. Scaled into an 18px slot that is unreadable mush, so a sheet
        is a reason to look for the plain variant next door.
        """
        found = self._on_disk(path)
        if not found:
            return True  # a vanilla texture we cannot open; assume it is fine
        try:
            from PIL import Image
            width, height = Image.open(found).size
        except Exception:
            return True
        return width == height and width <= 32

    def refine(self, path):
        """Improve a resolved path: prefer a drawn icon, avoid atlas sheets."""
        if not path:
            return path

        # Create's pack ships hand-drawn 3D block icons for its own guide, keyed
        # by the vanilla texture name. They read far better in an 18px slot than
        # a flat block face, and they are already tinted, which the greyscale
        # foliage textures are not.
        if path.startswith("textures/blocks/"):
            base = path.rsplit("/", 1)[1]
            for folder in ("icons3d", "icons2d"):
                drawn = "textures/ui/crafters/%s/%s" % (folder, base)
                if self._on_disk(drawn):
                    return drawn

        if self._is_single_tile(path):
            return path
        candidates = []
        if path.endswith("_connected"):
            base = path[: -len("_connected")]
            candidates.append(base)
            candidates.append(re.sub(r"_\d+$", "", base))
        candidates.append(re.sub(r"_\d+$", "", path))
        for candidate in candidates:
            if candidate != path and self._on_disk(candidate) \
                    and self._is_single_tile(candidate):
                return candidate
        return path

    def resolve(self, identifier):
        """Texture path for an item id, or None when nothing matches."""
        if ":" not in identifier:
            identifier = "minecraft:" + identifier
        namespace, name = identifier.split(":", 1)

        if identifier in DIRECT:
            return DIRECT[identifier]
        if identifier in self.items:
            return self.items[identifier]

        key = self.blocks.get(identifier)
        if key:
            if key in self.terrain:
                return self.terrain[key]
            if key.startswith("textures/"):
                return key

        if namespace == "minecraft":
            if name.endswith("_dye") and name[:-4] in DYE_TEXTURES:
                return "textures/items/" + DYE_TEXTURES[name[:-4]]
            alias = VANILLA_ALIASES.get(name, name)
            # Some aliases name a terrain key rather than an item key - the
            # carried variants of grass and ferns, which are the tinted ones -
            # so try the alias against both atlases before falling back.
            if alias != name and alias in self.terrain:
                return self.terrain[alias]
            for candidate in (alias, name):
                if candidate in self.short_items:
                    return self.short_items[candidate]
            if name in self.terrain:
                return self.terrain[name]
        return None

    def resolve_or_fallback(self, identifier):
        return self.refine(self.resolve(identifier)) or FALLBACK


def build(create_rp, create_bp, vanilla_dir, extra_packs=()):
    """Index Create, vanilla and any extra packs (More Create's own)."""
    index = IconIndex()
    index.roots = [create_rp] + [rp for rp, _bp in extra_packs]
    index.add_item_texture(os.path.join(vanilla_dir, "vanilla_item_texture.json"), short=True)
    index.add_terrain_texture(os.path.join(vanilla_dir, "vanilla_terrain_texture.json"))
    index.add_vanilla_blocks(os.path.join(vanilla_dir, "vanilla_blocks.json"))

    index.add_item_texture(os.path.join(create_rp, "textures/item_texture.json"))
    index.add_terrain_texture(os.path.join(create_rp, "textures/terrain_texture.json"))
    index.add_custom_blocks(os.path.join(create_bp, "blocks"))

    for rp, bp in extra_packs:
        item_texture = os.path.join(rp, "textures/item_texture.json")
        terrain_texture = os.path.join(rp, "textures/terrain_texture.json")
        if os.path.exists(item_texture):
            index.add_item_texture(item_texture)
        if os.path.exists(terrain_texture):
            index.add_terrain_texture(terrain_texture)
        if bp and os.path.isdir(os.path.join(bp, "blocks")):
            index.add_custom_blocks(os.path.join(bp, "blocks"))
    return index
