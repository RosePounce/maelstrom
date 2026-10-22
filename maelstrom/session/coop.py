"""Two-player co-op on a local network: the host decides, the client mirrors.

Maelstrom is not deterministic (the global `random` drives drops, sparks and
the Thargoids' jitter), so it does not play in lockstep like purr-tage: the
HOST simulates the sector exactly as solo does, with a second ship steered by
the network, and sends a SNAPSHOT of it on every frame. The CLIENT simulates
nothing: it sends its inputs, draws the last snapshot and replays the visual
effects the host recorded (`Combat.emit`), so that each machine translates
the texts in its own language and keeps its own particles.

Messages (JSON, over `net.Link`):
  hello    client -> host   protocol, name, profile (ship, hangar, loadouts)
  welcome  host -> client   the host's name    / refuse: different versions
  start    host -> client   the sector, the two profiles
  input    client -> host   direction, pointer motion, missile presses
  snap     host -> client   the whole sector, plus the effects of the frame
  level    host -> client   the next sector (after "sector freed")
  bye      either side      leaving

Each player keeps their own meta: their ship, hangar and per-sector loadouts
fly, the meta-alloy gathered by the team is banked on BOTH sides, and the
solo records (deaths, best times, unlocks) are left alone.
"""

from settings.balance import (
    DEFAULT_SHIP, HANGAR, LEVELS, MISSILE_MAX, SHIPS, WEAPON_MAX_LEVEL, WEAPONS,
)
from settings.ui import SHAKE_DECAY
from maelstrom.enemies import Enemy, Interceptor, asteroid_shape
from maelstrom.pickups import Pickup
from maelstrom.projectiles import CausticCloud, Missile, Shot
from maelstrom.storage import log


# ----------------------------------------------------------------------
#  Players and session
# ----------------------------------------------------------------------

def profile(meta):
    """What a player brings to a game: hull, hangar, loadout per sector."""
    return {"ship": meta["ship"], "hangar": dict(meta["hangar"]),
            "loadouts": list(meta["loadouts"])}


def _loadout(item):
    if not isinstance(item, dict) or item.get("weapon") not in WEAPONS:
        return None
    try:
        return {"weapon": item["weapon"],
                "level": max(1, min(WEAPON_MAX_LEVEL, int(item["level"]))),
                "missiles": max(0, min(MISSILE_MAX, int(item["missiles"])))}
    except (KeyError, TypeError, ValueError):
        return None


def clean_profile(data):
    """A profile received from the network, rebuilt field by field: a
    partner's bad data must not crash the game."""
    data = data if isinstance(data, dict) else {}
    ship = data.get("ship")
    hangar = {}
    if isinstance(data.get("hangar"), dict):
        for key, level in data["hangar"].items():
            if key in HANGAR:
                try:
                    hangar[key] = max(0, min(HANGAR[key]["max"], int(level)))
                except (TypeError, ValueError):
                    pass
    loadouts = data.get("loadouts")
    loadouts = loadouts if isinstance(loadouts, list) else []
    return {"ship": ship if ship in SHIPS else DEFAULT_SHIP, "hangar": hangar,
            "loadouts": [_loadout(loadouts[i]) if i < len(loadouts) else None
                         for i in range(len(LEVELS))]}


class Session:
    """The link of a co-op game, from the lobby to the return to the menu.
    `players[0]` is the host, `players[1]` the client; `me` is the local one.
    Messages read but meant for the next sector are put back (`unread`)."""

    def __init__(self, link, role, players, partner=""):
        self.link = link
        self.role = role                 # "host" or "client"
        self.me = 0 if role == "host" else 1
        self.players = players
        self.partner = partner           # the other side's name, for the lobby
        self.backlog = []

    @property
    def alive(self):
        return self.link.alive

    def send(self, message):
        return self.link.send(message)

    def messages(self):
        out = self.backlog + self.link.poll()
        self.backlog = []
        return out

    def unread(self, messages):
        self.backlog = list(messages) + self.backlog

    def close(self):
        self.link.close()


# ----------------------------------------------------------------------
#  Snapshot encoding
# ----------------------------------------------------------------------

SHOT_KINDS = ("pulse", "frag", "rail", "enemy")
SHIPS_SHOWN = ("play", "warning", "boss", "boss_dying", "cleared")


def _r(v, digits=1):
    return round(v, digits)


def _shot(s):
    return [SHOT_KINDS.index(s.kind), round(s.x), round(s.y), round(s.vx),
            round(s.vy), s.radius]


def _ship(s):
    return [_r(s.x), _r(s.y), _r(s.tilt, 2), _r(s.invuln, 2), _r(s.flash, 2),
            _r(s.shield_flash, 2), _r(s.hull), _r(s.shield),
            {k: _r(v) for k, v in s.effects.items()}, s.weapon, s.level,
            s.missiles, _r(s.missile_t, 2), s.down, _r(s.respawn_t), _r(s.t, 2)]


def _enemy(e):
    return [e.uid, e.kind, _r(e.x), _r(e.y), e.radius, _r(e.hp), _r(e.hit_flash, 2),
            _r(e.angle, 2), _r(e.age, 2), e.freq, e.amp, e.phase, e.state,
            _r(e.state_t, 2), e.seed]


def _boss(b):
    return [b.key, _r(b.x), _r(b.y), b.state, _r(b.state_t, 2), _r(b.t, 2),
            _r(b.open, 3), _r(b.hit_flash, 2), b.heart, _r(b.heart_hp)]


def _mirror_enemy(kind, radius, seed):
    """An enemy for the client to draw: no behaviour, only what `draw` and
    the bug report read (set by `apply_snapshot`)."""
    e = Enemy.__new__(Enemy)
    e.kind, e.radius, e.seed = kind, radius, seed
    if kind == "asteroid":
        e.shape = asteroid_shape(radius, seed)
    return e


# ----------------------------------------------------------------------
#  The Game side
# ----------------------------------------------------------------------

class Coop:

    def init_coop(self):
        self.fx = []                     # host: effects of the frame, for the client
        self.alloys_gained = 0           # host: everything gathered in this sector
        self.alloys_seen = 0             # client: the part already credited
        self.host_overlay = None         # client: "dead" / "cleared" on the host
        self.missile_presses = 0         # client: AX presses not sent yet
        self.mirror = {}                 # client: uid -> mirrored enemy

    def net_lost(self):
        """The partner left or the link broke: the game stops here, and what
        was gathered is banked."""
        if self.overlay == "lost":
            return
        log.info("co-op: link lost (%s)", self.coop.link.error or "partner left")
        self.bank()
        self.paused = True
        self.open_overlay("lost")

    # --- host ---------------------------------------------------------------

    def host_receive(self):
        """The partner's inputs: its ship steers like the local one."""
        mate = self.ships[1]
        for msg in self.coop.messages():
            kind = msg.get("type")
            if kind == "input":
                try:
                    ax = max(-1.0, min(1.0, float(msg.get("ax", 0))))
                    ay = max(-1.0, min(1.0, float(msg.get("ay", 0))))
                    dx, dy = float(msg.get("dx", 0)), float(msg.get("dy", 0))
                    presses = min(3, int(msg.get("fire", 0)))
                except (TypeError, ValueError):
                    continue
                mate.axes = (ax, ay)
                if not mate.down:
                    mate.drag[0] += dx
                    mate.drag[1] += dy
                for _ in range(presses):
                    self.fire_missiles(mate)
            elif kind == "bye":
                self.net_lost()
        if not self.coop.alive:
            self.net_lost()

    def host_send(self):
        if self.overlay == "lost":
            return
        self.coop.send(self.snapshot())
        self.fx = []

    def snapshot(self):
        boss = self.boss if self.phase in ("boss", "boss_dying") else None
        return {
            "type": "snap",
            "phase": self.phase, "phase_t": _r(self.phase_t, 2),
            "t": _r(self.t, 2), "elapsed": _r(self.elapsed, 2),
            "kills": self.kills, "alloys": self.attempt_alloys,
            "total": self.alloys_gained, "shake": _r(self.shake),
            "checkpoint": bool(self.checkpoint),
            "overlay": self.overlay if self.overlay in ("dead", "cleared") else None,
            "ships": [_ship(s) for s in self.ships],
            "enemies": [_enemy(e) for e in self.enemies],
            "boss": _boss(boss) if boss else None,
            "shots": [_shot(s) for s in self.shots],
            "eshots": [_shot(s) for s in self.enemy_shots],
            "missiles": [[round(m.x), round(m.y), _r(m.angle, 2)] for m in self.missiles],
            "pickups": [[p.cat, p.key, round(p.x), round(p.y), _r(p.t, 2), _r(p.life, 2)]
                        for p in self.pickups],
            "clouds": [[round(c.x), round(c.y), _r(c.life, 2), _r(c.t, 2)]
                       for c in self.clouds],
            "fx": self.fx,
        }

    # --- client -------------------------------------------------------------

    def mirror_update(self, dt):
        """The client's frame: read the host, move the purely visual things,
        send the local inputs."""
        if self.overlay != "lost":
            messages = self.coop.messages()
            last = None
            for i, msg in enumerate(messages):
                kind = msg.get("type")
                if kind == "snap":
                    last = msg
                    self.replay(msg.get("fx", []))
                elif kind == "level":
                    self.exit_request = "next"
                    self.next_level = int(msg.get("level", self.level_index))
                    self.coop.unread(messages[i + 1:])   # the next sector's
                    break
                elif kind == "bye":
                    self.net_lost()
                    break
            if last is not None and self.overlay != "lost":
                self.apply_snapshot(last)
            if not self.coop.alive:
                self.net_lost()

        self.backdrop.update(dt, self.scroll)
        self.shake = max(0.0, self.shake - SHAKE_DECAY * dt)
        if self.banner:
            self.banner["t"] -= dt
            if self.banner["t"] <= 0:
                self.banner = None
        if self.phase in SHIPS_SHOWN:
            for ship in self.live_ships():
                self.engine_trail(ship)
        self.particles = [p for p in self.particles if p.update(dt)]
        self.floats = [f for f in self.floats if f.update(dt)]
        self.rings = [r for r in self.rings if r.update(dt)]

        if self.overlay != "lost" and self.exit_request is None:
            ax, ay = self.local_axes()
            self.coop.send({"type": "input", "ax": _r(ax, 3), "ay": _r(ay, 3),
                            "dx": _r(self.drag[0]), "dy": _r(self.drag[1]),
                            "fire": self.missile_presses})
            self.drag[0] = self.drag[1] = 0.0
            self.missile_presses = 0

    def replay(self, events):
        """The host's visual effects, played again here."""
        for ev in events:
            try:
                name, args = ev[0], ev[1:]
                if name == "spark":
                    self.spark(args[0], args[1], tuple(args[2]))
                elif name == "explode":
                    self.explode(args[0], args[1], tuple(args[2]), args[3], args[4])
                elif name == "ring":
                    self.ring(args[0], args[1], args[2], tuple(args[3]), args[4], args[5])
                elif name == "float":
                    self.float_at(args[0], args[1], args[2], tuple(args[3]), args[4])
                elif name == "banner":
                    self.show_banner(args[0], args[1], tuple(args[2]), args[3])
            except (IndexError, TypeError, ValueError):
                continue

    def apply_snapshot(self, m):
        self.phase, self.phase_t = m["phase"], m["phase_t"]
        self.t, self.elapsed, self.kills = m["t"], m["elapsed"], m["kills"]
        self.attempt_alloys = m["alloys"]
        self.shake = max(self.shake, m["shake"])
        self.checkpoint = [None] if m["checkpoint"] else None
        if m["total"] > self.alloys_seen:            # the team's gains, banked here too
            self.unbanked += m["total"] - self.alloys_seen
            self.alloys_seen = m["total"]

        for ship, row in zip(self.ships, m["ships"]):
            (ship.x, ship.y, ship.tilt, ship.invuln, ship.flash, ship.shield_flash,
             ship.hull, ship.shield, ship.effects, ship.weapon, ship.level,
             ship.missiles, ship.missile_t, ship.down, ship.respawn_t, ship.t) = row

        enemies, mirror = [], {}
        for row in m["enemies"]:
            uid, kind, radius, seed = row[0], row[1], row[4], row[14]
            e = self.mirror.get(uid) or _mirror_enemy(kind, radius, seed)
            (e.uid, e.kind, e.x, e.y, e.radius, e.hp, e.hit_flash, e.angle, e.age,
             e.freq, e.amp, e.phase, e.state, e.state_t, e.seed) = row
            enemies.append(e)
            mirror[uid] = e
        self.enemies, self.mirror = enemies, mirror

        b = m["boss"]
        if b is None:
            self.boss = None
        else:
            if self.boss is None or self.boss.key != b[0]:
                self.boss = Interceptor(b[0], self.level_index)
            boss = self.boss
            (_, boss.x, boss.y, boss.state, boss.state_t, boss.t, boss.open,
             boss.hit_flash, boss.heart, boss.heart_hp) = b

        self.shots = [Shot(x, y, vx, vy, 0, SHOT_KINDS[k], radius=r)
                      for k, x, y, vx, vy, r in m["shots"]]
        self.enemy_shots = [Shot(x, y, vx, vy, 0, "enemy", radius=r)
                            for _, x, y, vx, vy, r in m["eshots"]]
        self.missiles = [Missile(x, y, a, 1.0) for x, y, a in m["missiles"]]
        pickups = []
        for cat, key, x, y, t, life in m["pickups"]:
            p = Pickup(x, y, cat, key)
            p.t, p.life = t, life
            pickups.append(p)
        self.pickups = pickups
        clouds = []
        for x, y, life, t in m["clouds"]:
            c = CausticCloud(x, y, 0)
            c.life, c.t = life, t
            clouds.append(c)
        self.clouds = clouds

        overlay = m["overlay"]
        if overlay != self.host_overlay:
            self.host_overlay = overlay
            if overlay:                  # dead or freed: bank, then wait for the host
                self.bank()
                self.open_overlay(overlay)
            elif self.overlay in ("dead", "cleared"):
                self.overlay = None      # the host retried
                self.overlay_buttons = []
