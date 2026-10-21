"""The Game class: one sector, from its first wave to its Interceptor.

`Game` is a composition: each base class comes from a file of this folder,
has no state and no `__init__`, and only provides methods that read and
write `self`. The state is created here only: the interface by `__init__`,
an attempt by `start()`.

The phases of an attempt (`self.phase`):
  play        the waves scroll by, until the sector's `duration`;
  warning     "Interceptor approaching" (the checkpoint is taken here);
  boss        the Interceptor fights;
  boss_dying  its explosions, the ship cannot be hurt any more;
  dead        the ship is destroyed: retry overlay;
  cleared     the sector is freed: next / hangar / menu overlay.
"""

import random

import pygame

from settings.balance import (
    BOSS_CLEAR_WAIT, BOSS_WARNING, BOSSES, HANGAR, LEVELS, MISSILE_MAX,
    MISSILE_START,
)
from settings.ui import (
    BANNER_TIME, C_NEON_CYAN, C_NEON_RED, C_TEXT_GRAY, HEIGHT, SHAKE_DECAY,
    WIDTH,
)
from maelstrom import audio, i18n, screen
from maelstrom.backdrop import Backdrop
from maelstrom.effects import FloatText, Particle
from maelstrom.enemies import Enemy, Interceptor
from maelstrom.levels import build_script
from maelstrom.player import Ship
from maelstrom.storage import base_loadout, log, read_meta, write_meta
from maelstrom.session.bug_form import BugForm
from maelstrom.session.combat import Combat
from maelstrom.session.controls import Controls
from maelstrom.session.hud import Hud


# Phases in which the world moves and the ship flies
FLYING = ("play", "warning", "boss", "boss_dying")


class Game(Combat, Controls, Hud, BugForm):
    def __init__(self, level_index):
        self.meta = read_meta()
        self.level_index = level_index
        self.level = LEVELS[level_index]
        self.scroll = self.level["scroll"]
        self.backdrop = Backdrop(self.level["key"])
        self.world = pygame.Surface((WIDTH, HEIGHT)).convert()
        self.exit_request = None         # "menu", "quit", "hangar", "next"
        self.next_level = level_index    # the sector main.py plays next
        self.checkpoint = None           # ship loadout when the boss came
        self.unbanked = 0                # meta-alloy not yet written to the meta
        self.layout_hud()
        self.build_bug_form()
        self.start(from_boss=False)

    # --- an attempt ---------------------------------------------------------

    def entry_loadout(self):
        """The loadout the ship had when it entered this sector."""
        if self.level_index == 0:
            return base_loadout(self.meta["ship"])
        return dict(self.meta["loadouts"][self.level_index]
                    or base_loadout(self.meta["ship"]))

    def start(self, from_boss):
        """A new attempt: from the start of the sector, or from its
        Interceptor with the loadout the ship had when it came."""
        loadout = dict(self.checkpoint) if from_boss and self.checkpoint else self.entry_loadout()
        floor = MISSILE_START + HANGAR["missiles"]["step"] * self.meta["hangar"].get("missiles", 0)
        loadout["missiles"] = min(MISSILE_MAX, max(loadout["missiles"], floor))
        self.ship = Ship(140, HEIGHT * 0.45, self.meta["hangar"], loadout,
                         self.meta["ship"])
        self.script = build_script(self.level_index)
        self.script_i = 0
        self.t = 0.0                     # sector clock: drives the waves
        self.elapsed = 0.0               # time of this attempt
        self.enemies, self.shots, self.enemy_shots = [], [], []
        self.missiles, self.pickups, self.clouds = [], [], []
        self.particles, self.floats, self.rings = [], [], []
        self.boss = None
        self.phase, self.phase_t = "play", 0.0
        self.kills = 0
        self.attempt_alloys = 0
        self.shake = 0.0
        self.paused = False
        self.overlay = None              # "pause", "dead", "cleared"
        self.overlay_buttons = []
        self.pointer = None
        self.drag = [0.0, 0.0]
        self.banner = None
        audio.restart()                  # every attempt starts its music over
        if from_boss and self.checkpoint:
            self.t = self.level["duration"]
            self.enter_warning(checkpoint=False)
            self.phase_t = BOSS_WARNING * 0.45      # a shorter warning on a retry
        else:
            self.show_banner(i18n.t("banner.sector", n=self.level_index + 1),
                             i18n.level_name(self.level["key"]), C_NEON_CYAN)
        log.info("sector %d attempt (from_boss=%s)", self.level_index + 1, from_boss)

    def show_banner(self, title, sub, color, time=BANNER_TIME):
        self.banner = {"title": title, "sub": sub, "color": color,
                       "t": time, "max": time}

    def enter_warning(self, checkpoint=True):
        self.phase, self.phase_t = "warning", 0.0
        boss = self.level["boss"]
        self.show_banner(i18n.t("banner.boss_warning"),
                         i18n.t("banner.boss_warning_sub", name=i18n.boss_name(boss),
                                hearts=BOSSES[boss]["hearts"]),
                         C_NEON_RED, BOSS_WARNING)
        if checkpoint:
            self.checkpoint = self.ship.loadout()
            self.floats.append(FloatText(WIDTH // 2, HEIGHT * 0.62,
                                         i18n.t("banner.checkpoint"), C_TEXT_GRAY, 2.2))

    def progress(self):
        return min(1.0, self.t / self.level["duration"])

    def music_track(self):
        """The key of `MUSIC` this phase calls for (None: fade out). Asked on
        every frame by loop.py; `audio.music()` ignores a repeat."""
        phase = self.phase
        if self.paused:
            return "pause"               # the sector track resumes after it
        if phase == "play":
            return self.level["key"]
        if phase == "boss":
            return self.level["boss"]
        if phase == "boss_dying":
            return None                  # fades out under the explosions
        if phase == "cleared" and self.level_index + 1 == len(LEVELS):
            return "credits"
        return phase                     # "warning", "dead", "cleared"

    def state_data(self):
        """A snapshot of the attempt, for the bug reports (`state.json`).
        Diagnostic only: there is no run save to load it back into."""
        ship = self.ship
        boss = None
        if self.boss is not None:
            b = self.boss
            boss = {"key": b.key, "state": b.state, "state_t": round(b.state_t, 2),
                    "heart": b.heart, "hearts": b.hearts,
                    "heart_hp": round(b.heart_hp, 1), "x": round(b.x), "y": round(b.y)}
        return {
            "sector": self.level_index, "key": self.level["key"],
            "phase": self.phase, "phase_t": round(self.phase_t, 2),
            "overlay": self.overlay, "paused": self.paused,
            "t": round(self.t, 2), "elapsed": round(self.elapsed, 2),
            "script_i": self.script_i, "script_len": len(self.script),
            "checkpoint": self.checkpoint, "kills": self.kills,
            "attempt_alloys": self.attempt_alloys, "unbanked": self.unbanked,
            "ship": {"x": round(ship.x), "y": round(ship.y),
                     "hull": round(ship.hull, 1), "hull_max": ship.hull_max,
                     "shield": round(ship.shield, 1), "shield_max": ship.shield_max,
                     "weapon": ship.weapon, "level": ship.level,
                     "missiles": ship.missiles, "invuln": round(ship.invuln, 2),
                     "effects": {k: round(v, 2) for k, v in ship.effects.items()}},
            "boss": boss,
            "enemies": [{"kind": e.kind, "x": round(e.x), "y": round(e.y),
                         "hp": round(e.hp, 1), "state": e.state}
                        for e in self.enemies],
            "pickups": [{"cat": p.cat, "key": p.key, "x": round(p.x), "y": round(p.y)}
                        for p in self.pickups],
            "clouds": len(self.clouds), "shots": len(self.shots),
            "missiles": len(self.missiles), "enemy_shots": len(self.enemy_shots),
        }

    # --- the bank of meta-alloy ---------------------------------------------

    def gain_alloys(self, amount):
        self.unbanked += amount
        self.attempt_alloys += amount

    def bank(self):
        """Writes what was gathered to the meta. Called on death, on a cleared
        sector and on every way out: nothing gathered is ever lost."""
        if self.unbanked:
            self.meta["alloys"] += self.unbanked
            self.unbanked = 0
        write_meta(self.meta)

    def die(self):
        self.phase, self.phase_t = "dead", 0.0
        self.explode(self.ship.x, self.ship.y, C_NEON_CYAN, 60, 320)
        self.shake = 16
        self.meta["deaths"][self.level_index] += 1
        self.bank()
        self.open_overlay("dead")
        log.info("sector %d: ship destroyed at %.0f%%", self.level_index + 1,
                 self.progress() * 100)

    def clear_sector(self):
        i = self.level_index
        self.phase, self.phase_t = "cleared", 0.0
        best = self.meta["best"][i]
        if best is None or self.elapsed < best:
            self.meta["best"][i] = round(self.elapsed, 1)
        if i + 1 < len(LEVELS):
            self.meta["unlocked"] = max(self.meta["unlocked"], i + 2)
            self.meta["loadouts"][i + 1] = self.ship.loadout()
            self.next_level = i + 1
        else:
            self.meta["won"] = True
        self.bank()
        self.open_overlay("cleared")
        log.info("sector %d cleared in %.1f s", i + 1, self.elapsed)

    # --- simulation ---------------------------------------------------------

    def update(self, dt):
        if self.paused:
            return
        self.phase_t += dt
        self.backdrop.update(dt, self.scroll)
        self.shake = max(0.0, self.shake - SHAKE_DECAY * dt)
        if self.banner:
            self.banner["t"] -= dt
            if self.banner["t"] <= 0:
                self.banner = None

        flying = self.phase in FLYING
        if flying:
            self.elapsed += dt
        if self.phase == "play":
            self.t += dt
            while (self.script_i < len(self.script)
                   and self.script[self.script_i].t <= self.t):
                s = self.script[self.script_i]
                self.spawn_enemy(s.kind, s.x, s.y, s.params)
                self.script_i += 1
            if self.t >= self.level["duration"]:
                ships_left = any(e.kind not in ("asteroid", "mine") for e in self.enemies)
                if not ships_left or self.t >= self.level["duration"] + BOSS_CLEAR_WAIT:
                    self.enter_warning()
        elif self.phase == "warning":
            if self.phase_t >= BOSS_WARNING:
                self.boss = Interceptor(self.level["boss"], self.level_index)
                self.phase, self.phase_t = "boss", 0.0
        elif self.phase == "boss":
            self.boss.update(dt, self)
        elif self.phase == "boss_dying":
            self.update_boss_death(dt)

        if self.phase == "cleared":            # the ship jumps out
            self.ship.x += (200 + self.phase_t * 900) * dt
            self.engine_trail()
        if flying:
            ax, ay = self.input_axes()
            self.ship.update(dt, ax, ay, self.drag)
            # `drag` is NOT cleared here: Ship.update spends what the cap allows
            # and leaves the rest, so a fast flick carries over and catches up.
            if self.ship.ready_to_fire(dt):
                self.shots.extend(self.ship.volley())
            self.engine_trail()

        self.shots = [s for s in self.shots if s.update(dt)]
        self.enemy_shots = [s for s in self.enemy_shots if s.update(dt)]
        for m in self.missiles:
            m.update(dt, self.missile_target(m))
        self.missiles = [m for m in self.missiles if not m.dead]
        for e in self.enemies:
            e.update(dt, self)
        self.enemies = [e for e in self.enemies if not e.gone]
        ship = self.ship if flying else None
        self.pickups = [p for p in self.pickups if p.update(dt, ship, self.ship.magnet)]
        self.clouds = [c for c in self.clouds if c.update(dt)]
        self.particles = [p for p in self.particles if p.update(dt)]
        self.floats = [f for f in self.floats if f.update(dt)]
        self.rings = [r for r in self.rings if r.update(dt)]

        if flying:
            self.collide()
            if self.ship.hull <= 0 and self.phase != "boss_dying":
                self.die()

    def engine_trail(self):
        if random.random() < 0.6 and not self.ship.has("shutdown"):
            self.particles.append(Particle(self.ship.x - 18, self.ship.y + random.uniform(-2, 2),
                                           -random.uniform(80, 160), random.uniform(-15, 15),
                                           0.28, (255, 120, 170), 2))

    def spawn_enemy(self, kind, x, y, params=None):
        self.enemies.append(Enemy(kind, x, y, self.level_index, params))

    # --- drawing ------------------------------------------------------------

    def draw(self):
        w = self.world
        self.backdrop.draw(w)
        for c in self.clouds:
            c.draw(w)
        for p in self.pickups:
            p.draw(w)
        for s in self.shots:
            s.draw(w)
        for m in self.missiles:
            m.draw(w)
        for e in self.enemies:
            e.draw(w)
        if self.boss and self.phase in ("boss", "boss_dying"):
            self.boss.draw(w)
        if self.phase in FLYING or self.phase == "cleared":
            self.ship.draw(w)
        for s in self.enemy_shots:
            s.draw(w)
        for r in self.rings:
            r.draw(w)
        for p in self.particles:
            p.draw(w)
        for f in self.floats:
            f.draw(w)

        out = screen.SCREEN
        out.fill((0, 0, 0))
        ox = oy = 0
        if self.shake > 0:
            ox = int(random.uniform(-self.shake, self.shake))
            oy = int(random.uniform(-self.shake, self.shake))
        out.blit(w, (ox, oy))
        self.draw_jamming(out)
        self.draw_hud(out)
        self.draw_banner(out)
        if self.overlay:
            self.draw_overlay(out)
        if self.showing_bug_form:
            self.draw_bug_form(out)
        self.draw_notice(out)
        out.blit(screen.SCANLINES, (0, 0))
