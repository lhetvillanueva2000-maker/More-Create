# Vanilla atlas references

Three files copied verbatim from Mojang's
[`bedrock-samples`](https://github.com/Mojang/bedrock-samples) resource pack
(`resource_pack/textures/item_texture.json`,
`resource_pack/textures/terrain_texture.json` and `resource_pack/blocks.json`).

They are **build-time reference data only** — nothing here is shipped inside
either More Create pack. `tools/icons.py` reads them to work out which texture
path belongs to a vanilla item or block, which is what lets the Recipe Browser
draw an icon for `minecraft:gravel` when JSON UI will only accept a path.

They live in the repository so the browser can be regenerated without fetching
anything, the same reason `tools/data/` keeps the Create recipe diff.

To refresh them:

```
base=https://raw.githubusercontent.com/Mojang/bedrock-samples/main/resource_pack
curl -o vanilla_item_texture.json    $base/textures/item_texture.json
curl -o vanilla_terrain_texture.json $base/textures/terrain_texture.json
curl -o vanilla_blocks.json          $base/blocks.json
```
