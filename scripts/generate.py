#!/usr/bin/env python3
"""Pre-render the flag PNGs in w160/ into truecolor ANSI art.

Default style ("sextant") packs a 2x3 grid of sub-pixels into each
terminal cell using the Unicode sextant block characters (U+1FB00..),
giving three times the detail of half blocks. Each cell can only show
two colours (foreground and background), so pixels are first snapped to
the flag's own palette and the best two-colour split is picked per cell.
That keeps edges crisp instead of blending neighbouring colours.

The "half" style uses the upper half block (one colour on top, one below),
for terminals whose font lacks the sextant characters.

Output goes to colorscripts/<size>/<code>.

Usage: python3 scripts/generate.py [--style sextant|half]   (requires Pillow)
"""

import argparse
import itertools
import shutil
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "w160"
OUT = ROOT / "colorscripts"
NAMES = ROOT / "names.tsv"

# Width in terminal columns for each size.
SIZES = {"small": 24, "regular": 40, "large": 64}

# A colour must cover this share of the flag to join its palette.
PALETTE_MIN_SHARE = 0.0005
# Colours covering at least this share are the flag's main colours.
# Rarer colours that sit between two main colours are anti-aliasing.
MAIN_SHARE = 0.02
BLEND_TOLERANCE = 20
# Palette colours closer than this to a commoner one are merged into it.
MERGE_DISTANCE = 30

# Terminal cells are roughly twice as tall as they are wide.
CELL_ASPECT = 2.0

RESET = "\x1b[0m"


def dist2(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def blend_of(c, main):
    """If c is a mix of two main colours, return the one it is closer to."""
    for a, b in itertools.combinations(main, 2):
        ab = [y - x for x, y in zip(a, b)]
        length = sum(v * v for v in ab)
        t = sum((ci - ai) * v for ci, ai, v in zip(c, a, ab)) / length
        if not 0 < t < 1:
            continue
        p = [ai + t * v for ai, v in zip(a, ab)]
        if sum((ci - pi) ** 2 for ci, pi in zip(c, p)) ** 0.5 < BLEND_TOLERANCE:
            return a if t < 0.5 else b
    return None


def palette_of(img):
    """Return (palette, main colours) of the flag."""
    counts = Counter(p[:3] for p in img.get_flattened_data() if p[3] >= 128)
    total = sum(counts.values())
    main = []
    for colour, n in counts.most_common():
        if n < MAIN_SHARE * total:
            break
        if not blend_of(colour, main):
            main.append(colour)
    palette = []
    for colour, n in counts.most_common():
        if n < PALETTE_MIN_SHARE * total:
            break
        if any(dist2(colour, p) < MERGE_DISTANCE ** 2 for p in palette):
            continue
        if colour not in main and (n >= MAIN_SHARE * total or blend_of(colour, main)):
            continue
        palette.append(colour)
    return palette, main


def sample(img, cols, rows):
    """Downscale to cols x rows by majority vote of palette-snapped pixels.

    Returns a grid of colours, None where the pixel is transparent.
    """
    palette, main = palette_of(img)
    snapped = {}

    def snap(c):
        if c not in snapped:
            nearest = min(palette, key=lambda p: dist2(c, p))
            if dist2(c, nearest) >= MERGE_DISTANCE ** 2:
                nearest = blend_of(c, main) or nearest
            snapped[c] = nearest
        return snapped[c]

    w, h = img.size
    src = img.load()
    grid = []
    for sy in range(rows):
        y0 = sy * h // rows
        y1 = max(y0 + 1, (sy + 1) * h // rows)
        line = []
        for sx in range(cols):
            x0 = sx * w // cols
            x1 = max(x0 + 1, (sx + 1) * w // cols)
            votes = Counter()
            for y in range(y0, y1):
                for x in range(x0, x1):
                    r, g, b, a = src[x, y]
                    if a >= 128:
                        votes[snap((r, g, b))] += 1
            area = (y1 - y0) * (x1 - x0)
            line.append(votes.most_common(1)[0][0] if 2 * sum(votes.values()) >= area else None)
        grid.append(line)
    return grid


def split_two(pixels):
    """Pick fg/bg colours and the fg mask for one cell's sub-pixels."""
    opaque = [c for c in pixels if c is not None]
    if not opaque:
        return None, None, 0
    if len(opaque) < len(pixels):
        # Transparent sub-pixels show the terminal background.
        fg = Counter(opaque).most_common(1)[0][0]
        return fg, None, sum(1 << i for i, c in enumerate(pixels) if c is not None)
    colours = list(dict.fromkeys(opaque))
    if len(colours) == 1:
        return None, colours[0], 0
    best = None
    for a, b in itertools.combinations(colours, 2):
        mask = err = 0
        for i, c in enumerate(pixels):
            da, db = dist2(c, a), dist2(c, b)
            if da <= db:
                mask |= 1 << i
                err += da
            else:
                err += db
        if best is None or err < best[0]:
            best = (err, a, b, mask)
    _, fg, bg, mask = best
    if mask == (1 << len(pixels)) - 1:
        return None, fg, 0
    return fg, bg, mask


def sextant_char(mask):
    # Bit i is sub-pixel i, row-major in a 2-wide, 3-tall grid. The block
    # skips the four patterns that already exist elsewhere in Unicode.
    if mask == 0:
        return " "
    if mask == 63:
        return "█"  # █
    if mask == 21:
        return "▌"  # ▌
    if mask == 42:
        return "▐"  # ▐
    n = mask - (mask > 21) - (mask > 42)
    return chr(0x1FB00 + n - 1)


def half_char(mask):
    return {0: " ", 1: "▀", 2: "▄", 3: "█"}[mask]


STYLES = {
    # sub-pixels per cell (x, y), mask -> character
    "sextant": (2, 3, sextant_char),
    "half": (1, 2, half_char),
}


def render(img, width, style):
    sub_x, sub_y, char_for = STYLES[style]
    w, h = img.size
    rows = max(1, round(h / w * width / CELL_ASPECT))
    grid = sample(img, width * sub_x, rows * sub_y)

    lines = []
    for cy in range(rows):
        out = []
        cur_fg = cur_bg = None  # colour state, only emit on change
        for cx in range(width):
            pixels = [
                grid[cy * sub_y + i // sub_x][cx * sub_x + i % sub_x]
                for i in range(sub_x * sub_y)
            ]
            fg, bg, mask = split_two(pixels)
            if bg != cur_bg:
                out.append("\x1b[48;2;%d;%d;%dm" % bg if bg else "\x1b[49m")
                cur_bg = bg
            if mask and fg != cur_fg:
                out.append("\x1b[38;2;%d;%d;%dm" % fg)
                cur_fg = fg
            out.append(char_for(mask))
        out.append(RESET)
        lines.append("".join(out))
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--style", choices=STYLES, default="sextant")
    args = parser.parse_args()

    names = dict(
        line.split("\t", 1)
        for line in NAMES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    pngs = sorted(SRC.glob("*.png"))
    missing = [p.stem for p in pngs if p.stem not in names]
    if missing:
        raise SystemExit("names.tsv is missing: " + ", ".join(missing))

    if OUT.exists():
        shutil.rmtree(OUT)
    for size, width in SIZES.items():
        (OUT / size).mkdir(parents=True)
        for png in pngs:
            img = Image.open(png).convert("RGBA")
            (OUT / size / png.stem).write_text(render(img, width, args.style), encoding="utf-8")
    print("rendered %d flags x %d sizes (%s) into %s" % (len(pngs), len(SIZES), args.style, OUT))


if __name__ == "__main__":
    main()
