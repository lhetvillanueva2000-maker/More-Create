#!/usr/bin/env python3
"""Generate the Encased Chain Drive's face textures.

Create draws the chain on the drive's *axis* faces - the ones showing the
sprocket - and which texture a drive uses depends on where its neighbours are:

    no neighbours     plain shaft hole (Create's `gearbox`)
    one neighbour     `encased_chain_drive_end`    sprocket, chain leaving one side
    both sides        `encased_chain_drive_middle` sprocket, chain straight through

The end texture is asymmetric, so it needs one variant per direction the chain
can leave. A drive's two axis faces look at each other from opposite sides, so
they take mirrored variants: that way both draw the chain heading toward the
same neighbour rather than away from it.

Usage: gen_chain_textures.py <Create jar block textures dir>
"""

import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "packs/resource/textures/morecreate/blocks")


def load16(path):
    image = Image.open(path).convert("RGBA")
    return image.crop((0, 0, 16, 16)) if image.size != (16, 16) else image


def chain_exit(image):
    """Which edge the chain runs out of, read off the texture itself."""
    pixels = image.load()
    row = 7  # the chain sits on rows 7-8
    left = sum(1 for x in range(0, 5) if pixels[x, row][3] and sum(pixels[x, row][:3]) < 150)
    right = sum(1 for x in range(11, 16) if pixels[x, row][3] and sum(pixels[x, row][:3]) < 150)
    column = 7
    up = sum(1 for y in range(0, 5) if pixels[column, y][3] and sum(pixels[column, y][:3]) < 150)
    down = sum(1 for y in range(11, 16) if pixels[column, y][3] and sum(pixels[column, y][:3]) < 150)
    return {"left": left, "right": right, "up": up, "down": down}


def main():
    jar_textures = sys.argv[1]
    os.makedirs(OUT, exist_ok=True)

    end = load16(os.path.join(jar_textures, "encased_chain_drive_end.png"))
    middle = load16(os.path.join(jar_textures, "encased_chain_drive_middle.png"))
    side = load16(os.path.join(jar_textures, "encased_chain_drive.png"))

    print("source end texture, chain pixels per edge:", chain_exit(end))

    # Create's end texture runs the chain out of the right-hand edge.
    variants = {
        "chain_drive_end_right": end,
        "chain_drive_end_left": end.transpose(Image.FLIP_LEFT_RIGHT),
        "chain_drive_end_up": end.rotate(90, expand=False),
        "chain_drive_end_down": end.rotate(270, expand=False),
        "chain_drive_link_h": middle,
        "chain_drive_link_v": middle.rotate(90, expand=False),
        "encased_chain_drive": side,
    }
    for name, image in variants.items():
        image.save(os.path.join(OUT, name + ".png"))
        if name.startswith("chain_drive_end"):
            edges = chain_exit(image)
            leading = max(edges, key=edges.get)
            print("  %-24s chain leaves: %-6s %s" % (name, leading, edges))
        else:
            print("  %-24s" % name)


if __name__ == "__main__":
    main()
