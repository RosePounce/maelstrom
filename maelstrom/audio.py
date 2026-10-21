"""Music: one track at a time, streamed by `pygame.mixer.music`.

The screens do not start or stop tracks: they say which one should be
playing, on every frame if they like (`music(key)`), and nothing happens
while it already is. A sector asks for the track of its phase
(`Game.music_track()`); `restart()` makes the next request start over from
the top, which is what a new attempt wants. A looping track cut by another
one (the pause music, the hangar) takes up where it stopped when it is asked
for again.

The volume is a player preference, kept in `prefs.json` beside the language.
Without an audio device, or with a file missing, the game simply stays
silent.
"""

import os

import pygame

from settings.ui import (
    MUSIC, MUSIC_DIR, MUSIC_FADE_IN, MUSIC_FADE_OUT, MUSIC_VOLUME, MUSIC_VOLUMES,
)
from maelstrom import storage
from maelstrom.storage import log


PREFS = "prefs.json"
EXTENSIONS = (".ogg", ".mp3")

_current = None               # key of the track asked for last
_start = 0.0                  # where it started in its file, seconds
_left = None                  # (key, seconds): the looping track cut last
_volume = MUSIC_VOLUME


def _ready():
    """True if music can play; opens the mixer once if `pygame.init()` did
    not (no audio device: False, and the game stays silent)."""
    if pygame.mixer.get_init():
        return True
    try:
        pygame.mixer.init()
    except pygame.error:
        return False
    return bool(pygame.mixer.get_init())


def _path(name):
    for ext in EXTENSIONS:
        path = os.path.join(MUSIC_DIR, name + ext)
        if os.path.isfile(path):
            return path
    return None


def init():
    """Reads the volume back. To be called after `pygame.init()`."""
    global _volume
    doc = storage.store_read(PREFS)
    if isinstance(doc, dict) and isinstance(doc.get("music"), (int, float)):
        _volume = max(0.0, min(1.0, float(doc["music"])))
    if _ready():
        pygame.mixer.music.set_volume(_volume)


def music(key):
    """Makes `key` the track playing (a key of `MUSIC`); None fades out.
    Asking again for the track already asked for does nothing."""
    global _current, _start, _left
    if key == _current:
        return
    resume = _left[1] if _left and _left[0] == key else 0.0
    if _ready() and _current in MUSIC and MUSIC[_current][1] and pygame.mixer.music.get_busy():
        _left = (_current, _start + pygame.mixer.music.get_pos() / 1000.0)
    _current = key
    if not _ready():
        return
    if key is None:
        pygame.mixer.music.fadeout(MUSIC_FADE_OUT)
        return
    if key not in MUSIC:
        pygame.mixer.music.stop()
        log.info("music %r: not in MUSIC", key)
        return
    name, loop = MUSIC[key]
    path = _path(name)
    if path is None:
        pygame.mixer.music.stop()
        log.info("music %r: no file %s.ogg / .mp3", key, name)
        return
    _start = resume
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(_volume)
        _play(loop)
    except pygame.error as err:
        log.warning("music %r cannot play: %s", key, err)


def _play(loop):
    """Plays the loaded track from `_start`. Past the end of the file (it had
    looped), from the top."""
    global _start
    loops, fade = (-1, MUSIC_FADE_IN) if loop else (0, 0)
    try:
        pygame.mixer.music.play(loops, start=_start, fade_ms=fade)
    except pygame.error:
        _start = 0.0
        pygame.mixer.music.play(loops, fade_ms=fade)


def restart():
    """The next `music()` call starts its track from the top, even the same
    one."""
    global _current, _left
    _current = ""
    _left = None


def volume():
    return _volume


def next_volume():
    """The next step of MUSIC_VOLUMES, remembered for the next launches."""
    global _volume
    steps = MUSIC_VOLUMES
    higher = [v for v in steps if v > _volume + 1e-6]
    _volume = higher[0] if higher else steps[0]
    if _ready():
        pygame.mixer.music.set_volume(_volume)
    doc = storage.store_read(PREFS)
    if not isinstance(doc, dict):
        doc = {}
    doc["music"] = _volume
    storage.store_write(PREFS, doc)
    return _volume
