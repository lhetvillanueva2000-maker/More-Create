# More Create

An add-on for the **Create** Bedrock addon by Vatonage that adds features missing from Bedrock Create.

- **Author:** Usersainyy
- **Requires:** Minecraft Bedrock **1.26.13 or newer**, and Vatonage's Create addon (behaviour + resource pack) enabled in the same world.
- **Download:** [`dist/MoreCreate-v1.7.mcaddon`](dist/MoreCreate-v1.7.mcaddon) — every version is listed in [CHANGELOG.md](CHANGELOG.md)

More Create never imports from the Create pack. Everything is registered through
Create's **Compatibility API v2** over script events, so the two packs stay
independent and More Create simply does nothing if Create is missing.

---

## What it adds

### 1. Missing recipes — 703 in total

Produced by diffing every recipe folder in Create 1.21.1 against the tables and
recipe files built into the Bedrock addon, then dropping anything whose items do
not exist on Bedrock.

**Through Create's Compatibility API (116)**

| Machine | Added | Notes |
|---|---:|---|
| Crushing Wheels | 46 | The decorative stone family (asurine, crimsite, ochrum, veridium, tuff, diorite and all their cut/brick/stair variants) shipped as blocks but could not be crushed. Plus zinc ore, deepslate zinc ore, gilded blackstone, nether wart block, prismarine crystals and tuff. |
| Crushing Wheels (milling fallback) | 56 | In Create a wheel runs a Millstone recipe when the item has no crushing recipe. Bedrock's wheel only ever checked crushing recipes, so every Millstone recipe without a crushing counterpart was unusable in a wheel. |
| Millstone | 4 | Pink petals, pitcher plant, torchflower, terracotta. |
| Mechanical Press | 6 | Dirt, coarse dirt, rooted dirt, mycelium, podzol and grass block → dirt path. |
| Bulk Washing (fan + water) | 2 | Industrial iron block / window → weathered variants. |
| **Mechanical Crafter** | 1 | **The Crushing Wheel.** It had no recipe anywhere in the Bedrock addon — not on the crafting table, not in the crafter. The crafter's own matcher already handles 5×5 patterns (its code comments even name the wheel), so only the recipe was missing. |
| **Bug fix** | 1 | Washing Crushed Raw Copper produced `create:copper_nugget`, an item the addon never defines, so the recipe silently yielded nothing. It now returns one copper ingot (the nine nuggets Create gives are worth exactly that) plus the usual clay ball chance. |

**As ordinary Bedrock recipe files (587)** — these need no Create hook at all:

| Type | Added | Notes |
|---|---:|---|
| **Stonecutter** | 581 | Create wires each stone family as an any-to-any web through item tags — any andesite block cuts into any other andesite variant. Bedrock had 162 of those pairs; this adds the remaining 581, covering 113 result blocks across all 14 stone families. |
| Furnace / blast furnace | 3 | Zinc Ore and Raw Zinc could not be smelted into Zinc Ingots. |
| Crafting table | 3 | Chain from zinc, Dough from flour + water bucket, Minecart back from a Minecart Contraption. |

The stonecutting recipes come from Create's 327 tag-driven entries. A Bedrock
stonecutter recipe takes one concrete ingredient, so each tag is expanded into
one recipe per source block, dropping blocks Bedrock does not have and pairs it
already covers.

Bulk smelting, bulk smoking, bulk haunting, mixing, spouting and sequenced
assembly were already complete — the diff found nothing missing in those.

#### Recipe types Create Bedrock offers no hook for

Create's Compatibility API exposes twelve machines. Six recipe types have no
hook, so nothing can register them from outside the Create pack — the Bedrock
deployer, for instance, keeps its recipes in a private `DEPLOY_RECIPES` table
that no script event can reach. These stay missing until Vatonage adds hooks:

| Type | In Create | Valid on Bedrock |
|---|---:|---:|
| Deploying | 167 | 38 |
| Compacting | 7 | 6 |
| Item application | 8 | 3 |
| Cutting (Mechanical Saw) | 2 | 2 |
| Sandpaper polishing | 1 | 1 |
| Emptying | 2 | 0 |

Writing More Create's own handlers for these would mean duplicating Create's
machine logic and risking double-processing, so they are deliberately left out.

Two more things from Create's data folder land in the same bucket:

- **Potato Cannon ammo.** Create defines 25 projectile types; Bedrock implements
  25 too, but seven of them differ — Blaze Cake, Chocolate Glazed Berries,
  Glistering Melon Slice, Honeyed Apple, Melon Block, Pumpkin and Suspicious
  Stew are Create ammo that Bedrock does not accept. Every one of those items
  exists on Bedrock, and the projectile's `create:ammo_type` property is even
  declared with room for 32 values while only 25 are used — but the ammo list is
  a private array in Create's `potatoCannon.js` with no hook, so nothing outside
  that pack can extend it.
- **Damage types.** Create ships nine (`crush`, `fan_fire`, `fan_lava`,
  `mechanical_saw`, `run_over` and so on). Bedrock add-ons have no data-driven
  damage-type system at all, so these have no equivalent.

### 2. Encased Chain Drive

**Where to find it:** Creative menu → **Items** tab → the **More Create:
Kinetics** group. Or craft it — the recipe shows in the recipe book.

**Crafting (shapeless):** Andesite Casing + 3 × Iron Nugget, **or** Andesite
Casing + 3 × Zinc Nugget.

Faithful to Create: drives relay rotation to each other in a row, everything in
that row turns the **same** direction at 1:1, and any drive in the row may be
rotated 90°. They connect on their four side faces only — an axis face can
never mate with a side face — and the two axis faces are ordinary shaft ports.

The important part is that a chain drive **never reverses rotation**. A row of
cogwheels flips direction at every mesh; a row of chain drives does not, so
speed and direction stay identical however long the run gets. That is set by
`sense: "equal"` with `ratio: 1` on the four side faces, and by leaving the
faces without an alignment constraint so a drive can be turned 90° mid-row.

Replaying the config through Create's own connection logic:

| Case | Result |
|---|---|
| drive → drive, parallel row | `sense=equal ratio=1` |
| drive → drive, rotated 90° | `sense=equal ratio=1` |
| drive → drive, axis to axis | `sense=equal ratio=1` |
| drive side → cogwheel side | rejected, no connection |

**How it is drawn.** The block is not a cube with one texture per face — it
carries Create's own six models, converted to Bedrock geometry straight from the
jar. That matters because Create rotates the casing texture per face (the metal
strip runs *around* the block) and tells the two ends of a run apart by turning
the model 180°, which is not the same as mirroring the texture. Bedrock UVs can
express a 180° turn but not 90°, so those are baked as pre-turned copies.
`tools/verify_chain_drive.py` checks all 116 faces against Java's own sampling,
pixel for pixel, so this cannot silently drift again.

### 3. Hiding shafts and cogwheels inside casings

Right-click a shaft, cogwheel or large cogwheel with **any** casing —
andesite, brass, copper or creative — and it becomes an encased block.

- **Encased shaft** — a solid, full casing block. The shaft is hidden
  *completely*; there is nothing left to see. Rotation and stress keep flowing
  through it exactly as before.
- **Encased cogwheel / large cogwheel** — the casing slices through the middle,
  hiding the hub and the through-shaft, leaving only the outer tooth ring
  showing and still turning. The casing carries Create's slotted
  `*_encased_cogwheel_side` texture, whose gap is **transparent** — you see the
  wheel itself turning through it, not a painted-on band. Create only ships that
  art for andesite and brass; copper and creative derive the same slot as a
  per-pixel darkening ratio, so all four match while keeping their own colour.

This is also a genuine optimisation. Create draws shafts as an *invisible*
block with a visual entity on top; an encased shaft is registered with
`noEntity`, so that entity is never spawned. Every shaft you encase is one
fewer entity in the world.

Other interactions:

- Right-click an encased block with a **different** casing to swap the material — the old casing is returned.
- **Sneak + right-click with a Wrench** to take the casing back off.
- Breaking an encased block always drops both the kinetic part and its casing, so the casing material is never lost.

### 4. Recipe Book

**Crafting (shapeless):** Book + Andesite Alloy.

Bedrock has no recipe browser for script-driven machines, so Create's processing
recipes are invisible unless you already know them. The book lists **all 400** —
Create's own and More Create's together — grouped by machine:

| Machine | Recipes |
|---|---:|
| Crushing Wheels | 94 |
| Bulk Smelting | 87 |
| Bulk Washing | 76 |
| Millstone | 63 |
| Bulk Haunting | 30 |
| Mechanical Press | 15 |
| Mechanical Mixer | 13 |
| Spout | 12 |
| Bulk Smoking | 10 |

Each machine page names the setup it needs ("Encased Fan blowing through a water
source onto the items") and lists every input with its outputs and drop chances.
There is also a **search**, which finds every machine that uses or produces a
given item — searching `gravel` answers all three at once:

```
Crushing Wheels   Gravel  ->  Sand, Flint (25%)
Millstone         Gravel  ->  Flint
Bulk Washing      Gravel  ->  Flint (25%), Iron Nugget (13%)
```

### 5. Recipe Browser — not currently shipped

v1.6 added a JEI-style browser opened from a button on the pause menu. It is
**removed in v1.7**: the way it attached itself to the pause screen blanked that
screen entirely, so pausing showed an empty menu with no way out of the world.

The cause was the entry point, not the browser. Bedrock's JSON UI cannot call a
script, so a pause-menu button has to be added by patching the vanilla
`pause_screen_content` control. More Create did that from its own file with
`"namespace": "pause"`, hoping the patch would merge. Instead it *replaced* the
vanilla control with one that has no content, and a control with no content
draws nothing.

The generators are still here (`tools/gen_browser_ui.py`,
`tools/gen_browser_textures.py`, `tools/icons.py`) because the browser itself was
fine — only its door was wrong. Re-adding it needs an entry point that cannot
touch a vanilla screen, most likely the container-title trick the Schematic
Cannon already uses. Until then the **Recipe Book** item lists the same 400
recipes.

### 6. Schematic Cannon

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

## Running alongside other Create add-ons

Checked against **Create New Energy** (`ne:`) and **Create Multiblock**
(`createmb:`) by indexing all 2,735 files across the five packs and looking for
paths that would override each other.

More Create is clear of both:

- its ids all live under `morecreate:`, which nothing else uses;
- its script entry is `scripts/morecreate/main.js`, not the usual
  `scripts/main.js`, so it cannot clash with another pack's scripts;
- the only files it shares with anything are `blocks.json`,
  `terrain_texture.json`, `item_texture.json`, `_ui_defs.json` and the item
  catalog — all of which Minecraft **merges** across packs rather than
  overriding.

One finding that is **not** about More Create: **New Energy and Multiblock both
ship their script entry at `scripts/main.js`.** Behaviour packs share one
merged filesystem, so if those two are enabled together only one of those files
survives and the other add-on's scripts may not run. Nothing More Create can fix
— it needs one of those two packs to move its entry point.

Suggested behaviour pack order (top = highest priority):

```
Create            <- must be above More Create
More Create
Create New Energy
Create Multiblock
```

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
| `python3 tools/gen_cogwheel_textures.py <jar textures> <Create casings>` | Regenerates the slotted casing textures, with a self-check against Create's art |
| `python3 tools/gen_cogwheel_geo.py <Create RP>` | Regenerates the encased cogwheel visual geometry |
| `python3 tools/analyze_gaps.py <Create jar dir> <Create BP dir>` | Re-diffs every Java recipe folder against Bedrock into `tools/data/gap_report_v2.json` |
| `python3 tools/gen_recipes.py tools/data/gap_report.json tools/data/be_recipes.json tools/data/gap_report_v2.json` | Regenerates the compatibility-API recipe tables |
| `python3 tools/gen_native_recipes.py tools/data/gap_report_v2.json` | Regenerates the plain Bedrock crafting and cooking recipe files |
| `python3 tools/port_cannon.py <extracted cannon addon>` | Re-runs the cannon asset port |
| `CREATE_RP=<path to Create RP> python3 tools/validate.py` | Checks JSON, manifests, textures, geometry, lang keys and script imports |
| `python3 tools/gen_chain_drive.py <Create jar assets/create>` | Ports Create's own chain drive models to Bedrock geometry, bakes the turned textures, and writes the block |
| `python3 tools/verify_chain_drive.py <Create jar assets/create>` | Proves every converted face samples the same pixels Create's model does |
| `python3 tools/gen_book.py tools/data/be_recipes.json tools/data/gap_report.json tools/data/be_recipes2.json` | Regenerates the Recipe Book's recipe table |
| `python3 tools/gen_browser_textures.py` | Draws the Recipe Browser's chrome — round pause button, panel, slots, arrow, tabs |
| `python3 tools/gen_browser_ui.py <Create RP> <Create BP>` | Regenerates the Recipe Browser's JSON UI from the book's recipe table |
| `python3 tools/build.py` | Builds `dist/MoreCreate-v<VERSION>.mcaddon` (bump `VERSION` in the script) |
| `python3 tools/gen_release_notes.py` | Splits `CHANGELOG.md` into `dist/release-notes/v*.md` and regenerates `tools/publish_releases.sh` |
| `bash tools/publish_releases.sh` | Publishes every built version to the repository's Releases tab (needs the GitHub CLI) |

`tools/data/` holds the recipe diff the generator consumes, so the recipe
tables can be rebuilt without the original Create jar to hand.
`tools/data/vanilla/` holds Mojang's own atlas listings, which is how the
browser knows where a vanilla item's texture lives; they are build-time
reference only and are never shipped inside a pack.

## Releases

Every version is on the
[Releases tab](https://github.com/lhetvillanueva2000-maker/More-Create/releases)
with its `.mcaddon` attached, and the same files are in [`dist/`](dist/).

Publishing is handled by `.github/workflows/publish-releases.yml`, which runs
`tools/publish_releases.sh` inside GitHub Actions. Each release takes its title
and notes from the matching section of `CHANGELOG.md`, and its tag points at the
commit that actually added that build rather than at the branch head.

The workflow exists because the automation that develops this repository can
push commits but cannot create releases — tag pushes are refused with HTTP 403,
`api.github.com/repos/*` is blocked at its proxy, and its GitHub tooling can only
read releases. Actions runs with the repository's own token, which has
`contents: write`, so it can.

To publish a new version: bump `VERSION` in `tools/build.py`, build, add the
section to `CHANGELOG.md`, then

```
python3 tools/gen_release_notes.py
```

and push. Changing `dist/release-notes/` triggers the workflow, which skips every
version that already has a release. It can also be run by hand from the Actions
tab, or locally with `gh auth login && bash tools/publish_releases.sh`.

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
