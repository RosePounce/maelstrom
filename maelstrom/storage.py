"""Storage: the meta-progression, on the desktop as in the browser.

A die-and-retry has no run to save: a sector is short and starts over. What
survives is the META: the meta-alloy balance, the hangar upgrades, the
sectors unlocked, the deaths and the best time per sector, and the loadout
the ship had when it entered each sector. On the desktop, `saves/meta.json`;
in the browser (pygbag), the localStorage.

Also the game log (`log`, `setup_logging`): it writes next to the saves, in
`saves/maelstrom.log`.
"""

import json
import logging
import os
import sys

from settings.balance import DEFAULT_SHIP, MISSILE_START, SHIPS
from settings.ui import PROJECT_DIR, WEB


def _save_dir():
    """Run from the sources, the saves sit next to the project. Packaged
    (PyInstaller), that folder is read-only (Program Files, the AppImage
    mount): they go to the player's home, at the usual spot per system."""
    if not getattr(sys, "frozen", False):
        return os.path.join(PROJECT_DIR, "saves")
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "Maelstrom")
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "maelstrom")


SAVE_DIR = _save_dir()
STORE_PREFIX = "maelstrom."   # prefix of the keys in the browser storage

# Game log: one logger for the whole game, configured by setup_logging()
log = logging.getLogger("maelstrom")
LOG_FILE = (os.environ.get("MAELSTROM_LOG_FILE")
            or os.path.join(SAVE_DIR, "maelstrom.log"))


def setup_logging():
    """Configure the logger once (called at the start of `screen.init()`).

    The level is set by the environment variable `MAELSTROM_LOG`
    (`DEBUG`, `INFO`...), `WARNING` by default. Two outputs: `stdout`
    always, and `LOG_FILE` outside the browser (no durable file system
    there).
    """
    if log.handlers:                 # already configured: do not stack
        return
    level = getattr(logging, os.environ.get("MAELSTROM_LOG", "WARNING").upper(),
                    logging.WARNING)
    log.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S")
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    log.addHandler(stream)
    if not WEB:
        try:
            os.makedirs(os.path.dirname(LOG_FILE) or ".", exist_ok=True)
            file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
            file_handler.setFormatter(fmt)
            log.addHandler(file_handler)
        except OSError:
            pass                     # a read-only disk must not stop the game


def _local_storage():
    """The browser storage, or None outside the browser (or when refused)."""
    if not WEB:
        return None
    try:
        import platform as _platform
        return _platform.window.localStorage
    except Exception:
        return None


def store_read(name):
    """Reads a JSON document back, or None. `name` is a file name without path."""
    store = _local_storage()
    if store is not None:
        try:
            raw = store.getItem(STORE_PREFIX + name)
            return json.loads(raw) if raw else None
        except Exception:
            return None
    try:
        with open(os.path.join(SAVE_DIR, name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def store_write(name, data):
    """Writes a JSON document (overwriting the previous one). False on failure."""
    store = _local_storage()
    if store is not None:
        try:
            store.setItem(STORE_PREFIX + name, json.dumps(data))
        except Exception:
            log.warning("browser storage refused %s", name)
            return False
        return True
    try:
        os.makedirs(SAVE_DIR, exist_ok=True)
        with open(os.path.join(SAVE_DIR, name), "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError as err:
        log.warning("cannot write %s: %s", name, err)
        return False
    return True


# ----------------------------------------------------------------------
#  Meta-progression
# ----------------------------------------------------------------------

META_VERSION = 3
META_NAME = "meta.json"


def base_loadout(ship=DEFAULT_SHIP):
    """What the ship carries when it enters the first sector. Its starting
    weapon comes from the chosen hull."""
    weapon = SHIPS.get(ship, SHIPS[DEFAULT_SHIP])["weapon"]
    return {"weapon": weapon, "level": 1, "missiles": MISSILE_START}


def default_meta():
    return {
        "alloys": 0,
        "hangar": {},
        "ship": DEFAULT_SHIP,        # the chosen starting hull
        "progress": {},              # id -> {best, deaths, loadout, cleared}
        "liberated": [],             # ids of the regions freed (map colour)
        "won": False,
    }


def _loadout_ok(item):
    return (isinstance(item, dict) and isinstance(item.get("weapon"), str)
            and isinstance(item.get("level"), int)
            and isinstance(item.get("missiles"), int))


def _clean_entry(v):
    """A progress entry, rebuilt field by field (a damaged file cannot crash)."""
    if not isinstance(v, dict):
        return None
    best = v.get("best")
    try:
        deaths = max(0, int(v.get("deaths") or 0))
    except (TypeError, ValueError):
        deaths = 0
    lo = v.get("loadout")
    return {"best": float(best) if isinstance(best, (int, float)) else None,
            "deaths": deaths, "loadout": lo if _loadout_ok(lo) else None,
            "cleared": bool(v.get("cleared"))}


def sector_entry(meta, sid):
    """The progress entry for id `sid`, created and stored if absent."""
    return meta["progress"].setdefault(
        sid, {"best": None, "deaths": 0, "loadout": None, "cleared": False})


def read_meta():
    """Reads the meta back. Always a usable dict: every field is REBUILT, so a
    file damaged or tinkered with by hand cannot crash a screen. An older meta
    (v1 flat lists, v2 sector ids) keeps its alloys / hangar / ship; its per-
    level progress is reset -- the galaxy's region ids are a new scheme."""
    meta = default_meta()
    data = store_read(META_NAME)
    if not isinstance(data, dict):
        return meta
    try:
        meta["alloys"] = max(0, int(data.get("alloys", 0)))
        hangar = data.get("hangar", {})
        if isinstance(hangar, dict):
            meta["hangar"] = {str(k): max(0, int(v)) for k, v in hangar.items()}
        ship = data.get("ship")
        meta["ship"] = ship if ship in SHIPS else DEFAULT_SHIP
        meta["won"] = bool(data.get("won", False))
        if data.get("version") == META_VERSION:      # same scheme: keep progress
            prog = data.get("progress", {})
            if isinstance(prog, dict):
                for sid, v in prog.items():
                    entry = _clean_entry(v)
                    if entry:
                        meta["progress"][str(sid)] = entry
            lib = data.get("liberated")
            if isinstance(lib, list):
                meta["liberated"] = [str(x) for x in lib]
    except (TypeError, ValueError):
        return default_meta()
    return meta


def write_meta(meta):
    """Writes the meta (overwriting the previous one). False if refused."""
    data = dict(meta)
    data["version"] = META_VERSION
    return store_write(META_NAME, data)
