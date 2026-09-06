# More Create — versions

Every build lives in [`dist/`](dist/). Download the `.mcaddon` for the version
you want and open it to import both packs.

Version numbers are `v<major>.<minor>`. The minor rolls into the major at ten,
so `v1.9` is followed by `v2.0`.

| Version | File | What it is |
|---|---|---|
| v1.8 | [`MoreCreate-v1.8.mcaddon`](dist/MoreCreate-v1.8.mcaddon) | Pack version now bumps per release so updates install; chain drive rotation, seams and casing strip fixed |
| v1.7 | [`MoreCreate-v1.7.mcaddon`](dist/MoreCreate-v1.7.mcaddon) | Pause menu fixed; Recipe Book stops breaking blocks; chain drive ported from Create's own models |
| v1.6 | [`MoreCreate-v1.6.mcaddon`](dist/MoreCreate-v1.6.mcaddon) | Recipe Browser on the pause menu; chain drive facing, connected textures and item render fixed |
| v1.5 | [`MoreCreate-v1.5.mcaddon`](dist/MoreCreate-v1.5.mcaddon) | Cogwheel slot is see-through; copper and creative keep their colour |
| v1.4 | [`MoreCreate-v1.4.mcaddon`](dist/MoreCreate-v1.4.mcaddon) | Schematic Cannon screen fix |
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

---

## v1.4 — the Schematic Cannon screen

- **The cannon's screen opens again.** Its interface is the container of a
  hidden entity sitting inside the block — the same trick Create uses for its
  vault — but unlike Create's, that entity was never marked persistent, so the
  engine was free to remove it. Once it was gone, right-clicking the cannon did
  nothing at all and there was no way to get it back.

  The entity now carries `minecraft:persistent`, `minecraft:physics` and a type
  family, matching Create's own working vault anchor. On top of that,
  right-clicking a cannon that has lost its entity re-creates it — with its
  control buttons back in place — and a small sweep around each player repairs
  cannons in worlds saved before this fix.

- The fuel, schematic and output slots stay **empty** on placement, so you
  supply your own gunpowder and schematic. Only the control buttons are placed
  for you.

---

## v1.5 — the cogwheel slot, properly

Two defects in how v1.3 built the slotted casings, both found by inspecting the
textures pixel by pixel instead of trusting the preview.

- **Copper and creative had lost their colour.** The slot was made by pasting
  rows 2–13 of the andesite texture onto the other casings, which dragged
  andesite's brown across three quarters of the texture — copper kept only its
  top and bottom edge, so it barely read as copper at all. The slot is now taken
  as a per-pixel *ratio* of how much Create darkened its own andesite casing, and
  that ratio is applied to each casing, so every one keeps its own frame and body
  while getting an identical slot. A self-check confirms the derived slot
  reproduces Create's andesite art to the pixel.

- **The slot should be see-through, not black.** Create does not paint the gap
  dark — it punches it fully transparent, so the wheel turning inside is
  genuinely visible through it. The generated textures were opaque black there,
  and the blocks rendered `opaque`, so the gap read as a flat dark band. The
  slot is now transparent, those faces render with `alpha_test`, and the encased
  wheel keeps its hub and web (previously stripped as "hidden") because that is
  exactly what you now see through the gap. The disc sits at y 6.55–9.45, lining
  up with the slot rows.

Encased shafts are untouched and stay completely solid — hiding the shaft is the
whole point of them.

---

## v1.6 — the Recipe Browser, and the chain drive properly

### Recipe Browser

The Recipe Book from v1.3 read out 400 recipes as text. This adds a second way
to read the same 400, drawn the way a recipe browser should be: input slots, an
arrow, output slots, the drop chance printed on each output, and the
plain-language line underneath.

**Open it from the pause menu** — a round button carrying the pack icon, next to
Create's own guide button. Press it again to close it. Nine tabs across the top
pick the machine; the bigger machines split into numbered pages of forty.

Three things about Bedrock made this harder than it sounds, and each is worth
recording:

- **JSON UI cannot call a script.** A button on the pause menu has no way to
  open a script-driven form, so the browser is not one — all 400 rows are
  generated ahead of time and shipped as static JSON UI. Create's pack solves
  the same problem the same way for its own guide; the difference is Create
  hand-draws an image per recipe, while these rows are assembled from the real
  item textures.
- **JSON UI cannot draw an item id**, only a texture path. So all 408
  identifiers are resolved to a path at build time — through Create's
  `item_texture.json`, through Create's block definitions, and through Mojang's
  own `blocks.json` and `terrain_texture.json`. Where Create ships one of its
  drawn 3D block icons that is used instead, which also fixes the greyscale
  foliage textures that are meant to be tinted. Every resolved path was checked
  to exist; nothing falls back to a placeholder, and connected-texture sheets
  are swapped for the plain 16×16 tile beside them so a slot shows a block
  rather than sixteen corner pieces.
- **It does not touch Create's `ui/pause_screen.json`.** Create's entire guide
  lives in that file, and a second file at the same path could hide it
  depending on pack order. More Create instead adds to the `pause` namespace
  from its own `ui/morecreate/pause_patch.json`, registered through
  `ui/_ui_defs.json`. If the game does not pick that patch up, the only thing
  lost is our button — Create's guide is never at risk, and the Recipe Book item
  still opens the same recipes as text.

### Encased Chain Drive

- **The connected texture pointed the wrong way.** A drive with one neighbour
  drew its chain leaving the wrong edge, because the two faces showing the
  sprocket look at each other from opposite sides and were given the same
  texture. There are now four directional end textures — right, left, up, down —
  and each face takes the variant that sends the chain *toward* the neighbour.
  The generator verifies this by reading the pixels back out of each texture and
  reporting which edge the chain actually leaves.
- **Drives now face the player when placed**, like Create's own cogwheel, rather
  than facing the block face you clicked. Putting one down on the ground gives a
  horizontal drive instead of one standing on end.
- **The item render was wrong** — a bare cube with no shaft, lying on the wrong
  axis. It has its own model now, with the shaft stubs on and the axis matching
  the way the block lands when you place it.

### Recipes, triple-checked

Checked four independent ways, all passing:

1. Replayed every registration through Create's compatibility bridge — **129
   accepted, 0 rejected**.
2. Confirmed the specific recipes that had been reported missing are present.
3. Merged the tables exactly as Create's `getRecipesForType` does and read the
   results back: bulk washing 76, bulk smelting 87, bulk smoking 10, bulk
   haunting 30, crushing 150. `Gravel -> Flint 25% + Iron Nugget 12.5%` confirmed
   end to end.
4. Re-scanned the 596 native recipe files: **0 duplicate identifiers, 0
   structural problems**.

---

## v1.7 — the pause menu, and the chain drive from Create's own models

### The pause menu works again

v1.6's Recipe Browser button **blanked the pause screen**. Pressing Escape showed
an empty menu with no buttons, and no way to leave the world. That is fixed by
removing the browser's pause-menu patch entirely.

The browser needed a door, and Bedrock's JSON UI cannot call a script, so the
only way to put a button on the pause menu is to patch the vanilla
`pause_screen_content` control. More Create did that from its own file declaring
`"namespace": "pause"`, expecting the patch to merge with the vanilla screen. It
did not merge — it **replaced** the vanilla control with one that has no content
of its own, and a control with no content draws nothing.

v1.6's notes claimed the worst case was "our button does not appear". That was
wrong, and it was the wrong thing to gamble on a screen you need in order to quit
the game. The browser is out until it has an entry point that cannot touch a
vanilla screen; the **Recipe Book** item still lists all 400 recipes, and its
generators are kept for when the door is rebuilt.

### The Recipe Book no longer breaks blocks

In creative, every item breaks a block instantly on tap — and on touch controls
the tap that opens the book lands on whatever you are looking at, so reading the
book mined the ground in front of you. The book now carries
`minecraft:can_destroy_in_creative: false`. It is a reference, not a tool.

### The Encased Chain Drive is ported, not guessed

The drive has been drawn wrong twice, both times because a texture transform was
worked out by hand and looked plausible. It is now converted directly from
`assets/create/models/block/encased_chain_drive/*.json` in the Create jar, and
the conversion is *checked*.

What the guesses got wrong:

- **The side line ran the wrong way.** Create rotates the casing texture per
  face, so the metal strip runs around the block; a Bedrock
  `material_instances` cube cannot rotate a texture, so every side face showed
  the strip horizontally.
- **The two ends of a row pointed the same way.** Create tells `start` from
  `end` by turning the whole model 180°. Earlier versions used a *mirrored*
  copy of the end texture instead — which puts the sprocket in the right place
  but leaves the frame's lit edge on the wrong side, so one end of every row
  read as inverted.
- **Vertical runs had no connected look at all.** Create ships
  `end_vertical` and `middle_vertical` models; there was no Bedrock equivalent,
  so a drive mounted on top of a row stayed unconnected.

All six of Create's models — `single`, `end_horizontal`, `middle_horizontal`,
`end_vertical`, `middle_vertical` and `item` — are now real Bedrock geometry,
placed by `minecraft:transformation` using the same rotations Create's blockstate
uses. Bedrock UVs can express a 180° turn (negate both `uv_size` components) but
not 90° or 270°, so those are baked as pre-turned copies of the texture with the
UV rectangle moved to match.

That rectangle rule is the part that went wrong before, so it is no longer taken
on trust: `tools/verify_chain_drive.py` renders every one of the **116 faces**
both ways — Java's (crop the UV rectangle, turn the patch) and Bedrock's (crop
the converted rectangle out of the pre-turned texture) — and compares them pixel
for pixel at 64× scale. All 116 match.

The item model comes from Create's own `item.json`, so the shaft through the
middle is Create's, not an approximation. The block also no longer spawns a
visual entity: it draws its whole self now, and one sitting on top would
double-draw the casing.

---

## v1.8 — why updates were not arriving, and the chain drive's rotation

### Installing a new build now actually replaces the old one

Every release from v1.0 to v1.7 shipped `"version": [1, 0, 0]` in both
manifests. Minecraft identifies an installed pack by UUID **and** version, so
importing a new `.mcaddon` whose packs claim a version already installed does
not reliably replace them — the world keeps running the copy it already has.

That is almost certainly why the pause menu was still blank after v1.7 removed
the code that broke it: the fix was built, published and downloaded, and the
game went on using v1.6's resource pack. The pack version now follows the
release, so v1.8's packs identify as `[1, 8, 0]`, and `tools/build.py` stamps it
automatically so it can never drift again.

**Updating from an older build:** delete the old More Create behaviour and
resource packs from Minecraft's pack list before importing v1.8, then re-enable
them on the world. That guarantees a clean swap regardless of what the previous
install left behind.

### The chain drive turns the right way now

Three separate faults, each found from a specific thing that looked wrong in
game rather than by another guess:

- **The two ends of a horizontal run were swapped.** Bedrock's
  `minecraft:transformation` turns the opposite way about Y to Java's blockstate
  `y` rotation, so `y: 90` and `y: 270` traded places — which is exactly the
  180° that tells one end of a run from the other. The Y rotation is now
  negated when the blockstate is ported.

  What made this identifiable rather than a coin flip: the *middle* looked
  correct and so did every *vertical* run. The middle texture is symmetric
  left-to-right, so a 180° error is invisible on it, and vertical runs are
  placed with X rotations, which were never affected. Only horizontal ends —
  the one case that is both asymmetric and Y-rotated — were wrong.

- **The grey bars between connected drives** were the same fault seen from the
  other side. A swapped end puts its closed casing edge against its neighbour
  instead of facing outward, so every seam in a row grew a frame. Connected
  drives now meet with no bar; a lone drive keeps its full frame, as Create's
  own `single` model does.

- **The casing strip did not meet at the corners.** Bedrock's cube faces do not
  all start from the same texture orientation Java's do, so a face can sample
  exactly the right pixels and still be turned. The east/west pair was 90° out:
  the strip ran vertically there while running horizontally on the top and
  bottom. Those two faces now carry a documented correction.

- **A run along X picked the wrong model.** Create's "first" perpendicular axis
  is the lower-ordinal one, so a drive turning on X runs along Y first and Z
  second; the script had those the wrong way round for X alone.

`tools/verify_chain_drive.py` still checks all 116 faces pixel for pixel, now
including the orientation correction, so the rectangle maths stays proven.
