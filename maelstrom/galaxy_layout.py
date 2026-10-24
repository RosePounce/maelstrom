"""The galaxy layout: the Milky Way cut into REGIONS, each a territory on the
map made of four SECTORS plus a Titan.

Hierarchy -- galaxy -> regions -> sectors:
  - a REGION owns a set of grid cells (its shape on the polar map), a name, and
    (for the start region) a `start` flag -- the "Bubble" the campaign begins
    from. Freeing a region (beating its Titan) opens its NEIGHBOURS.
  - a region holds four SECTORS, each a level like the originals (waves + its
    own Interceptor: Cyclops / Basilisk / Medusa / Hydra), and a TITAN played
    once the four are freed. Beating the Titan frees the region.

A sector / the Titan is a "level dict" (`key`, `boss`, `scroll`, `duration`,
`gap`, `seed`, `patterns`, and `spec` for the Titan) -- exactly what `Game`
plays. Region 1 (the Bubble) reuses the hand-written `LEVELS` as its four
sectors and the finale as its Titan.

The layout is read from `saves/galaxy_layout.json` (the editor) when present,
else a built-in default is generated once by a seeded carve.
"""

import random

from settings.balance import LEVELS
from maelstrom import storage
from maelstrom.galaxy import COLS, RINGS


LAYOUT_FILE = "galaxy_layout.json"
CARVE_SEED = 0x0DE
DEFAULT_REGIONS = 5

_GENERIC_PATTERNS = {"scout_trio": 2, "marauder": 3, "berserker": 2,
                     "swarm_v": 2, "mines": 1}
_INTERCEPTORS = ("cyclops", "basilisk", "medusa", "hydra")
_BACKDROPS = ("merope", "oracle", "pleiades", "maelstrom")


def _carve(n):
    """Partition the polar grid into `n` regions with jagged, grid-following
    borders. Returns `cell[ring][col]` (the owning region) and `outer[col]`."""
    rng = random.Random(CARVE_SEED)
    outer = []
    while len(outer) < COLS:
        level = RINGS - rng.choice((0, 0, 0, 1))
        for _ in range(rng.randint(3, 7)):
            if len(outer) < COLS:
                outer.append(level)
    col_per = COLS / n
    bcol = [[0] * RINGS for _ in range(n)]
    for b in range(n):
        base = round(b * col_per)
        c = base
        for k in range(RINGS):
            c = max(base - 2, min(base + 2, c + rng.choice((-1, 0, 0, 1))))
            bcol[b][k] = c % COLS
    cell = [[-1] * COLS for _ in range(RINGS)]
    for k in range(RINGS):
        for b in range(n):
            m, end = bcol[b][k], bcol[(b + 1) % n][k]
            for _ in range(COLS):
                if k < outer[m % COLS]:
                    cell[k][m % COLS] = b
                m += 1
                if m % COLS == end:
                    break
    return cell, outer


def _sector_from(level):
    """A region sector from a hand-written LEVELS entry (keeps its Interceptor)."""
    return {"key": level["key"], "boss": level["boss"], "scroll": level["scroll"],
            "duration": level["duration"], "gap": level["gap"],
            "seed": level["seed"], "patterns": dict(level["patterns"])}


def _titan_from(level):
    """The region's Titan level from the finale LEVELS entry."""
    return {"key": level["key"], "boss": "titan", "scroll": level["scroll"],
            "duration": level["duration"], "gap": level["gap"],
            "seed": level["seed"], "patterns": dict(level["patterns"]),
            "spec": {"boss": "titan"}}


def _generic_sectors(r):
    return [{"key": _BACKDROPS[s], "boss": _INTERCEPTORS[s], "scroll": 160,
             "duration": 40, "gap": 1.6, "seed": 1000 * (r + 1) + s,
             "patterns": dict(_GENERIC_PATTERNS)} for s in range(4)]


def _generic_titan(r):
    return {"key": ("titan", "maelstrom")[r % 2], "boss": "titan", "scroll": 200,
            "duration": 30, "gap": 1.7, "seed": 5000 + r, "patterns": dict(_GENERIC_PATTERNS),
            "spec": {"boss": "titan", "skin": ("violet", "cyan", "crimson")[r % 3]}}


def _default():
    """The built-in layout: region 1 (the Bubble) reuses the hand-written
    campaign; the rest are generic Thargoid regions to reconquer."""
    builtin = [lv for lv in LEVELS if not lv.get("finale")]
    finale = next((lv for lv in LEVELS if lv.get("finale")), builtin[-1])
    cell, _ = _carve(DEFAULT_REGIONS)
    regions = []
    for r in range(DEFAULT_REGIONS):
        cells = [[k, m] for m in range(COLS) for k in range(RINGS) if cell[k][m] == r]
        if r == 0:
            regions.append({
                "id": "bubble", "name": "La Bulle", "start": True, "cells": cells,
                "sectors": [_sector_from(lv) for lv in builtin],
                "titan": _titan_from(finale)})
        else:
            regions.append({
                "id": f"region{r + 1}", "name": f"Region {r + 1}", "cells": cells,
                "sectors": _generic_sectors(r), "titan": _generic_titan(r)})
    return regions


def _valid(data):
    return (isinstance(data, list) and data
            and all(isinstance(s, dict) and isinstance(s.get("cells"), list)
                    and isinstance(s.get("sectors"), list) for s in data))


def load_layout():
    """The authored layout from disk, or the built-in default. Always usable:
    a damaged file falls back to the default rather than crashing the map."""
    data = storage.store_read(LAYOUT_FILE)
    return data if _valid(data) else _default()


def save_layout(regions):
    """Persist a layout (the editor). False if the disk refused."""
    return storage.store_write(LAYOUT_FILE, regions)


def new_region(name):
    """A fresh, empty region for the editor: four generic sectors and a Titan,
    no cells yet. Paint its shape, then it takes its place on the map."""
    sid = "reg-" + format(random.randrange(1 << 24), "06x")
    return {"id": sid, "name": name, "cells": [],
            "sectors": _generic_sectors(0), "titan": _generic_titan(0)}


# --- identity and content ----------------------------------------------------

def region_id(region):
    return region.get("id") or region.get("name") or "?"


def sector_id(region, i):
    """The stable id a sector files its progress under."""
    return f"{region_id(region)}:{i}"


def titan_id(region):
    return f"{region_id(region)}:titan"


def sector_level(region, i):
    """The level dict `Game` plays for sector `i` of a region."""
    return region["sectors"][i]


def titan_level(region):
    return region["titan"]


# --- adjacency (the conquest front) ------------------------------------------

def _touch(cells_a, set_b):
    for k, m in cells_a:
        if ((k + 1, m) in set_b or (k - 1, m) in set_b
                or (k, (m + 1) % COLS) in set_b or (k, (m - 1) % COLS) in set_b):
            return True
    return False


def adjacency(regions):
    """For each region, the set of indices of the regions it borders on the
    grid -- how the conquest front spreads from the Bubble to its neighbours."""
    sets = [{(k, m) for k, m in r["cells"]} for r in regions]
    adj = [set() for _ in regions]
    for i in range(len(regions)):
        for j in range(i + 1, len(regions)):
            if _touch(regions[i]["cells"], sets[j]):
                adj[i].add(j)
                adj[j].add(i)
    return adj
