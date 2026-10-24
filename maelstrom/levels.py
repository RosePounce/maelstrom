"""The waves of a sector, written once by a SEEDED generator.

`build_script(index)` turns the sector's pattern weights (`LEVELS` in
balance.py) into a list of `Spawn`, sorted by time. The generator is seeded
with the sector's `seed`: every attempt meets the same waves at the same
moments, which is what makes a die-and-retry learnable. The drops, on the
other hand, stay random.

A pattern is a function `(t, rng) -> [Spawn]`, named after a key of the
`patterns` tables. One more pattern = one function here + its key in a
sector's table.
"""

import random
from collections import namedtuple

from settings.balance import GAP_RAMP, LEVELS
from settings.ui import PLAY_BOTTOM, PLAY_TOP, WIDTH


Spawn = namedtuple("Spawn", "t kind x y params")
SPAWN_X = WIDTH + 40


def _y(rng, margin):
    return rng.uniform(PLAY_TOP + margin, PLAY_BOTTOM - margin)


def swarm_line(t, rng):
    y = _y(rng, 50)
    amp = rng.choice((0, 18, 30))
    return [Spawn(t + i * 0.2, "swarm", SPAWN_X, y, {"amp": amp, "freq": 2.0, "home": 70})
            for i in range(5)]


def swarm_wave(t, rng):
    y = _y(rng, 110)
    return [Spawn(t + i * 0.22, "swarm", SPAWN_X, y, {"amp": 90, "freq": 2.2})
            for i in range(6)]


def swarm_v(t, rng):
    y = _y(rng, 90)
    return [Spawn(t, "swarm", SPAWN_X + abs(k) * 28, y + k * 22, {"home": 45})
            for k in range(-3, 4)]


def scout_pair(t, rng):
    y1, y2 = _y(rng, 60), _y(rng, 60)
    return [Spawn(t, "scout", SPAWN_X, y1, {"amp": 50, "phase": 0.0}),
            Spawn(t + 0.5, "scout", SPAWN_X, y2, {"amp": 50, "phase": 1.5})]


def scout_trio(t, rng):
    span = PLAY_BOTTOM - PLAY_TOP
    return [Spawn(t + i * 0.45, "scout", SPAWN_X, PLAY_TOP + span * (i + 1) / 4,
                  {"amp": 40, "phase": i * 1.1}) for i in range(3)]


def marauder(t, rng):
    return [Spawn(t, "marauder", SPAWN_X, _y(rng, 60),
                  {"target_x": WIDTH * rng.uniform(0.72, 0.86)})]


def berserker(t, rng):
    return [Spawn(t, "berserker", SPAWN_X + 20, _y(rng, 120),
                  {"target_x": WIDTH * rng.uniform(0.74, 0.86)})]


def mines(t, rng):
    return [Spawn(t + i * 0.4, "mine", SPAWN_X, _y(rng, 30),
                  {"drift": 0.7, "phase": rng.uniform(0, 6)}) for i in range(4)]


def asteroids(t, rng):
    return [Spawn(t + i * 0.6, "asteroid", SPAWN_X + 20, _y(rng, 30),
                  {"radius": rng.randint(16, 34), "drift": rng.uniform(0.8, 1.3),
                   "vy": rng.uniform(-22, 22)})
            for i in range(rng.randint(3, 5))]


PATTERNS = {f.__name__: f for f in (swarm_line, swarm_wave, swarm_v, scout_pair,
                                    scout_trio, marauder, berserker, mines,
                                    asteroids)}


def build_from(mission):
    """The spawns of one mission, sorted by time. `mission` is a dict with
    `duration`, `gap`, `seed` and `patterns` (pattern name -> weight): the same
    fields a `LEVELS` entry carries, so a sector's missions and the old flat
    sectors build the same way. Seeded, so a die-and-retry meets the same waves."""
    rng = random.Random(mission["seed"])
    names = list(mission["patterns"])
    weights = [mission["patterns"][n] for n in names]
    duration, gap = mission["duration"], mission["gap"]
    events = []
    t = 2.5
    while t < duration - 3:
        name = rng.choices(names, weights)[0]
        events.extend(PATTERNS[name](t, rng))
        t += gap * (1 - GAP_RAMP * t / duration) * rng.uniform(0.75, 1.25)
    events.sort(key=lambda e: e.t)
    return events


def build_script(index):
    """The spawns of flat sector `index` (`LEVELS`). Kept for `--verification`
    and any flat-sector path; the campaign builds per mission with `build_from`."""
    return build_from(LEVELS[index])
