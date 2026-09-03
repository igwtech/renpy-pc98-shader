#!/usr/bin/env python3
"""Builds 16-colour PC-98 style palettes for each background and writes them
to game/palettes_generated.rpy.

Real PC-98 games shipped one hand-picked palette per scene (16 colours chosen
from the 4096-colour 12-bit hardware space). This script emulates the artist:
a pixel-count-weighted k-means over the scene's 4-bit colour histogram, so the
colours most pixels use become exact palette entries and as little as possible
has to be dithered. Every colour is snapped to 4 bits per channel so it is a
legal PC-98 colour, index 0 is always black, and for background+sprite scenes
the sprite's dominant colours are fixed entries (the character is drawn flat).

A "_night" variant is derived register by register (cold, dark shift of each
day colour), so a day -> night change is a pure palette-register swap: every
pixel keeps its colour index, only the register value changes - exactly how
PC-98 games did night scenes and fades.

Requires Pillow. Run from the project root:  python3 tools/make_palettes.py
"""
import glob
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES = os.path.join(ROOT, "game", "images")
OUT = os.path.join(ROOT, "game", "palettes_generated.rpy")


def to_4bit(rgb):
    """Snap an 8-bit colour to the PC-98 4-bit-per-channel grid."""
    return tuple(int(round(c / 17.0)) * 17 for c in rgb)


def night_shift(rgb):
    """Cold, dark version of one palette register (moonlight)."""
    r, g, b = rgb
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    r = 0.30 * r + 0.10 * lum
    g = 0.35 * g + 0.15 * lum
    b = 0.55 * b + 0.30 * lum + 20
    return to_4bit((min(255, r), min(255, g), min(255, b)))


PERCEPTUAL = np.array([0.30, 0.59, 0.11])   # same weights as pc98_dist() in the shader


def _hist4(rgb_pixels):
    """Histogram of colours snapped to the 4-bit PC-98 grid: (N,3) colours, (N,) counts."""
    q = (np.asarray(rgb_pixels, dtype=np.int32) + 8) // 17
    keys = q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2]
    counts = np.bincount(keys, minlength=4096)
    idx = np.nonzero(counts)[0]
    cols = np.stack([idx // 256, (idx // 16) % 16, idx % 16], axis=1) * 17
    return cols.astype(np.float64), counts[idx].astype(np.float64)


def _wdist(a, b):
    """Perceptual squared distance between (N,3) and (M,3) -> (N,M)."""
    d = a[:, None, :] - b[None, :, :]
    return (d * d * PERCEPTUAL).sum(axis=2)


SPRITE_WEIGHT = 4.0   # the character must read well: its pixels count 4x in the objective


## Colours that must be in a palette (snapped to 4 bits): e.g. the two siren
## colours of the police car, so the colour-cycling demo can swap them.
FIXED = {
    "street": [(255, 34, 34), (34, 85, 255)],
}


def palette_for(im, colors=16, sprite_mask=None, fixed=()):
    """16 colours that minimise the dithering needed to show `im`.

    Weighted k-means (Lloyd) over the 4-bit colour histogram of the scene:
    the objective is the pixel-count-weighted quantisation error, so the
    colours most pixels actually use become exact palette entries and only
    rare transitions need to be dithered. Black is always index 0. When a
    sprite mask is given, the sprite's pixels weigh SPRITE_WEIGHT times more,
    so the character gets exact colours before the background does."""
    small = im.convert("RGB").resize((480, 270), Image.LANCZOS)
    px = np.asarray(small).reshape(-1, 3)
    w = np.ones(len(px))
    if sprite_mask is not None:
        m = np.asarray(sprite_mask.resize((480, 270), Image.LANCZOS)).reshape(-1) > 128
        w[m] = SPRITE_WEIGHT
    q = (px.astype(np.int32) + 8) // 17
    keys = q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2]
    counts = np.bincount(keys, weights=w, minlength=4096)
    idx = np.nonzero(counts)[0]
    cols = (np.stack([idx // 256, (idx // 16) % 16, idx % 16], axis=1) * 17).astype(np.float64)
    counts = counts[idx]

    fixed_list = [(0, 0, 0)] + [to_4bit(c) for c in fixed if to_4bit(c) != (0, 0, 0)]
    fixed_arr = np.array(fixed_list, dtype=np.float64)
    k = colors - len(fixed_list)

    # k-means++ style seeding: repeatedly take the colour with the largest weighted error
    centers = []
    for _ in range(k):
        cur = np.vstack([fixed_arr] + ([np.array(centers)] if centers else []))
        d = _wdist(cols, cur).min(axis=1)
        centers.append(cols[int(np.argmax(d * counts))].copy())
    centers = np.array(centers)

    for _ in range(40):
        allc = np.vstack([fixed_arr, centers])
        assign = _wdist(cols, allc).argmin(axis=1)
        new = centers.copy()
        for j in range(k):
            m = assign == len(fixed_list) + j
            if counts[m].sum() > 0:
                new[j] = (cols[m] * counts[m, None]).sum(axis=0) / counts[m].sum()
        if np.allclose(new, centers):
            break
        centers = new

    out = fixed_list + [to_4bit(tuple(int(round(v)) for v in c)) for c in centers]
    seen, uniq = set(), []
    for c in out:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    while len(uniq) < colors:   # refill slots lost to snapping with the heaviest residual
        d = _wdist(cols, np.array(uniq, dtype=np.float64)).min(axis=1) * counts
        c = to_4bit(tuple(int(v) for v in cols[int(np.argmax(d))]))
        if c in seen:
            break
        seen.add(c)
        uniq.append(c)
    return sorted(uniq[:colors], key=lambda c: 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2])


def dither_stats(im, palette):
    """(rms error in 8-bit units, share of pixels within 1 step, within 2 steps)
    of the nearest palette colour. Pixels within a step are drawn flat."""
    small = im.convert("RGB").resize((480, 270), Image.LANCZOS)
    px = np.asarray(small).reshape(-1, 3).astype(np.float64)
    d = _wdist(px, np.array(palette, dtype=np.float64)).min(axis=1)
    return (float(np.sqrt(d.mean())), float((d <= 17 ** 2).mean()), float((d <= (2 * 17) ** 2).mean()))


## Scene composites: background + character sprite, so the 16 colours are
## shared between both (what a PC-98 artist would have done for that scene).
COMPOSITES = {
    "cafe_claire": ("bg_cafe.webp", "claire.png"),
    "sunset_claire": ("bg_sunset.webp", "claire.png"),
    "candles_claire": ("bg_candles.webp", "claire.png"),
    "rooftop_claire": ("bg_rooftop.webp", "claire.png"),
}


def _fmt(stats):
    return (stats[0], 100 * stats[1], 100 * stats[2])


def composite(bg_name, sprite_name, screen=(1920, 1080), with_mask=False):
    bg = Image.open(os.path.join(IMAGES, bg_name)).convert("RGBA")
    z = screen[1] / float(bg.height)
    bg = bg.resize((int(round(bg.width * z)), screen[1]), Image.LANCZOS)
    x0 = max(0, (bg.width - screen[0]) // 2)
    bg = bg.crop((x0, 0, x0 + screen[0], screen[1]))
    sp = Image.open(os.path.join(IMAGES, sprite_name)).convert("RGBA")
    zoom = screen[1] / float(sp.height)
    sp = sp.resize((int(sp.width * zoom), screen[1]), Image.LANCZOS)
    pos = ((screen[0] - sp.width) // 2, screen[1] - sp.height)
    bg.alpha_composite(sp, pos)
    if with_mask:
        mask = Image.new("L", screen, 0)
        mask.paste(sp.split()[-1], pos)
        return bg.convert("RGB"), mask
    return bg.convert("RGB")


def main():
    entries = []
    for path in sorted(glob.glob(os.path.join(IMAGES, "bg_*.webp"))):
        name = os.path.splitext(os.path.basename(path))[0][3:]
        im = Image.open(path).convert("RGB")
        day = palette_for(im, fixed=FIXED.get(name, ()))
        print("%-16s rms %5.1f  flat(1 step) %4.1f%%  (2 steps) %4.1f%%" % ((name,) + _fmt(dither_stats(im, day))))
        entries.append((name, day))
        entries.append((name + "_night", [night_shift(c) for c in day]))
    for name, (bg_name, sprite_name) in sorted(COMPOSITES.items()):
        comp, mask = composite(bg_name, sprite_name, with_mask=True)
        day = palette_for(comp, sprite_mask=mask)
        print("%-16s rms %5.1f  flat(1 step) %4.1f%%  (2 steps) %4.1f%%" % ((name,) + _fmt(dither_stats(comp, day))))
        entries.append((name, day))
        entries.append((name + "_night", [night_shift(c) for c in day]))

    # Swatch strips (game/images/pal_<name>.png) for the demo video.
    for name, cols in entries:
        strip = Image.new("RGBA", (16 * 66 - 2, 64), (0, 0, 0, 0))
        for i, c in enumerate(cols):
            strip.paste(Image.new("RGBA", (64, 64), c + (255,)), (i * 66, 0))
        strip.save(os.path.join(IMAGES, "pal_%s.png" % name))

    with open(OUT, "w") as f:
        f.write("## GENERATED by tools/make_palettes.py - do not edit by hand.\n")
        f.write("## One 16-colour palette per background (4 bits per channel),\n")
        f.write("## plus a *_night variant derived register by register.\n\n")
        f.write("init -5 python:\n")
        f.write("    pc98_palettes.update({\n")
        for name, cols in entries:
            f.write('        "%s": [\n' % name)
            for r, g, b in cols:
                f.write("            (%.4f, %.4f, %.4f),  # #%02x%02x%02x\n" % (r / 255.0, g / 255.0, b / 255.0, r, g, b))
            f.write("        ],\n")
        f.write("    })\n")
    print("wrote", OUT, "with", len(entries), "palettes")


if __name__ == "__main__":
    main()
