#!/usr/bin/env python3
"""Pre-render the flag PNGs in w160/ into truecolor ANSI art.

Each terminal cell holds two vertical pixels using the half-block
character: the foreground colour paints the top pixel, the background
colour paints the bottom one. Output goes to colorscripts/<size>/<code>.

Usage: python3 scripts/generate.py   (requires Pillow)
"""

import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "w160"
OUT = ROOT / "colorscripts"
NAMES = ROOT / "names.tsv"

# Width in terminal columns for each size.
SIZES = {"small": 24, "regular": 40, "large": 64}

UPPER = "▀"  # ▀
LOWER = "▄"  # ▄
RESET = "\x1b[0m"


def fg(c):
    return "\x1b[38;2;%d;%d;%dm" % c


def bg(c):
    return "\x1b[48;2;%d;%d;%dm" % c


def render(img, width):
    w, h = img.size
    height = max(2, round(h * width / w))
    height += height % 2  # whole cells
    img = img.resize((width, height), Image.Resampling.BOX)
    px = img.load()

    lines = []
    for y in range(0, height, 2):
        out = []
        cur_fg = cur_bg = None  # colour state, only emit on change
        for x in range(width):
            r1, g1, b1, a1 = px[x, y]
            r2, g2, b2, a2 = px[x, y + 1]
            top = (r1, g1, b1) if a1 >= 128 else None
            bot = (r2, g2, b2) if a2 >= 128 else None

            if top is None and bot is None:
                if cur_bg is not None:
                    out.append("\x1b[49m")
                    cur_bg = None
                out.append(" ")
                continue

            if top is not None and bot is not None:
                char, want_fg, want_bg = UPPER, top, bot
            elif top is not None:
                char, want_fg, want_bg = UPPER, top, None
            else:
                char, want_fg, want_bg = LOWER, bot, None

            if want_bg != cur_bg:
                out.append(bg(want_bg) if want_bg else "\x1b[49m")
                cur_bg = want_bg
            if want_fg != cur_fg:
                out.append(fg(want_fg))
                cur_fg = want_fg
            out.append(char)
        out.append(RESET)
        lines.append("".join(out))
    return "\n".join(lines) + "\n"


def main():
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
            (OUT / size / png.stem).write_text(render(img, width), encoding="utf-8")
    print("rendered %d flags x %d sizes into %s" % (len(pngs), len(SIZES), OUT))


if __name__ == "__main__":
    main()
