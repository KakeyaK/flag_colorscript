# flag-colorscript

Show a new flag with its country name every time you open the terminal.
Heavily inspired by [pokemon-colorscripts](https://gitlab.com/phoneybadger/pokemon-colorscripts).

The flags are pre-rendered into truecolor ANSI art, so printing one is just a
`cat`: no Python, no image libraries, and it works inside terminal multiplexers
like zellij and tmux.

Each terminal cell holds a 2x3 grid of sub-pixels, drawn with the Unicode
sextant block characters (🬀–🬻). Colours are snapped to each flag's own
palette, so stripes and emblems stay crisp instead of blurring together.

## Install (macOS / Linux)

```sh
git clone https://github.com/KakeyaK/flag_colorscript.git
cd flag_colorscript
./install.sh
```

This copies everything to `~/.local/share/flag-colorscript` and links the
command into `~/.local/bin`. Make sure that is on your `PATH`, then add the
command to the end of your `~/.zshrc` (zsh is the macOS default shell):

```sh
export PATH="$HOME/.local/bin:$PATH"
flag-colorscript
```

Every new Ghostty window/tab and every new zellij pane will now greet you with a flag.

Uninstall with `./install.sh uninstall`.

## Usage

```
flag-colorscript                     # random flag
flag-colorscript -n br               # by ISO code
flag-colorscript -n "south korea"    # by name
flag-colorscript -s small            # small | regular | large
flag-colorscript --no-title          # flag only
flag-colorscript -l                  # list all codes and names
```

Set `FLAG_COLORSCRIPT_SIZE=small` in your shell config to change the default size.

## Terminal requirements

Your terminal needs 24-bit (truecolor) support. Ghostty, iTerm2, kitty, WezTerm
and Alacritty all have it, and zellij passes it through. macOS's built-in
Terminal.app only supports 256 colours, so flags will look wrong there.

The sextant characters need Unicode 13 support. Ghostty, kitty and WezTerm draw
them natively. If you see boxes or question marks instead of flags, regenerate
with the simpler half-block style (see below).

## Regenerating the art

The source images live in `w160/` (160px wide PNGs) and the names in
`names.tsv`. After changing either, rebuild `colorscripts/` with:

```sh
pip install Pillow
python3 scripts/generate.py
```

Use `python3 scripts/generate.py --style half` for half-block art (1x2
sub-pixels per cell, works in any font). Column widths for each size are set in
`SIZES` at the top of the script.
