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
  - main.py    this loop: home -> sectors -> sector -> ... -> home, and the
               co-op one: home -> ship -> lobby -> sector -> ... -> home;
  - menu.py    the screens outside a sector (home, sectors, hangar, options,
               co-op lobby);
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
from maelstrom import bugreport, bugsend, galaxy_layout, loop
from maelstrom.storage import base_loadout, read_meta, sector_entry, write_meta


async def campaign():
    """The galaxy: pick a region on the map, play its sectors + Titan to free
    it, then pick another. Returns "menu" or "quit"."""
    while True:
        regions = galaxy_layout.load_layout()
        ri = await menu.galaxy_map(regions)
        if isinstance(ri, str):                  # "menu" or "quit"
            return ri
        if await region_flow(regions, ri) == "quit":
            return "quit"


async def region_flow(regions, ri):
    """One region: pick its sectors (and, once the four are freed, its Titan),
    play them, carry the loadout from one to the next. Beating the Titan frees
    the region. Returns "menu" or "quit"."""
    region = regions[ri]
    rid = galaxy_layout.region_id(region)
    carry_id = rid + ":carry"
    meta = read_meta()
    carried = meta["progress"].get(carry_id, {}).get("loadout")
    carry = [dict(carried or base_loadout(meta["ship"]))]
    while True:
        pick = await menu.region_screen(regions, ri)
        if pick in ("menu", "quit"):
            return pick
        if pick == "titan":
            level, sid = galaxy_layout.titan_level(region), galaxy_layout.titan_id(region)
        else:
            level = galaxy_layout.sector_level(region, pick)
            sid = galaxy_layout.sector_id(region, pick)
        outcome, game = await loop.play(level, sid, carry=carry)
        loop.current_game = None
        if game.cleared:
            carry = game.carry_out
            meta = read_meta()
            sector_entry(meta, carry_id)["loadout"] = carry[0]
            if pick == "titan" and rid not in meta["liberated"]:
                meta["liberated"].append(rid)
            write_meta(meta)
            if pick == "titan":
                return "menu"                    # region freed -> back to the map
        if outcome == "quit":
            return "quit"
        if outcome == "menu":
            return "menu"
        if outcome == "hangar" and await menu.hangar() == "quit":
            return "quit"


async def coop():
    """Co-op is being reworked for the region model -- temporarily unavailable."""
    return "menu"


async def main():
    menu.init()
    bugsend.flush_async()        # resend whatever an earlier run could not
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
        if choice == "coop":
            if await coop() == "quit":
                break
            continue
        # campaign: pick a ship, then the galaxy map (coming back to it loops)
        chosen = await menu.ships()
        if chosen == "quit":
            break
        if chosen == "menu":
            continue
        if await campaign() == "quit":
            break


def verification():
    """`--verification`: the packaged game checks itself, then quits.

    Run by the release pipeline (.github/workflows/packages.yml) on the
    PyInstaller package and on the AppImage, under SDL's dummy drivers: the
    bundled font and languages must load, and every sector must start and
    play a few seconds without raising. Returns the exit code."""
    from maelstrom import galaxy_layout, i18n, screen
    from maelstrom.session.game import Game

    menu.init()
    for code in ("fr", "en"):
        if not i18n.catalog(code):
            print(f"verification: language {code} missing", file=sys.stderr)
            return 1
    if screen.FONT is None:
        print("verification: font not loaded", file=sys.stderr)
        return 1
    regions = galaxy_layout.load_layout()
    levels = 0
    for region in regions:
        for i in range(len(region["sectors"])):
            encounters = [(galaxy_layout.sector_level(region, i),
                           galaxy_layout.sector_id(region, i))]
            if i == 0:                                   # exercise the Titan once
                encounters.append((galaxy_layout.titan_level(region),
                                   galaxy_layout.titan_id(region)))
            for level, sid in encounters:
                game = Game(level, sid)
                for _ in range(120):                     # a few seconds of waves
                    game.update(1 / 60)
                    game.draw()
                game.t = game.level["duration"]
                game.enter_warning()                     # bring on the boss
                for _ in range(240):
                    game.update(1 / 60)
                    game.draw()
                levels += 1
        pygame.display.flip()
    print(f"verification: {len(regions)} regions, {levels} levels OK")
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
        # Leave a ticket so the next launch sends it (sending now, on the way
        # down, is unsafe). Only when the player allowed it and a relay is set.
        if bugsend.consent() and bugsend.enabled():
            try:
                bugsend.queue_report(folder, "crash")
            except OSError:
                pass
    raise
if not WEB:
    pygame.quit()
