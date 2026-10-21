"""Bug reports written by the game itself, one folder per report.

Two ways in: `Game` opens a one-line form (F8, or "Signaler un bug" in the
pause menu), and `main.py` catches a crash. Both end in `write_report`, which
drops into `saves/bugs/<timestamp>/`:

  report.md    what happened: description, context, traceback if any
  screen.png   the screen at the moment of the bug
  state.json   a snapshot of the attempt (`Game.state_data`)
  log.txt      the tail of the game log (`storage.LOG_FILE`)

There is no run save in Maelstrom: `state.json` is a DIAGNOSTIC snapshot
(sector, phase, sector clock, ship, enemies, Interceptor), not a file the
game can load back. A sector is replayed from its start, its waves being
seeded: the sector clock `t` says where in it the bug happened.

Desktop only: in the browser (pygbag) there is no durable file system.
`ENABLED` is what every caller checks.

Everything here is defensive: a report is written while something is already
going wrong, so a missing piece (no screenshot, a state that fails to
serialize) is noted in the report instead of raising.
"""

import datetime
import json
import os
import subprocess
import traceback

import pygame

from settings import GAME_NAME
from settings.ui import PROJECT_DIR, WEB
from maelstrom.storage import LOG_FILE, SAVE_DIR, log, read_meta


ENABLED = not WEB
REPORT_DIR = os.path.join(SAVE_DIR, "bugs")
LOG_TAIL_LINES = 200
DESCRIPTION_MAX_LEN = 200     # the form is a single line


def git_commit():
    """Short hash of the checked-out commit (with "+dirty" if the project
    folder has local changes), or "unknown" outside a git checkout."""
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=PROJECT_DIR, capture_output=True, text=True,
                              timeout=2)
        if head.returncode != 0:
            return "unknown"
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "."],
                               cwd=PROJECT_DIR, capture_output=True, text=True,
                               timeout=2)
        return head.stdout.strip() + ("+dirty" if dirty.stdout.strip() else "")
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def log_tail(lines=LOG_TAIL_LINES):
    """The last `lines` lines of the game log, or "" if there is none."""
    try:
        with open(LOG_FILE, encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-lines:])
    except OSError:
        return ""


def capture_screen():
    """A copy of the canvas as it is now, or None (no display yet)."""
    from maelstrom import screen
    try:
        return screen.SCREEN.copy() if screen.SCREEN is not None else None
    except pygame.error:
        return None


def game_state(game):
    """(state dict, error text): the attempt snapshot, or None and why."""
    if game is None:
        return None, "no game running"
    try:
        return game.state_data(), None
    except Exception:
        return None, traceback.format_exc()


def _meta_rows():
    """The meta-progression, read from its file (it survives the attempts)."""
    try:
        meta = read_meta()
        hangar = ", ".join(f"{k} {v}" for k, v in sorted(meta["hangar"].items())
                           if v) or "none"
        return [("meta alloys", str(meta["alloys"])),
                ("meta hangar", hangar),
                ("meta sectors open", str(meta["unlocked"])),
                ("meta deaths per sector", ", ".join(str(d) for d in meta["deaths"]))]
    except Exception:
        return [("meta error", traceback.format_exc().strip())]


def game_context(game):
    """[(label, value)] describing where the attempt stands, for report.md."""
    if game is None:
        return [("game", "none (menus)")] + _meta_rows()
    rows = []
    try:
        ship = game.ship
        level = game.level
        rows += [
            ("sector", f"{game.level_index + 1} ({level['key']})"),
            ("mode", game.role + (f", local ship {game.me + 1}" if game.coop else "")),
            ("phase", f"{game.phase} ({game.phase_t:.1f} s)"
                      + (f", overlay {game.overlay}" if game.overlay else "")),
            ("sector clock", f"{game.t:.1f} / {level['duration']} s "
                             f"(spawn {game.script_i}/{len(game.script)})"),
            ("attempt time", f"{game.elapsed:.1f} s"),
            ("hull", f"{ship.hull:.0f} / {ship.hull_max:.0f}"),
            ("shield", f"{ship.shield:.0f} / {ship.shield_max:.0f}"),
            ("weapon", f"{ship.weapon} level {ship.level}, AX {ship.missiles}"),
            ("effects", ", ".join(f"{k} {v:.1f} s" for k, v in sorted(ship.effects.items()))
                        or "none"),
            ("enemies / enemy shots", f"{len(game.enemies)} / {len(game.enemy_shots)}"),
            ("pickups", str(len(game.pickups))),
            ("checkpoint", str(game.checkpoint) if game.checkpoint else "none"),
            ("kills", str(game.kills)),
            ("alloys this attempt", str(game.attempt_alloys)),
        ]
        if game.boss is not None:
            b = game.boss
            rows.append(("interceptor", f"{b.key} {b.state}, heart {b.heart}/{b.hearts} "
                                        f"({b.heart_hp:.0f} / {b.heart_hp_max:.0f})"))
    except Exception:
        rows.append(("context error", traceback.format_exc().strip()))
    return rows + _meta_rows()


def _new_folder():
    """A fresh folder named after the current time (a suffix if taken)."""
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(REPORT_DIR, stamp)
    n = 2
    while os.path.exists(path):
        path = os.path.join(REPORT_DIR, f"{stamp}-{n}")
        n += 1
    os.makedirs(path)
    return path


def write_report(description, game=None, shot=None, state=None,
                 state_error=None, context=None, trace=None, kind="manual"):
    """Write one report folder. Returns its path, or None if nothing could be
    written (browser, read-only disk).

    `shot`, `state` and `context` are passed in when they were taken EARLIER
    than now (the form captures them when it opens, before drawing itself
    over the frozen game); otherwise they are taken here. `kind` is "manual"
    or "crash".
    """
    if not ENABLED:
        return None
    try:
        folder = _new_folder()
    except OSError:
        log.exception("bug report: cannot create a folder in %s", REPORT_DIR)
        return None
    if shot is None:
        shot = capture_screen()
    if state is None and state_error is None:
        state, state_error = game_state(game)

    notes = []
    if shot is not None:
        try:
            pygame.image.save(shot, os.path.join(folder, "screen.png"))
        except pygame.error as err:
            notes.append(f"screenshot not saved: {err}")
    else:
        notes.append("no screenshot (no display)")
    if state is not None:
        try:
            with open(os.path.join(folder, "state.json"), "w",
                      encoding="utf-8") as f:
                json.dump(state, f, indent=1)
        except (OSError, TypeError, ValueError) as err:
            notes.append(f"state not saved: {err}")
    else:
        notes.append("no game state: " + (state_error or "unknown").strip())
    tail = log_tail()
    if tail:
        try:
            with open(os.path.join(folder, "log.txt"), "w",
                      encoding="utf-8") as f:
                f.write(tail)
        except OSError as err:
            notes.append(f"log not saved: {err}")
    else:
        notes.append("no log (empty or missing log file)")

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"# {GAME_NAME} - {'crash' if kind == 'crash' else 'bug report'}",
             "",
             f"- date: {now}",
             f"- commit: {git_commit()}"]
    if context is None:
        context = game_context(game)
    lines += [f"- {label}: {value}" for label, value in context]
    lines += ["", "## Description", "", description.strip() or "(none)"]
    if trace:
        lines += ["", "## Traceback", "", "```text", trace.rstrip(), "```"]
    lines += ["", "## Files", ""]
    lines += [f"- `{name}`" for name in ("screen.png", "state.json", "log.txt")
              if os.path.exists(os.path.join(folder, name))]
    if notes:
        lines += ["", "## Missing", ""] + [f"- {n}" for n in notes]
    try:
        with open(os.path.join(folder, "report.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        log.exception("bug report: cannot write report.md in %s", folder)
        return None
    log.warning("bug report written: %s", folder)
    return folder


def report_crash(game=None):
    """Called from an `except` block: write a crash report for the exception
    being handled. Never raises; returns the folder or None."""
    try:
        return write_report("Crash: the game stopped on an uncaught exception.",
                            game=game, trace=traceback.format_exc(),
                            kind="crash")
    except Exception:
        log.exception("bug report: the crash report itself failed")
        return None
