# More Create

An add-on for the **Create** Bedrock addon by Vatonage that adds features missing from Bedrock Create.

- **Author:** Usersainyy
- **Requires:** Minecraft Bedrock **1.26.13 or newer**, and Vatonage's Create addon (behaviour + resource pack) enabled in the same world.
- **Download:** [`dist/MoreCreate.mcaddon`](dist/MoreCreate.mcaddon)

More Create never imports from the Create pack. Everything is registered through
Create's **Compatibility API v2** over script events, so the two packs stay
independent and More Create simply does nothing if Create is missing.

---

## What it adds

### 1. Missing processing recipes — 115 in total

Produced by diffing Create 1.21.1's recipe data against the tables built into
the Bedrock addon, then dropping anything whose items do not exist on Bedrock.

| Machine | Added | Notes |
|---|---:|---|
| Crushing Wheels | 46 | The decorative stone family (asurine, crimsite, ochrum, veridium, tuff, diorite and all their cut/brick/stair variants) shipped as blocks but could not be crushed. Plus zinc ore, deepslate zinc ore, gilded blackstone, nether wart block, prismarine crystals and tuff. |
| Crushing Wheels (milling fallback) | 56 | In Create a wheel runs a Millstone recipe when the item has no crushing recipe. Bedrock's wheel only ever checked crushing recipes, so every Millstone recipe without a crushing counterpart was unusable in a wheel. |
| Millstone | 4 | Pink petals, pitcher plant, torchflower, terracotta. |
| Mechanical Press | 6 | Dirt, coarse dirt, rooted dirt, mycelium, podzol and grass block → dirt path. |
| Bulk Washing (fan + water) | 2 | Industrial iron block / window → weathered variants. |
| **Bug fix** | 1 | Washing Crushed Raw Copper produced `create:copper_nugget`, an item the addon never defines, so the recipe silently yielded nothing. It now returns one copper ingot (the nine nuggets Create gives are worth exactly that) plus the usual clay ball chance. |

Bulk smelting/melting, bulk smoking and bulk haunting were already complete in
the Bedrock addon — the diff found nothing missing there.

### 2. Encased Chain Drive

Faithful to Create: drives relay rotation to each other in a row, everything in
that row turns the **same** direction at 1:1, and any drive in the row may be
rotated 90°. They connect on their four side faces only — an axis face can
never mate with a side face — and the two axis faces are ordinary shaft ports.

**Crafting (shapeless):** Andesite Casing + 3 × Iron Nugget, **or** Andesite
Casing + 3 × Zinc Nugget.

### 3. Hiding shafts and cogwheels inside casings

Right-click a shaft, cogwheel or large cogwheel with **any** casing —
andesite, brass, copper or creative — and it becomes an encased block.

- **Encased shaft** — a solid, full casing block. The shaft is hidden
  *completely*; there is nothing left to see. Rotation and stress keep flowing
  through it exactly as before.
- **Encased cogwheel / large cogwheel** — the casing slices through the middle,
  hiding the hub and the through-shaft, leaving only the outer tooth ring
  showing and still turning.

This is also a genuine optimisation. Create draws shafts as an *invisible*
block with a visual entity on top; an encased shaft is registered with
`noEntity`, so that entity is never spawned. Every shaft you encase is one
fewer entity in the world.

Other interactions:

- Right-click an encased block with a **different** casing to swap the material — the old casing is returned.
- **Sneak + right-click with a Wrench** to take the casing back off.
- Breaking an encased block always drops both the kinetic part and its casing, so the casing material is never lost.

### 4. Schematic Cannon

The Create Cannon / Schematic addon, integrated into More Create and fully
translated to English:

- Schematic Cannon, cannon base and Schematic Table
- Schematic & Quill, Empty Schematic, Schematic, Material Clipboard and the Cannon Guide
- Every menu, message and item name translated from Portuguese; the old
  Portuguese/Spanish/English language picker is gone and the guide is English only
- Ported from `@minecraft/server` 1.x / `server-ui` 1.x to the 2.x APIs this pack
  targets (13 form calls updated to the options-object signatures, `GameMode`
  enum casing fixed)
- Everything renamed out of `cannon_rp:` into `morecreate:`, generic geometry
  names namespaced, and textures moved out of the vanilla `textures/items` and
  `textures/blocks` folders so nothing can collide with another pack
- The addon's own `pack_icon.png` was dropped, as requested
- Two broken item-atlas entries fixed (they pointed at files that did not exist)
- The Admin panel's "Reset all cannons" and "Delete all structures" buttons only
  printed a message in the original; they now actually do it

---

## Repository layout

```
packs/behavior/     More Create behaviour pack
packs/resource/     More Create resource pack
tools/              generators, validator and the packager
dist/               built MoreCreate.mcaddon
```

### Tools

| Command | Purpose |
|---|---|
| `python3 tools/gen_encased.py` | Regenerates the 12 encased blocks and their loot tables |
| `python3 tools/gen_recipes.py tools/data/gap_report.json tools/data/be_recipes.json` | Regenerates the missing-recipe tables |
| `python3 tools/port_cannon.py <extracted cannon addon>` | Re-runs the cannon asset port |
| `CREATE_RP=<path to Create RP> python3 tools/validate.py` | Checks JSON, manifests, textures, geometry, lang keys and script imports |
| `python3 tools/build.py` | Builds `dist/MoreCreate.mcaddon` |

`tools/data/` holds the recipe diff the generator consumes, so the recipe
tables can be rebuilt without the original Create jar to hand.

## Installing

1. Enable Vatonage's **Create** behaviour and resource packs on the world.
2. Open `MoreCreate.mcaddon` to import it, then enable both More Create packs on
   the same world.
3. More Create must be **below** Create in the behaviour pack order so Create's
   compatibility bridge is listening when More Create registers.

If the registrations go unanswered, More Create logs a warning to the content
log naming the likely cause.

## Credits

- **Create** (Bedrock) by Vatonage — the base addon this extends.
- **Create** (Java) by the Create team — the source of the recipe data and the chain drive model and textures.
- Cannon / Schematic addon by Reversy Player — integrated and translated here.
