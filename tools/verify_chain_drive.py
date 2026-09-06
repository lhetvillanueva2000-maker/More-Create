#!/usr/bin/env python3
"""Prove the ported chain drive samples exactly the pixels Create's models do.

The Encased Chain Drive was drawn wrong in game twice, both times because a
texture transform was worked out by hand and looked plausible. This checks it
instead: for every face of every model, it renders what Java would show (crop
the UV rectangle out of the original texture, then turn the patch by the face's
`rotation`) and what Bedrock will show (crop the converted rectangle, signs and
all, out of the pre-turned texture), and compares them pixel for pixel.

Textures are blown up 64x first so a turn or a flip cannot lose anything to
rounding.

Usage: verify_chain_drive.py <Create jar assets/create dir>
"""

import importlib.util
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAKED = os.path.join(ROOT, "packs/resource/textures/morecreate/blocks")
SCALE = 64


def load_generator():
    spec = importlib.util.spec_from_file_location(
        "gen_chain_drive", os.path.join(ROOT, "tools/gen_chain_drive.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(path):
    image = Image.open(path).convert("RGBA")
    if image.size != (16, 16):
        image = image.crop((0, 0, 16, 16))
    return image.resize((SCALE, SCALE), Image.NEAREST)


def crop(image, x1, y1, x2, y2):
    """Crop a UV rectangle in 0..16 space, reading reversed coords as flips."""
    step = SCALE / 16
    box = (int(round(min(x1, x2) * step)), int(round(min(y1, y2) * step)),
           int(round(max(x1, x2) * step)), int(round(max(y1, y2) * step)))
    if box[2] <= box[0] or box[3] <= box[1]:
        return None
    patch = image.crop(box)
    if x2 < x1:
        patch = patch.transpose(Image.FLIP_LEFT_RIGHT)
    if y2 < y1:
        patch = patch.transpose(Image.FLIP_TOP_BOTTOM)
    return patch


def pixels(image):
    getter = getattr(image, "get_flattened_data", None)
    return list(getter()) if getter else list(image.getdata())


def main():
    source = sys.argv[1]
    generator = load_generator()
    java_textures = os.path.join(source, "textures/block")

    checked = failed = 0
    for name in generator.MODELS:
        model = generator.load(os.path.join(
            source, "models/block/encased_chain_drive", name + ".json"))
        textures = model["textures"]
        for element in model["elements"]:
            for face, spec in element["faces"].items():
                texture = textures[spec["texture"].lstrip("#")].split("/")[-1]
                x1, y1, x2, y2 = spec["uv"]
                turn = spec.get("rotation", 0) % 360

                expected = crop(load(os.path.join(java_textures, texture + ".png")),
                                x1, y1, x2, y2)
                if expected is None:
                    continue
                if turn:
                    expected = expected.rotate(-turn, expand=True)

                converted = generator.face_uv(
                    spec, lambda ref, suffix, t=texture: (t, suffix))
                baked, suffix = converted["material_instance"]
                u, v = converted["uv"]
                width, height = converted["uv_size"]
                got = crop(load(os.path.join(BAKED, baked + suffix + ".png")),
                           u, v, u + width, v + height)

                checked += 1
                if got is None or got.size != expected.size \
                        or pixels(got) != pixels(expected):
                    failed += 1
                    print("  MISMATCH %-18s %-6s rot=%-3s %s"
                          % (name, face, turn, texture + suffix))

    print("faces checked: %d   mismatching: %d" % (checked, failed))
    if failed:
        print("\nFAILED - the Bedrock UVs do not reproduce Create's faces")
        return 1
    print("\nOK - every face samples the same pixels Create's model does")
    return 0


if __name__ == "__main__":
    sys.exit(main())
