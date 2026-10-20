"""
Maelstrom - entry point of the project.

On the desktop:

    pip install -r ../requirements.txt
    python main.py

In the browser (pygbag packages this folder as WebAssembly):

    cd maelstrom          # pygbag reads pygbag.ini in the current folder
    pygbag .                 # serves on http://localhost:8000
    pygbag --build .         # writes build/web/, to publish as is

Three layers, one role each:
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
        # campaign: the sector list, as long as the player comes back to it
        pick = await menu.sectors()
        if pick == "quit":
            break
        if pick == "menu":
            continue
        if await campaign(pick) == "quit":
            break


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
