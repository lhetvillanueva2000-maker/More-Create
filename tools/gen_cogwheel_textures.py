#!/usr/bin/env python3
"""Generate the slotted casing textures for encased cogwheels.

Create cuts a dark gap across the casing where the cogwheel passes through, and
ships that art as `<casing>_encased_cogwheel_side.png` - but only for andesite
and brass, because those are the only two casings Java can encase with. More
Create allows all four, so copper and creative need the same slot on their own
colours.

Rather than copying andesite's pixels over another casing - which drags
andesite's brown across the middle of the texture and loses the copper or
creative frame - the slot is taken as a *ratio*. Comparing Create's andesite
slotted texture against the plain andesite casing gives, per pixel, how much
Create darkened it; applying that same ratio to any casing cuts an identical
slot while leaving the casing's own colour intact.

The andesite pair is the reference because Java's and Bedrock's andesite casing
textures are byte-identical, so the ratio is unambiguous.

Every casing goes through the same path so all four read as one family, and a
90-degree rotation of each gives the `_v` variant used on the block faces whose
UVs run the other way.
"""

import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "packs/resource/textures/morecreate/blocks")

CASINGS = ("andesite", "brass", "copper", "creative")


def load16(path):
    image = Image.open(path).convert("RGBA")
    return image.crop((0, 0, 16, 16)) if image.size != (16, 16) else image


def slot_ratio(jar_textures):
    """Per-pixel darkening Create applies to cut the slot, from the andesite pair.

    The gap itself is not painted dark - Create punches it fully transparent, so
    the cogwheel turning inside shows through. Those pixels are recorded as
    "clear"; the rest carry a per-channel ratio, with an absolute value where the
    plain casing channel is zero and a ratio would say nothing.
    """
    slotted = load16(os.path.join(jar_textures, "andesite_encased_cogwheel_side.png")).load()
    plain = load16(os.path.join(jar_textures, "andesite_casing.png")).load()
    ratio = {}
    for y in range(16):
        for x in range(16):
            src, dst = plain[x, y], slotted[x, y]
            if src == dst:
                continue
            if dst[3] == 0:
                ratio[(x, y)] = "clear"
                continue
            ratio[(x, y)] = [
                ("mul", dst[i] / src[i]) if src[i] else ("abs", dst[i])
                for i in range(3)
            ] + [("abs", dst[3])]
    return ratio


def apply_slot(base, ratio):
    out = base.copy()
    pixels = out.load()
    for (x, y), channels in ratio.items():
        if channels == "clear":
            pixels[x, y] = (0, 0, 0, 0)
            continue
        pixel = pixels[x, y]
        values = []
        for i, (mode, value) in enumerate(channels):
            values.append(int(value) if mode == "abs"
                          else min(255, int(round(pixel[i] * value))))
        pixels[x, y] = tuple(values)
    return out


def main():
    jar_textures, bedrock_casings = sys.argv[1], sys.argv[2]
    os.makedirs(OUT, exist_ok=True)
    ratio = slot_ratio(jar_textures)
    print("slot covers %d of 256 pixels" % len(ratio))

    for casing in CASINGS:
        base = load16(os.path.join(bedrock_casings, "%s_casing.png" % casing))
        shipped = os.path.join(jar_textures, "%s_encased_cogwheel_side.png" % casing)
        if os.path.isfile(shipped):
            # Create draws andesite and brass itself - use its own art.
            art = load16(shipped)
            source = "Create's art"
        else:
            art = apply_slot(base, ratio)
            source = "derived"
        art.save(os.path.join(OUT, "%s_encased_cogwheel_h.png" % casing))
        art.rotate(90, expand=False).save(
            os.path.join(OUT, "%s_encased_cogwheel_v.png" % casing))

        # How much of the casing's own colour survived, and how dark the slot got.
        pb, pa = base.load(), art.load()
        kept = sum(1 for y in range(16) for x in range(16) if pb[x, y] == pa[x, y])
        slot_lum = [sum(1 for x in range(16) if pa[x, y][3] == 0) for y in (6, 7, 8, 9)]
        print("  %-9s %-13s kept %3d/256 casing pixels, see-through px per slot row %s"
              % (casing, source, kept, slot_lum))

    # Self-check: the derived slot, applied to andesite, must reproduce Create's
    # own andesite art exactly - otherwise the ratio is losing information and
    # copper and creative would be subtly wrong too.
    check = apply_slot(load16(os.path.join(bedrock_casings, "andesite_casing.png")), ratio)
    truth = load16(os.path.join(jar_textures, "andesite_encased_cogwheel_side.png"))
    pc, pt = check.load(), truth.load()
    wrong = sum(1 for y in range(16) for x in range(16) if pc[x, y] != pt[x, y])
    print("self-check: derived andesite differs from Create's art in %d pixels%s"
          % (wrong, "" if wrong == 0 else "  <-- ratio is lossy"))


if __name__ == "__main__":
    main()
