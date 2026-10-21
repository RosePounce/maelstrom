"""
Maelstrom - entry point of the project.

On the desktop:

    pip install -r ../requirements.txt
    python main.py

In the browser (pygbag packages this folder as WebAssembly):

    cd maelstrom          # pygbag reads pygbag.ini in the current folder
    pygbag .                 # serves on http://localhost:8000
    pygbag --build .         # writes build/web/, to publish as is

Three layers, one role each: et le chieta
  - main.py    this loop: home -> sectors -> sector -> ... -> home;
  - menu.py    the screens outside a sector (home, sectors, hangar, options);
  - game/      the game, whose `loop.play()` plays ONE sector (all its
               attempts) and returns where to go next; its settings are
               apart, in settings/.

**Everything is asynchronous**, and pygbag imposes it: every screen loop
does `await asyncio.sleep(0)` after its `flip()`.

`pygame.quit()` is called here, and nowhere else.
"""

import asyncio
import sys

import pygame

import menu
from settings.ui import WEB
from maelstrom import bugreport, loop


async def campaign(level):
    """Plays from sector `level` on, until the player leaves for the menu.
    Returns "menu" or "quit".

    "next" chains the following sector; "hangar" opens the hangar then
    plays the sector `play()` named (the same one after a death, the next
    one after a cleared sector)."""
    while True:
        outcome, level = await loop.play(level)
        loop.current_game = None
        if outcome == "next":
            continue
        if outcome == "hangar":
            if await menu.hangar() == "quit":
                return "quit"
            continue
        return outcome


async def main():
    menu.init()
    while True:
        choice = await menu.home()
        if choice == "quit":
            break
        if choice == "hangar":
            if await menu.hangar() == "quit":
                break
            continue
        if choice == "options":
            if await menu.options() == "quit":
                break
            continue
        # campaign: pick a ship, then the sector list (coming back to it loops)
        chosen = await menu.ships()
        if chosen == "quit":
            break
        if chosen == "menu":
            continue
        pick = await menu.sectors()
        if pick == "quit":
            break
        if pick == "menu":
            continue
        if await campaign(pick) == "quit":
            break


def verification():
    """`--verification`: the packaged game checks itself, then quits.

    Run by the release pipeline (.github/workflows/packages.yml) on the
    PyInstaller package and on the AppImage, under SDL's dummy drivers: the
    bundled font and languages must load, and every sector must start and
    play a few seconds without raising. Returns the exit code."""
    from maelstrom import i18n, screen
    from maelstrom.session.game import Game
    from settings.balance import LEVELS

    menu.init()
    for code in ("fr", "en"):
        if not i18n.catalog(code):
            print(f"verification: language {code} missing", file=sys.stderr)
            return 1
    if screen.FONT is None:
        print("verification: font not loaded", file=sys.stderr)
        return 1
    for index in range(len(LEVELS)):
        game = Game(index)
        for _ in range(180):
            game.update(1 / 60)
            game.draw()
        pygame.display.flip()
    print(f"verification: {len(LEVELS)} sectors OK")
    return 0


if not WEB and "--verification" in sys.argv[1:]:
    code = verification()
    pygame.quit()
    sys.exit(code)

# pygbag looks for an `asyncio.run(main())` at module level: it is its entry
# point. In the browser the call never returns.
#
# Crash net (desktop): an uncaught exception, in a sector or in the menus,
# first writes a report in saves/bugs/ (traceback, screen, attempt state),
# then goes on as before: the traceback is still printed and the program
# still stops.
try:
    asyncio.run(main())
except Exception:
    folder = bugreport.report_crash(loop.current_game)
    if folder:
        print(f"Crash report written to {folder}", file=sys.stderr)
    raise
if not WEB:
    pygame.quit()
