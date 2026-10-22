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

Co-op (`coop` given, see coop.py): `self.ships` holds both ships, `self.ship`
stays the LOCAL one (HUD, controls). The host (`role` "host") simulates as
solo does and sends snapshots; the client (`role` "client") simulates nothing
and draws what it receives. A ship shot down returns after COOP_RESPAWN
seconds; the attempt is lost only when both are down.
"""

import random

import pygame

from settings.balance import (
    BOSS_CLEAR_WAIT, BOSS_WARNING, BOSSES, COOP_RESPAWN, HANGAR, LEVELS,
    MISSILE_MAX, MISSILE_START,
)
from settings.ui import (
    BANNER_TIME, C_NEON_CYAN, C_NEON_RED, C_PLAYERS, C_TEXT_GRAY, HEIGHT,
    SHAKE_DECAY, WIDTH,
)
from maelstrom import audio, i18n, screen
from maelstrom.backdrop import Backdrop
from maelstrom.effects import Particle
from maelstrom.enemies import Enemy, Interceptor
from maelstrom.levels import build_script
from maelstrom.player import Ship
from maelstrom.storage import base_loadout, log, read_meta, write_meta
from maelstrom.session.bug_form import BugForm
from maelstrom.session.combat import Combat
from maelstrom.session.controls import Controls
from maelstrom.session.coop import Coop, profile
from maelstrom.session.hud import Hud


# Phases in which the world moves and the ship flies
FLYING = ("play", "warning", "boss", "boss_dying")
SPAWN_X = 140


class Game(Combat, Controls, Hud, BugForm, Coop):
    def __init__(self, level_index, coop=None, carry=None):
        """`coop`: the co-op session (coop.Session), None solo. `carry`: in
        co-op, the loadouts the ships bring from the sector just cleared."""
        self.meta = read_meta()
        self.coop = coop
        self.role = coop.role if coop else "solo"
        self.me = coop.me if coop else 0         # index of the local ship
        # who flies: ship, hangar and per-sector loadouts of each player
        self.players = coop.players if coop else [profile(self.meta)]
        self.carry = carry
        self.level_index = level_index
        self.level = LEVELS[level_index]
        self.scroll = self.level["scroll"]
        self.backdrop = Backdrop(self.level["key"])
        self.world = pygame.Surface((WIDTH, HEIGHT)).convert()
        self.exit_request = None         # "menu", "quit", "hangar", "next"
        self.next_level = level_index    # the sector main.py plays next
        self.checkpoint = None           # ship loadouts when the boss came
        self.carry_out = None            # co-op: loadouts after a cleared sector
        self.unbanked = 0                # meta-alloy not yet written to the meta
        self.next_uid = 1                # names the enemies on the network
        self.init_coop()
        self.layout_hud()
        self.build_bug_form()
        self.start(from_boss=False)

    # --- an attempt ---------------------------------------------------------

    def entry_loadout(self, i=0):
        """The loadout ship `i` had when it entered this sector."""
        if self.carry:
            return dict(self.carry[i])
        player = self.players[i]
        if self.level_index == 0:
            return base_loadout(player["ship"])
        return dict(player["loadouts"][self.level_index]
                    or base_loadout(player["ship"]))

    def spawn_y(self, i):
        if len(self.players) == 1:
            return HEIGHT * 0.45
        return HEIGHT * (0.33 + 0.26 * i)

    def make_ship(self, i, from_boss):
        player = self.players[i]
        loadout = (dict(self.checkpoint[i]) if from_boss and self.checkpoint
                   else self.entry_loadout(i))
        floor = MISSILE_START + HANGAR["missiles"]["step"] * player["hangar"].get("missiles", 0)
        loadout["missiles"] = min(MISSILE_MAX, max(loadout["missiles"], floor))
        return Ship(SPAWN_X, self.spawn_y(i), player["hangar"], loadout,
                    player["ship"], C_PLAYERS[i])

    def start(self, from_boss):
        """A new attempt: from the start of the sector, or from its
        Interceptor with the loadouts the ships had when it came."""
        self.ships = [self.make_ship(i, from_boss) for i in range(len(self.players))]
        self.ship = self.ships[self.me]
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
        self.drag = self.ship.drag       # the local controls push this one
        self.banner = None
        audio.restart()                  # every attempt starts its music over
        if self.role == "client":        # the host decides, and announces
            return
        if from_boss and self.checkpoint:
            self.t = self.level["duration"]
            self.enter_warning(checkpoint=False)
            self.phase_t = BOSS_WARNING * 0.45      # a shorter warning on a retry
        else:
            self.show_banner(["t", "banner.sector", {"n": self.level_index + 1}],
                             ["level_name", self.level["key"]], C_NEON_CYAN)
        log.info("sector %d attempt (from_boss=%s)", self.level_index + 1, from_boss)

    def show_banner(self, title, sub, color, time=BANNER_TIME):
        """`title` and `sub` are texts as data (see `i18n.text`)."""
        self.emit("banner", title, sub, color, time)
        self.banner = {"title": i18n.text(title), "sub": i18n.text(sub),
                       "color": color, "t": time, "max": time}

    def enter_warning(self, checkpoint=True):
        self.phase, self.phase_t = "warning", 0.0
        boss = self.level["boss"]
        self.show_banner(["t", "banner.boss_warning"],
                         ["t", "banner.boss_warning_sub",
                          {"name": ["boss_name", boss], "hearts": BOSSES[boss]["hearts"]}],
                         C_NEON_RED, BOSS_WARNING)
        if checkpoint:
            self.checkpoint = [ship.loadout() for ship in self.ships]
            self.float_at(WIDTH // 2, HEIGHT * 0.62, ["t", "banner.checkpoint"],
                          C_TEXT_GRAY, 2.2)

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
            "checkpoint": self.checkpoint, "kills": self.kills, "role": self.role,
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
        self.alloys_gained += amount
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
        if self.coop:                    # the ships already blew up one by one;
            self.bank()                  # the solo records stay the solo's
            self.open_overlay("dead")
            log.info("co-op sector %d: both ships down at %.0f%%",
                     self.level_index + 1, self.progress() * 100)
            return
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
        if self.coop:
            # co-op: only the meta-alloy is kept (bank); the solo records,
            # unlocks and loadouts are not touched. The loadouts go on to the
            # next co-op sector instead.
            if i + 1 < len(LEVELS):
                self.next_level = i + 1
                self.carry_out = [ship.loadout() for ship in self.ships]
            self.bank()
            self.open_overlay("cleared")
            log.info("co-op sector %d cleared in %.1f s", i + 1, self.elapsed)
            return
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

    def live_ships(self):
        return [ship for ship in self.ships if not ship.down]

    def target(self, x, y):
        """The ship a Thargoid at (x, y) goes after: the nearest one still
        flying."""
        ships = self.live_ships() or self.ships
        return min(ships, key=lambda s: (s.x - x) ** 2 + (s.y - y) ** 2)

    def update(self, dt):
        if self.role == "client":
            self.mirror_update(dt)           # draws what the host sends
            return
        if self.role == "host":
            self.host_receive()
        self.simulate(dt)
        if self.role == "host":
            self.host_send()

    def simulate(self, dt):
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

        if self.phase == "cleared":            # the ships jump out
            for ship in self.live_ships():
                ship.x += (200 + self.phase_t * 900) * dt
                self.engine_trail(ship)
        if flying:
            self.ship.axes = self.local_axes()
            for ship in self.live_ships():
                ship.update(dt, ship.axes[0], ship.axes[1], ship.drag)
                # `drag` is NOT cleared here: Ship.update spends what the cap
                # allows and leaves the rest, so a fast flick carries over.
                if ship.ready_to_fire(dt):
                    self.shots.extend(ship.volley())
                self.engine_trail(ship)
            self.update_downed(dt)

        self.shots = [s for s in self.shots if s.update(dt)]
        self.enemy_shots = [s for s in self.enemy_shots if s.update(dt)]
        for m in self.missiles:
            m.update(dt, self.missile_target(m))
        self.missiles = [m for m in self.missiles if not m.dead]
        for e in self.enemies:
            e.update(dt, self)
        self.enemies = [e for e in self.enemies if not e.gone]
        self.pickups = [p for p in self.pickups if self.update_pickup(p, dt, flying)]
        self.clouds = [c for c in self.clouds if c.update(dt)]
        self.particles = [p for p in self.particles if p.update(dt)]
        self.floats = [f for f in self.floats if f.update(dt)]
        self.rings = [r for r in self.rings if r.update(dt)]

        if flying:
            self.collide()
            if self.phase != "boss_dying":
                self.check_hulls()

    def update_pickup(self, p, dt, flying):
        """A bonus drifts to the nearest ship still flying."""
        ships = self.live_ships() if flying else []
        if not ships:
            return p.update(dt, None, 0)
        ship = min(ships, key=lambda s: (s.x - p.x) ** 2 + (s.y - p.y) ** 2)
        return p.update(dt, ship, ship.magnet)

    def check_hulls(self):
        """Solo, a hull at 0 ends the attempt. Co-op, the ship goes down and
        the attempt ends only when no ship is left."""
        if not self.coop:
            if self.ship.hull <= 0:
                self.die()
            return
        for i, ship in enumerate(self.ships):
            if not ship.down and ship.hull <= 0:
                ship.knock_down(COOP_RESPAWN)
                self.explode(ship.x, ship.y, ship.color, 60, 320)
                self.shake = max(self.shake, 12)
                self.float_at(ship.x, ship.y - 30, ["t", "coop.down", {"n": i + 1}],
                              ship.color, 1.8)
        if not self.live_ships():
            self.die()

    def update_downed(self, dt):
        """Co-op: a downed ship returns once its delay is out, as long as its
        partner still flies."""
        for i, ship in enumerate(self.ships):
            if not ship.down:
                continue
            ship.respawn_t -= dt
            if ship.respawn_t <= 0 and self.live_ships():
                ship.revive(SPAWN_X, self.spawn_y(i))
                self.ring(ship.x, ship.y, 60, ship.color, 0.5)
                self.float_at(ship.x, ship.y - 30, ["t", "coop.revived", {"n": i + 1}],
                              ship.color)

    def engine_trail(self, ship):
        if random.random() < 0.6 and not ship.has("shutdown"):
            self.particles.append(Particle(ship.x - 18, ship.y + random.uniform(-2, 2),
                                           -random.uniform(80, 160), random.uniform(-15, 15),
                                           0.28, (255, 120, 170), 2))

    def spawn_enemy(self, kind, x, y, params=None):
        enemy = Enemy(kind, x, y, self.level_index, params)
        enemy.uid = self.next_uid
        self.next_uid += 1
        self.enemies.append(enemy)

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
            for ship in self.live_ships():
                ship.draw(w)
            self.draw_tags(w)
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
