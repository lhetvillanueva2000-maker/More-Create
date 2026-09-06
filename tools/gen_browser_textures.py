#!/usr/bin/env python3
"""Draw the recipe browser's chrome: button, panel, slots, arrow, tabs.

Everything here is generated rather than copied so More Create carries its own
art, but the palette is sampled from Create's own UI (dark brown ground, brass
frame, gold highlight) so the browser sits next to Create's screens without
looking like a different mod.

The pause-menu button is the pack icon masked into a circle inside a brass
ring, in three states - idle, hovered, and open - because the button is a
toggle: press once to open the browser, press again to close it.

Usage: gen_browser_textures.py
"""

import json
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "packs/resource/textures/morecreate/ui")
ICON = os.path.join(ROOT, "packs/resource/pack_icon.png")

# Sampled from Create's create_background.png and jei_background.png.
GROUND = (30, 22, 16, 255)
FRAME_DARK = (68, 42, 28, 255)
FRAME = (112, 70, 48, 255)
FRAME_LIT = (156, 104, 70, 255)
GOLD = (244, 200, 106, 255)
SLOT = (43, 33, 25, 255)
SLOT_SHADOW = (21, 16, 12, 255)
SLOT_LIGHT = (107, 74, 49, 255)
CLEAR = (0, 0, 0, 0)

# Supersampling factor for the round button, so the circle has no jaggies.
SS = 8


def save(name, image, nineslice=None):
    os.makedirs(OUT, exist_ok=True)
    image.save(os.path.join(OUT, name + ".png"))
    if nineslice is not None:
        with open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8") as handle:
            json.dump({"nineslice_size": nineslice,
                       "base_size": list(image.size)}, handle, indent=4)
            handle.write("\n")
    print("  %-26s %s%s" % (name + ".png", image.size,
                            "  nineslice %s" % (nineslice,) if nineslice else ""))


def panel_background():
    """20x20 nine-sliced frame: dark ground, brass border, gold inner line."""
    image = Image.new("RGBA", (20, 20), GROUND)
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, 19, 19], outline=FRAME_DARK, width=2)
    draw.rectangle([2, 2, 17, 17], outline=FRAME, width=1)
    draw.rectangle([3, 3, 16, 16], outline=FRAME_LIT, width=1)
    # A gold pip in each corner, the way Create frames its own panels.
    for x, y in ((4, 4), (15, 4), (4, 15), (15, 15)):
        image.putpixel((x, y), GOLD)
    return image


def slot():
    """18x18 sunken slot, the standard inventory look in Create's palette."""
    image = Image.new("RGBA", (18, 18), SLOT)
    draw = ImageDraw.Draw(image)
    # Two pixels of shadow on the top-left and light on the bottom-right is
    # what makes a flat square read as a recess rather than a tile.
    for inset in (0, 1):
        draw.line([(inset, inset), (17 - inset, inset)], fill=SLOT_SHADOW)
        draw.line([(inset, inset), (inset, 17 - inset)], fill=SLOT_SHADOW)
        draw.line([(inset, 17 - inset), (17 - inset, 17 - inset)], fill=SLOT_LIGHT)
        draw.line([(17 - inset, inset), (17 - inset, 17 - inset)], fill=SLOT_LIGHT)
    image.putpixel((0, 17), SLOT_SHADOW)
    image.putpixel((17, 0), SLOT_SHADOW)
    return image


def arrow():
    """A 24x16 gold arrow pointing right, drawn pixel by pixel."""
    image = Image.new("RGBA", (24, 16), CLEAR)
    draw = ImageDraw.Draw(image)
    draw.rectangle([2, 6, 15, 9], fill=GOLD)
    for step in range(6):
        draw.line([(14 + step, 3 + step), (14 + step, 12 - step)], fill=GOLD)
    # A darker underline gives the arrow a little depth against the ground.
    draw.line([(2, 10), (17, 10)], fill=FRAME)
    return image


def tab(selected):
    """16x16 nine-sliced tab button for the machine list down the left side."""
    image = Image.new("RGBA", (16, 16), GROUND if not selected else FRAME_DARK)
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, 15, 15], outline=FRAME if not selected else GOLD, width=1)
    draw.rectangle([1, 1, 14, 14],
                   outline=FRAME_DARK if not selected else FRAME_LIT, width=1)
    return image


def circle_mask(size, inset=0):
    mask = Image.new("L", (size * SS, size * SS), 0)
    ImageDraw.Draw(mask).ellipse(
        [inset * SS, inset * SS, (size - inset) * SS - 1, (size - inset) * SS - 1],
        fill=255)
    return mask.resize((size, size), Image.LANCZOS)


def button(ring, glow, dim):
    """The pack icon in a circle, ringed in brass. 32x32 so it stays crisp."""
    size = 32
    image = Image.new("RGBA", (size, size), CLEAR)

    ring_layer = Image.new("RGBA", (size, size), ring)
    image.paste(ring_layer, (0, 0), circle_mask(size))

    inner = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    icon = Image.open(ICON).convert("RGBA").resize((size - 6, size - 6), Image.LANCZOS)
    if dim:
        # The open state is darkened so it reads as pressed at a glance.
        icon = Image.eval(icon, lambda channel: int(channel * 0.72))
        icon.putalpha(Image.open(ICON).convert("RGBA")
                      .resize((size - 6, size - 6), Image.LANCZOS).getchannel("A"))
    inner.paste(icon, (3, 3))
    image.paste(inner, (0, 0), circle_mask(size, inset=3))

    if glow:
        # A brighter one-pixel rim, drawn as the difference of two circles.
        rim = Image.new("RGBA", (size, size), GOLD)
        outline = Image.new("L", (size, size), 0)
        outline.paste(circle_mask(size), (0, 0))
        hole = circle_mask(size, inset=2)
        outline = Image.composite(Image.new("L", (size, size), 0), outline, hole)
        image.paste(rim, (0, 0), outline)
    return image


def unknown_item():
    """Shown when an id has no texture, instead of the pink checkerboard."""
    image = Image.new("RGBA", (16, 16), CLEAR)
    draw = ImageDraw.Draw(image)
    draw.rectangle([3, 2, 12, 13], outline=FRAME_LIT)
    draw.line([(6, 5), (9, 5)], fill=GOLD)
    draw.line([(9, 5), (9, 8)], fill=GOLD)
    draw.line([(9, 8), (7, 8)], fill=GOLD)
    draw.line([(7, 8), (7, 9)], fill=GOLD)
    image.putpixel((7, 11), GOLD)
    return image


def blank():
    """A fully transparent pixel, for tab icons whose art is in the frame."""
    return Image.new("RGBA", (1, 1), CLEAR)


def main():
    print("browser chrome ->", os.path.relpath(OUT, ROOT))
    save("browser_bg", panel_background(), nineslice=6)
    save("browser_slot", slot())
    save("browser_arrow", arrow())
    save("browser_tab", tab(False), nineslice=3)
    save("browser_tab_selected", tab(True), nineslice=3)
    save("browser_button", button(FRAME, glow=False, dim=False))
    save("browser_button_hover", button(FRAME_LIT, glow=True, dim=False))
    save("browser_button_pressed", button(GOLD, glow=True, dim=True))
    save("unknown_item", unknown_item())
    save("blank", blank())


if __name__ == "__main__":
    main()
