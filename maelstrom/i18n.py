"""Translation of everything the player reads.

One language = one JSON file in `maelstrom/locales/`: "fr.json", "en.json"...
Adding one only takes dropping a file there; the code keeps no list of
languages. On the desktop the player may also drop a file into
`<saves>/locales/`, which translates the game without rebuilding it; on a name
clash, theirs wins.

Keys are hierarchical, written with dots:

    i18n.t("dead.progress", pct=63)
    i18n.boss_name("hydra")

French is the reference: a key missing from the current language is taken from
there, and a key missing everywhere is returned as is -- visible on screen
rather than silently empty.

The game's proper name and version are NOT here: they are constants in
`settings` (a proper noun is the same in every language). This module only
borrows `GAME_NAME` to build the window caption.
"""

import json
import locale as _locale
import os
import sys

from settings import GAME_NAME
from maelstrom import storage

REFERENCE = "fr"              # reference language, and fallback for all others
_BUILTIN = ("fr", "en")       # always findable, even if listdir is flaky (web)

_catalogs = {}                # code -> loaded catalog
_files = None                 # code -> file path, None = not scanned yet
_language = REFERENCE


# ---------------------------------------------------------------- catalogs ----
def locale_dirs():
    """Folders searched for languages, lowest priority first."""
    dirs = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales")]
    try:
        dirs.append(os.path.join(storage.SAVE_DIR, "locales"))
    except Exception:
        pass
    return dirs


def _scan(force=False):
    """The language files found: {code: path}. The builtin codes are probed
    by name as well, so the browser always finds them even when `listdir`
    does not enumerate the bundled folder."""
    global _files
    if _files is not None and not force:
        return _files
    found = {}
    for folder in locale_dirs():
        if os.path.isdir(folder):
            try:
                names = sorted(os.listdir(folder))
            except OSError:
                names = []
            for name in names:
                if name.startswith("_") or not name.endswith(".json"):
                    continue
                found[name[:-5].lower()] = os.path.join(folder, name)
        for code in _BUILTIN:
            if code not in found:
                path = os.path.join(folder, code + ".json")
                if os.path.isfile(path):
                    found[code] = path
    _files = found
    return found


def catalog(code):
    """A language catalog, loaded once. {} when unreadable."""
    code = (code or "").lower()
    if code in _catalogs:
        return _catalogs[code]
    path = _scan().get(code)
    data = {}
    if path:
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            print("Unreadable language \"%s\" (%s): %s" % (code, path, exc),
                  file=sys.stderr)
    if not isinstance(data, dict):
        data = {}
    _catalogs[code] = data
    return data


def reload():
    """Forget the in-memory catalogs: useful after editing a file."""
    _catalogs.clear()
    _scan(force=True)


def available():
    """Installed languages: [(code, name in that language), ...], reference first."""
    out = []
    for code in _scan():
        name = _lookup(catalog(code), "language.name")
        out.append((code, name if isinstance(name, str) else code.upper()))
    out.sort(key=lambda item: (item[0] != REFERENCE, item[1].lower()))
    return out


def codes():
    """The codes of the installed languages, in display order."""
    return [code for code, _name in available()]


# ----------------------------------------------------------------- lookup ----
def _lookup(node, key):
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def data(key, default=None):
    """The raw value of a key: a string, a list or a dictionary."""
    for code in (_language, REFERENCE):
        value = _lookup(catalog(code), key)
        if value is not None:
            return value
    return default


def _format(value, fields):
    if not fields:
        return value
    try:
        return value.format(**fields)
    except (KeyError, IndexError, ValueError):
        return value              # a bad field: the raw text beats nothing


def t(key, **fields):
    """The text of a key, with its fields: `t("dead.progress", pct=63)`."""
    value = data(key)
    if not isinstance(value, str):
        return key
    return _format(value, fields)


def lines(key):
    """A list of strings (a paragraph the translator split up)."""
    value = data(key)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if isinstance(value, str):
        return [value]
    return []


# -------------------------------------------------------- current language ----
def language():
    return _language


def language_name(code=None):
    code = code or _language
    name = _lookup(catalog(code), "language.name")
    return name if isinstance(name, str) else code.upper()


def set_language(code):
    """Pick the language. Returns the one actually applied."""
    global _language
    code = (code or "").lower()
    _language = code if code in _scan() else REFERENCE
    return _language


def next_language(code=None):
    """The next language in the list, for a button that cycles through them."""
    order = codes() or [REFERENCE]
    try:
        index = order.index(code or _language)
    except ValueError:
        return order[0]
    return order[(index + 1) % len(order)]


def window_caption():
    """The window title: the proper name, then the translated subtitle."""
    return "%s - %s" % (GAME_NAME, t("game.subtitle"))


# --------------------------------------------------------- player's choice ----
def preference():
    """The language remembered at the last launch, or None."""
    doc = storage.store_read("prefs.json")
    if isinstance(doc, dict) and isinstance(doc.get("language"), str):
        return doc["language"].lower()
    return None


def remember(code):
    """Remember the language for the next games. Silent on failure."""
    doc = storage.store_read("prefs.json")
    if not isinstance(doc, dict):
        doc = {}
    doc["language"] = code
    return storage.store_write("prefs.json", doc)


def _system_tags():
    """The language tags the system advertises, the most reliable first."""
    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(name)
        if value:
            for tag in value.split(":"):
                if tag:
                    yield tag
    try:
        tag = _locale.getdefaultlocale()[0]
    except (ValueError, TypeError, OSError):
        tag = None
    if tag:
        yield tag


def detect():
    """The language to use: remembered choice, else the system one, else French."""
    installed = _scan()
    saved = preference()
    if saved in installed:
        return saved
    try:
        for tag in _system_tags():
            code = tag.split(".")[0].replace("-", "_").split("_")[0].lower()
            if code in installed:
                return code
    except Exception:
        pass
    return REFERENCE


# -------------------------------------------------- labels of the game data ----
def _text(key, fallback):
    value = data(key)
    return value if isinstance(value, str) else fallback


def level_name(key):
    return _text("levels.%s.name" % key, key)


def level_lore(key):
    return _text("levels.%s.lore" % key, "")


def boss_name(key):
    return _text("bosses.%s" % key, key)


def weapon_name(key):
    return _text("weapons.%s.name" % key, key)


def weapon_letter(key):
    return _text("weapons.%s.letter" % key, "")


def pickup_name(key):
    return _text("pickups.%s.name" % key, key)


def pickup_letter(key):
    return _text("pickups.%s.letter" % key, "")


def pickup_info(key):
    return _text("pickups.%s.info" % key, "")


def pickup_tag(key):
    return _text("pickups.%s.tag" % key, "")


def effect_label(key):
    return _text("effects.%s" % key, key)


def hangar_name(key):
    return _text("hangar.items.%s.name" % key, key)


def hangar_desc(key):
    return _text("hangar.items.%s.desc" % key, "")


def ship_name(key):
    return _text("ships.%s.name" % key, key)


def ship_desc(key):
    return _text("ships.%s.desc" % key, "")


# ---------------------------------------------------------- texts as data ----
# A text can also be written as DATA, to be translated later: the co-op host
# sends its banners and floating texts this way, so that each machine shows
# them in its own language. A spec is
#   - a plain string, shown as is;
#   - ["t", key, {fields}]   -> t(key, **fields), a field may itself be a spec;
#   - [label, key]           -> one of the label functions below.
_LABELS = {"level_name": level_name, "boss_name": boss_name,
           "weapon_name": weapon_name, "pickup_name": pickup_name}


def text(spec):
    """The text a spec describes, in the current language."""
    if isinstance(spec, str):
        return spec
    try:
        name, key = spec[0], spec[1]
        if name == "t":
            fields = spec[2] if len(spec) > 2 else {}
            return t(key, **{k: text(v) if isinstance(v, list) else v
                             for k, v in fields.items()})
        return _LABELS[name](key)
    except (IndexError, KeyError, TypeError, AttributeError):
        return str(spec)
