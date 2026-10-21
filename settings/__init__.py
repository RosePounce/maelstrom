"""Maelstrom settings: everything that can be tuned, and nothing that runs.

Two files, to open depending on what you want to change:
  - balance.py  the game's numbers: ship, weapons, AX missiles, bonuses and
                maluses, hangar upgrades, Thargoids, Interceptors, sectors;
  - ui.py       the look: canvas, colors, sector palettes, HUD sizes.

Everything the player reads lives apart, in the package's `locales/*.json`,
reached through `maelstrom.i18n` (one key -> one string, per language). The
game's own proper name and version are NOT translated: they are the two
constants below.

None of this imports the game code. Values that are CREATED at runtime
(window, fonts, scanlines) are not here: they live in `maelstrom/screen.py`.
"""

GAME_NAME = "Maelstrom"          # proper noun: the same in every language
VERSION = "0.2.0"
VERSION_LABEL = f"{GAME_NAME}   -   beta {VERSION}"
