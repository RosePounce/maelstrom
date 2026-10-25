"""Headless captures of the game, for the store pages and the README.

    python tools/capture.py [out_dir] [--lang fr|en]

Default output: `docs/press/`.

Plays the real game under SDL's dummy drivers -- no window, no sound -- and
saves the canvas (960 x 540, scanlines included) at chosen moments. Every
screen of the game is a coroutine that yields once per frame
(`await asyncio.sleep(0)`, see main.py), so `coro.send(None)` plays exactly
one frame: the menus are captured by stepping them, a sector by building a
`Game` and updating it the way loop.py does.

Three things are staged, and only three: the ship FLIES ITSELF (the keyboard
is never pressed under the dummy driver, so `local_axes` steers it along a
path that keeps it in frame), it is held above a hull floor so a run of
captures never dies mid-shot, and the frame kept is the BUSIEST of a short
window -- a shot taken at a fixed second lands as often as not on an empty
sky. The rest is the game as it plays.

The player's save is never touched: `read_meta` serves a press meta (every
sector open, a stocked hangar) and `write_meta` writes nothing.
"""

import copy
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

FPS = 60
DT = 1.0 / FPS
HULL_FLOOR = 0.58            # part of the hull the captured ship keeps
MISSILE_EVERY = 1.6          # seconds between two captured missile launches


class Clock:
    """Fixed clock, in place of `pygame.time.Clock`: the shots must not
    depend on how fast the machine is, and nothing may sleep to hold 60 FPS.
    """

    def tick(self, fps=0):
        return int(1000 * DT)

    def get_fps(self):
        return float(FPS)


def press_meta():
    """A played-in save: every sector open, a stocked hangar, a few records.
    The sector list and the hangar are worth a shot only like this."""
    from maelstrom.storage import default_meta

    meta = default_meta()
    meta["alloys"] = 165
    meta["hangar"] = {"hull": 3, "shield": 3, "regen": 2, "damage": 3,
                      "rate": 2, "missiles": 2, "magnet": 2, "salvage": 1}
    meta["ship"] = "krait"
    meta["unlocked"] = len(meta["deaths"])
    meta["deaths"] = [6, 11, 15, 23, 4][:len(meta["deaths"])]
    meta["best"] = [94.6, 143.2, 157.8, None, None][:len(meta["best"])]
    meta["loadouts"] = [{"weapon": "pulse", "level": 3, "missiles": 4},
                        {"weapon": "frag", "level": 4, "missiles": 5},
                        {"weapon": "rail", "level": 4, "missiles": 5},
                        {"weapon": "pulse", "level": 5, "missiles": 6},
                        {"weapon": "rail", "level": 5, "missiles": 6}
                        ][:len(meta["loadouts"])]
    return meta


def flight_path(self):
    """Where the captured ship steers: a slow weave in the left third of the
    play area, where it reads against the backdrop and clear of the HUD.
    Replaces `Game.local_axes`, which reads a keyboard nobody presses."""
    from settings.ui import HEIGHT, WIDTH

    def toward(target, value):
        return max(-1.0, min(1.0, (target - value) / 60.0))

    ship = self.ship
    tx = WIDTH * (0.21 + 0.035 * math.sin(self.elapsed * 0.5))
    ty = HEIGHT * (0.46 + 0.17 * math.sin(self.elapsed * 0.9))
    return toward(tx, ship.x), toward(ty, ship.y)


def setup(lang):
    """Prepares the game as main.py does, then swaps the clock, the mouse,
    the controls and the save for ones a capture run can steer."""
    import menu
    from maelstrom import i18n, screen
    from maelstrom.session import game as game_module

    menu.init()
    i18n.set_language(lang)
    screen.CLOCK = Clock()

    meta = press_meta()
    for module in (menu, game_module):
        module.read_meta = lambda: copy.deepcopy(meta)
        module.write_meta = lambda meta: None
    game_module.Game.local_axes = flight_path
    hover((-10, -10))


def hover(pos):
    """Where the pointer sits: the cards and the panels lift under it."""
    pygame.mouse.get_pos = lambda: pos


def save(name, out_dir, surf=None):
    from maelstrom import screen

    path = os.path.join(out_dir, name + ".png")
    pygame.image.save(surf if surf is not None else screen.SCREEN, path)
    print("  " + os.path.relpath(path, ROOT))


# ----------------------------------------------------------------------
#  Menus: one `coro.send(None)` per frame
# ----------------------------------------------------------------------

def menu_shot(coro, name, out_dir, frames=90):
    """Plays `frames` frames of a menu screen, saves, then drops it."""
    try:
        for _ in range(frames):
            coro.send(None)
    except StopIteration:            # the screen returned on its own
        pass
    save(name, out_dir)
    coro.close()


def menus(out_dir):
    import menu

    hover((300, 250))                # over the campaign card
    menu_shot(menu.home(), "01-accueil", out_dir)
    hover((760, 260))                # over the last hull
    menu_shot(menu.ships(), "02-vaisseaux", out_dir)
    hover((480, 300))
    menu_shot(menu.sectors(), "03-secteurs", out_dir)
    hover((300, 300))
    menu_shot(menu.hangar(), "04-hangar", out_dir)
    hover((-10, -10))


# ----------------------------------------------------------------------
#  Sectors: a `Game`, updated as loop.py updates it
# ----------------------------------------------------------------------

def sustain(game):
    """Keeps the captured ships flying: a hull floor (a run of captures must
    not die mid-shot) and missiles in stock to launch."""
    from settings.balance import MISSILE_MAX

    for ship in game.ships:
        ship.hull = max(ship.hull, ship.hull_max * HULL_FLOOR)
        ship.missiles = min(MISSILE_MAX, max(ship.missiles, 3))


def arm(game, weapon, level):
    """The weapon the shot shows off: sector 1 is flown with a level 1 gun,
    which says nothing of what the game becomes."""
    for ship in game.ships:
        ship.weapon, ship.level = weapon, level


def run(game, seconds, missiles=True):
    """Simulates `seconds` of the attempt, drawing nothing."""
    launch = int(MISSILE_EVERY * FPS)
    for frame in range(int(seconds * FPS)):
        game.update(DT)
        sustain(game)
        if missiles and frame % launch == launch - 1:
            game.fire_local()


def on_screen(items):
    from settings.ui import HEIGHT, WIDTH

    return sum(1 for i in items
               if -20 < getattr(i, "x", -99) < WIDTH + 20
               and -20 < getattr(i, "y", -99) < HEIGHT + 20)


def action(game):
    """How much is happening on screen, to choose the frame to keep."""
    score = (3.0 * on_screen(game.enemies) + on_screen(game.shots)
             + 1.5 * on_screen(game.enemy_shots) + 2.5 * on_screen(game.missiles)
             + 2.0 * on_screen(game.pickups) + 0.06 * len(game.particles)
             + 0.5 * len(game.rings))
    if game.ship.has("shutdown"):
        score -= 500.0                          # stunned: engine out, guns out
    boss = game.boss
    if boss is not None and game.phase == "boss":
        score += 25.0 * boss.open               # petals open: the heart shows
        if boss.hit_flash > 0 and boss.state == "exposed":
            score -= 1000.0                     # a hit washes its petals white
    return score


def best_frame(game, seconds, missiles=True):
    """Plays `seconds` more and returns the busiest canvas of them: a shot
    taken at a fixed second lands as often as not on an empty sky."""
    from maelstrom import screen

    launch = int(MISSILE_EVERY * FPS)
    best, best_score = None, -1.0
    for frame in range(int(seconds * FPS)):
        game.update(DT)
        sustain(game)
        if missiles and frame % launch == launch - 1:
            game.fire_local()
        game.draw()
        score = action(game)
        if score > best_score:
            best_score, best = score, screen.SCREEN.copy()
    return best


def sector_shot(level_index, seconds, name, out_dir, weapon, level, window=5.0):
    """The waves of a sector, around `seconds` into the attempt."""
    from maelstrom.session.game import Game

    game = Game(level_index)
    arm(game, weapon, level)
    run(game, seconds)
    save(name, out_dir, best_frame(game, window))


def warning_shot(level_index, name, out_dir, weapon, level):
    """The "Interceptor approaching" banner, halfway through the warning."""
    from settings.balance import BOSS_WARNING
    from maelstrom.session.game import Game

    game = Game(level_index)
    arm(game, weapon, level)
    run(game, 6.0)
    go_to_boss(game)
    run(game, BOSS_WARNING * 0.45, missiles=False)
    game.draw()
    save(name, out_dir)


def go_to_boss(game):
    """Skips to the end of the sector: the Interceptor is announced."""
    game.t = game.level["duration"]
    game.enemies.clear()
    game.enter_warning()


def boss_shot(level_index, seconds, name, out_dir, weapon, level, window=12.0):
    """An Interceptor fight, `seconds` after it arrived. The window covers a
    whole armored / exposed cycle (5 s + 6 s): the shot kept is the busiest
    frame of the two, and never one where a hit has washed the petals
    white."""
    from settings.balance import BOSS_WARNING
    from maelstrom.session.game import Game

    game = Game(level_index)
    arm(game, weapon, level)
    run(game, 4.0)
    go_to_boss(game)
    run(game, BOSS_WARNING + 0.2 + seconds)
    save(name, out_dir, best_frame(game, window))


def sectors(out_dir):
    sector_shot(0, 26.0, "05-secteur-1-merope", out_dir, "pulse", 3)
    sector_shot(1, 44.0, "06-secteur-2-oracle", out_dir, "frag", 4)
    sector_shot(2, 58.0, "07-secteur-3-pleiades", out_dir, "rail", 4)
    warning_shot(3, "08-intercepteur-en-approche", out_dir, "pulse", 5)
    boss_shot(0, 6.0, "09-boss-cyclops", out_dir, "pulse", 4)
    boss_shot(3, 8.0, "10-boss-hydra", out_dir, "pulse", 5)
    boss_shot(4, 7.0, "11-titan", out_dir, "rail", 5)


def main(argv):
    lang = "fr"
    if "--lang" in argv:
        i = argv.index("--lang")
        lang = argv[i + 1]
        del argv[i:i + 2]
    out_dir = argv[0] if argv else os.path.join(ROOT, "docs", "press")
    os.makedirs(out_dir, exist_ok=True)

    setup(lang)
    print(f"captures -> {out_dir}")
    menus(out_dir)
    sectors(out_dir)
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
