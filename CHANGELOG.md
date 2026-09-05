# More Create — versions

Every build lives in [`dist/`](dist/). Download the `.mcaddon` for the version
you want and open it to import both packs.

Version numbers are `v<major>.<minor>`. The minor rolls into the major at ten,
so `v1.9` is followed by `v2.0`.

| Version | File | What it is |
|---|---|---|
| v1.3 | [`MoreCreate-v1.3.mcaddon`](dist/MoreCreate-v1.3.mcaddon) | Recipe Book, connected chain drives, slotted cogwheel casings, ghost-block fix |
| v1.2 | [`MoreCreate-v1.2.mcaddon`](dist/MoreCreate-v1.2.mcaddon) | 581 stonecutter recipes |
| v1.1 | [`MoreCreate-v1.1.mcaddon`](dist/MoreCreate-v1.1.mcaddon) | Crushing Wheel recipe, zinc smelting, full hook coverage |
| v1.0 | [`MoreCreate-v1.0.mcaddon`](dist/MoreCreate-v1.0.mcaddon) | First release |

---

## v1.0 — what More Create is

An add-on for the **Create** Bedrock addon by Vatonage that fills in features
missing from Bedrock Create. It talks to Create only through Create's own
Compatibility API v2, so the two packs stay independent and More Create simply
does nothing if Create is not installed.

This first version added:

- **115 missing processing recipes**, found by diffing Create 1.21.1's recipe
  data against the tables built into the Bedrock addon. Mostly Crushing Wheel
  recipes for the decorative stone family, which shipped as blocks that could
  not be crushed, plus the milling recipes a Crushing Wheel should fall back to.
- **Encased Chain Drive** — relays rotation along a row at 1:1 in the *same*
  direction, so a long run never reverses the way meshed cogwheels do. Crafted
  from an Andesite Casing and three iron or zinc nuggets.
- **Encasing shafts and cogwheels** — right-click a shaft, cogwheel or large
  cogwheel with any casing (andesite, brass, copper, creative) to hide it inside
  a solid block while rotation and stress keep flowing through. Because Create
  draws shafts as an invisible block with a visual entity on top, an encased
  shaft skips that entity entirely: the shaft disappears completely, and one
  entity per shaft goes with it.
- **Schematic Cannon** — the Cannon / Schematic addon integrated and fully
  translated to English, ported from `@minecraft/server` 1.x to 2.x.
- A **bug fix** in Create itself: washing Crushed Raw Copper produced
  `create:copper_nugget`, an item the addon never defines, so the recipe
  silently yielded nothing.

Requires Minecraft Bedrock **1.26.13** or newer.

---

## v1.1 — everything new

- **Crushing Wheels became craftable.** They had no recipe anywhere in the
  Bedrock addon — not on the crafting table, not in the Mechanical Crafter. The
  crafter already matched 5×5 patterns (its own code comments name the wheel);
  only the recipe was missing.
- **Zinc smelting** — Zinc Ore and Raw Zinc could not be smelted into Zinc
  Ingots in a furnace or blast furnace.
- **Three missing crafting recipes** — chain from zinc, dough from flour and a
  water bucket, and a minecart back from a Minecart Contraption.
- Re-diffed **every** recipe folder in Create, recursing into the nested
  category folders the first pass had missed. Spouting, sequenced assembly,
  mixing, bulk smelting, bulk smoking and bulk haunting were checked and found
  already complete.
- Verified the Encased Chain Drive by replaying its wiring through Create's own
  connection logic: `sense=equal, ratio=1` in every arrangement, parallel or
  rotated 90°, and it refuses to mesh with a cogwheel.
- Documented compatibility with **Create New Energy** and **Create Multiblock**
  after indexing all 2,735 files across the five packs.

Coverage after this version: 122 recipes.

---

## v1.2 — more added

- **581 stonecutter recipes.** Create wires each stone family as an any-to-any
  web through item tags — any andesite block cuts into any other andesite
  variant. Bedrock had 162 of those pairs; this adds the remaining 581 across
  113 result blocks and all 14 stone families (andesite, asurine, calcite,
  crimsite, deepslate, diorite, dripstone, granite, limestone, ochrum, scoria,
  scorchia, tuff, veridium).
- Found by spotting that **615 recipe files sit directly in Create's `recipe/`
  folder** rather than in a named category, which earlier passes never scanned.
- Checked the other 288 loose crafting recipes too: 190 produce items Bedrock
  does not have, 98 are already craftable, none were missing.

Coverage after this version: 703 recipes.

---

## v1.3 — fixes and the Recipe Book

- **Recipe Book.** A craftable book (book + andesite alloy) listing all **400**
  processing recipes in the game — Create's own and More Create's together —
  grouped by machine, with a search that finds every machine using a given item.
  No more guessing what a Crushing Wheel does with gravel.
- **Encased cogwheels now show the slot.** Create draws a dark gap across the
  casing where the wheel passes through, using dedicated
  `*_encased_cogwheel_side` textures. Andesite and brass use Create's own art;
  copper and creative are generated from the same slot so all four match.
  Encased shafts stay completely blank, as intended.
- **Chain drives connect visually.** A drive with a neighbour now shows the
  chain running across its sprocket face instead of a plain shaft hole, so a row
  reads as one continuous chain. The chain is drawn on the axis faces, which is
  where Create draws it — the faces where blocks touch are hidden between two
  solid blocks.
- **Ghost blocks fixed.** Visual entities could outlive their block when it was
  removed outside Create's own break path, leaving something that looked like an
  unbreakable block. Cleared on break, plus a sweep every ten seconds that
  removes any visual entity whose block is gone.
- **Last untranslated string.** The Schematic Table's dropdown still read
  "-- Nenhum Selecionado --"; it now reads "-- None Selected --".
