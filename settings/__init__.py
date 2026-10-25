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
VERSION = "1.1.1"
VERSION_LABEL = f"{GAME_NAME}  -  {VERSION}"

# The one address an installed build sends its bug reports to: a Cloudflare
# Worker (see relay/) that forwards them and holds no secret in this public
# code. Only a packaged build uses it; from the sources nothing leaves unless
# MAELSTROM_REPORT_URL points elsewhere. See maelstrom/bugsend.py.
BUG_REPORT_URL = "https://maelstrom.rose-pounce.workers.dev/report"

