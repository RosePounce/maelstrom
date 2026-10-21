"""The player's ship: movement, hull and shield, weapons, timed effects."""

import math
import random

import pygame

from settings.balance import (
    BONUSES, COOP_REVIVE_HULL, DEFAULT_SHIP, HANGAR, HIT_INVULN, MALUSES, MAGNET_RADIUS,
    MISSILE_COOLDOWN, MISSILE_MAX, SHIELD_DELAY, SHIELD_REGEN, SHIP_HITBOX,
    SHIP_HULL, SHIP_SHIELD, SHIP_SPEED, SHIPS, SPAWN_INVULN, WEAPONS,
)
from settings.ui import (
    C_CAUSTIC, C_NEON_CYAN, C_NEON_ORANGE, C_NEON_PINK, C_NEON_RED, C_SHIELD,
    DRAG_SPEED_CAP, PLAY_BOTTOM, PLAY_LEFT, PLAY_RIGHT, PLAY_TOP,
)
from maelstrom.neon import blit_glow, neon_polygon, rotate_points
from maelstrom.projectiles import Missile, Shot


# One silhouette per starting ship, TOP-DOWN, nose to the right (x forward, y
# down), traced from the Elite Dangerous size chart (docs/ship_list.jpg): the
# Krait Mk II's forked twin tusks and wide swept wings with a notched tail, the
# Alliance Chieftain's pointed nose with mid wings and rear engine nubs, the
# Type-10 Defender's huge broad delta, the Mamba's long narrow dagger.
SHIP_SHAPES = {
    "krait": {
        "hull": [(9, -1.4), (12.1, -2.8), (10, -5), (0.1, -10.3), (-12.1, -15.3),
                 (-2.2, -15.8), (-12.3, -16.1), (-19.7, -6), (-19.5, -1.5),
                 (-17.4, -1.3), (-17.4, 1.2), (-19.5, 1.4), (-19.7, 6),
                 (-12, 14.6), (-2.4, 14.5), (-12, 13.8), (0.2, 9.7),
                 (10.4, 5.4), (12, 2.1), (9.2, 0.9)],
        "cockpit": [(8, 0), (0, -3), (0, 3)],
    },
    "chieftain": {
        "hull": [(18.3, 0), (6.6, -5.5), (0.1, -12), (-4, -5), (-7.1, -5.1),
                 (-14, -10), (-12.1, -3), (-11.8, 2.2), (-14, 9.6), (-7, 4.9),
                 (-4, 5), (0.1, 12.2), (6.8, 5.1)],
        "cockpit": [(12, 0), (4, -3), (4, 3)],
    },
    "type10": {
        "hull": [(12.7, -7.2), (7.7, -11.1), (0, -17), (-14.4, -17), (-12.5, -7.2),
                 (-19.2, -7), (-19.7, 7.8), (-12, 7.9), (-14.6, 17.8), (0, 17.8),
                 (7.4, 12.3), (12.7, 7.9)],
        "cockpit": [(8, 0), (1, -4), (1, 4)],
    },
    "mamba": {
        "hull": [(27.8, 2.8), (15.8, 2.1), (15.6, -1.7), (27.9, -4.8),
                 (27.9, -7.7), (0.2, -9), (-16, -10), (-12, -3), (-14, 0),
                 (-12, 3), (-16, 10), (-7.7, 9.1), (-0.3, 8.4), (28, 5.7)],
        "cockpit": [(15, 0), (6, -2), (6, 2)],
    },
}
# default silhouette: the home-screen card art and a safe fallback
HULL_SHAPE = SHIP_SHAPES[DEFAULT_SHIP]["hull"]
COCKPIT = SHIP_SHAPES[DEFAULT_SHIP]["cockpit"]


class Ship:
    def __init__(self, x, y, hangar, loadout, ship=DEFAULT_SHIP, color=C_NEON_CYAN):
        def lv(key):
            return hangar.get(key, 0)

        def step(key):
            return HANGAR[key]["step"] * lv(key)

        self.ship_key = ship if ship in SHIPS else DEFAULT_SHIP
        p = SHIPS[self.ship_key]
        shape = SHIP_SHAPES[self.ship_key]
        self.hull_shape, self.cockpit = shape["hull"], shape["cockpit"]

        self.x, self.y = x, y
        # the ship profile scales the base stats; the hangar then adds flat on top
        self.hull_max = int(SHIP_HULL * p["hull"]) + step("hull")
        self.shield_max = int(SHIP_SHIELD * p["shield"]) + step("shield")
        self.regen = SHIELD_REGEN * (1 + step("regen"))
        self.base_speed = SHIP_SPEED * p["speed"]
        self.hitbox = SHIP_HITBOX * p["hitbox"]
        self.damage_mult = (1 + step("damage")) * p["damage"]
        self.rate_mult = (1 + step("rate")) * p["rate"]
        self.magnet = MAGNET_RADIUS + step("magnet")
        self.malus_mult = max(0.2, 1 - step("dampers"))
        self.drop_mult = 1 + step("salvage")

        self.hull = self.hull_max
        self.shield = self.shield_max
        self.weapon = loadout["weapon"]
        self.level = loadout["level"]
        self.missiles = min(MISSILE_MAX, loadout["missiles"])

        self.fire_t = 0.0
        self.missile_t = 0.0
        self.invuln = SPAWN_INVULN
        self.since_hit = 99.0
        self.effects = {}            # effect key -> seconds left
        self.flash = 0.0             # white flash of the hull after a hit
        self.shield_flash = 0.0
        self.tilt = 0.0              # -1 climbing .. 1 diving, for the drawing
        self.t = 0.0
        self.color = color           # the outline: tells the two co-op ships apart
        # what steers it: the keyboard direction and the pointer motion not
        # spent yet. The local player's come from its own controls, a co-op
        # partner's from the network.
        self.axes = (0.0, 0.0)
        self.drag = [0.0, 0.0]
        self.down = False            # co-op: shot down, waiting to return
        self.respawn_t = 0.0

    def loadout(self):
        """What carries over to the next sector (and to a checkpoint)."""
        return {"weapon": self.weapon, "level": self.level,
                "missiles": self.missiles}

    def has(self, key):
        return self.effects.get(key, 0.0) > 0

    def speed(self):
        s = self.base_speed
        if self.has("shutdown"):
            s *= MALUSES["shutdown"]["slow"]
        if self.has("jamming"):
            s *= MALUSES["jamming"]["slow"]
        return s

    def fire_interval(self):
        rate = WEAPONS[self.weapon]["rate"] * self.rate_mult
        if self.has("overcharge"):
            rate *= BONUSES["overcharge"]["rate"]
        if self.has("overheat"):
            rate *= MALUSES["overheat"]["rate"]
        return 1.0 / rate

    # --- simulation ---------------------------------------------------------

    def update(self, dt, ax, ay, drag):
        """`ax`, `ay`: keyboard direction (-1..1); `drag`: pointer motion in
        pixels since the last frame (mouse held or finger)."""
        self.t += dt
        speed = self.speed()
        dx, dy = ax * speed * dt, ay * speed * dt
        if drag[0] or drag[1]:
            # the pointer leads, but the ship keeps its top speed (and its
            # maluses): a flick does not teleport it. What the cap leaves
            # unspent STAYS in `drag`, so a fast flick is not lost -- the ship
            # catches up over the next frames instead of dropping behind.
            cap = speed * DRAG_SPEED_CAP * dt
            mx, my = drag[0] * speed / SHIP_SPEED, drag[1] * speed / SHIP_SPEED
            dist = math.hypot(mx, my)
            if dist > cap:
                f = cap / dist
                mx, my = mx * f, my * f
                drag[0] *= 1 - f           # keep the remainder for next frames
                drag[1] *= 1 - f
            else:
                drag[0] = drag[1] = 0.0
            dx += mx
            dy += my
        self.x = max(PLAY_LEFT, min(PLAY_RIGHT, self.x + dx))
        self.y = max(PLAY_TOP, min(PLAY_BOTTOM, self.y + dy))
        want = max(-1.0, min(1.0, dy / (speed * dt) if dt else 0.0))
        self.tilt += (want - self.tilt) * min(1.0, dt * 10)

        self.invuln = max(0.0, self.invuln - dt)
        self.flash = max(0.0, self.flash - dt * 4)
        self.shield_flash = max(0.0, self.shield_flash - dt * 3)
        self.missile_t = max(0.0, self.missile_t - dt)
        self.since_hit += dt
        for key in list(self.effects):
            self.effects[key] -= dt
            if self.effects[key] <= 0:
                del self.effects[key]

        if self.has("caustic"):
            self.hull -= MALUSES["caustic"]["dps"] * dt
        if self.since_hit > SHIELD_DELAY and not self.has("shutdown"):
            self.shield = min(self.shield_max, self.shield + self.regen * dt)

    def hit(self, damage):
        """A shot or a ram. The shield takes it first. False during the grace
        time after a previous hit."""
        if self.invuln > 0:
            return False
        self.since_hit = 0.0
        self.invuln = HIT_INVULN
        if self.shield > 0:
            taken = min(self.shield, damage)
            self.shield -= taken
            damage -= taken
            self.shield_flash = 1.0
        if damage > 0:
            self.hull -= damage
            self.flash = 1.0
        return True

    def knock_down(self, respawn):
        """Co-op: the ship is destroyed but comes back in `respawn` seconds
        if its partner holds on."""
        self.down = True
        self.respawn_t = respawn
        self.effects.clear()
        self.drag[0] = self.drag[1] = 0.0

    def revive(self, x, y):
        self.down = False
        self.x, self.y = x, y
        self.hull = max(1, self.hull_max * COOP_REVIVE_HULL)
        self.shield = self.shield_max
        self.invuln = SPAWN_INVULN
        self.since_hit = 99.0
        self.drag[0] = self.drag[1] = 0.0

    def add_effect(self, key, seconds, malus=False):
        if malus:
            seconds *= self.malus_mult
        self.effects[key] = max(self.effects.get(key, 0.0), seconds)

    # --- weapons ------------------------------------------------------------

    def ready_to_fire(self, dt):
        """Automatic fire: True when the next volley is due."""
        if self.has("shutdown"):
            self.fire_t = 0.0
            return False
        self.fire_t -= dt
        if self.fire_t > 0:
            return False
        self.fire_t += self.fire_interval()
        if self.fire_t < 0:              # a long pause must not queue volleys
            self.fire_t = 0.0
        return True

    def volley(self):
        """The shots of one volley of the weapon in hand, at its level."""
        w = WEAPONS[self.weapon]
        lvl = self.level - 1
        nose_x = self.x + 20
        dmg = w["damage"] * self.damage_mult
        shots = []
        if self.weapon == "pulse":
            for oy, deg in w["levels"][lvl]:
                a = math.radians(deg)
                shots.append(Shot(nose_x, self.y + oy, math.cos(a) * w["speed"],
                                  math.sin(a) * w["speed"], dmg, "pulse"))
        elif self.weapon == "frag":
            count, spread = w["pellets"][lvl], w["spread"][lvl]
            for i in range(count):
                deg = -spread / 2 + spread * i / max(1, count - 1)
                deg += random.uniform(-2, 2)
                a = math.radians(deg)
                sp = w["speed"] * random.uniform(0.85, 1.1)
                shots.append(Shot(nose_x, self.y, math.cos(a) * sp, math.sin(a) * sp,
                                  dmg, "frag", radius=3, life=w["life"]))
        else:
            dmg *= w["mult"][lvl]
            for oy in w["levels"][lvl]:
                shots.append(Shot(nose_x, self.y + oy, w["speed"], 0, dmg, "rail",
                                  radius=4, pierce=True))
        return shots

    def launch_missiles(self):
        """Space: one stock, a pair of AX missiles. [] when not possible."""
        if self.missiles <= 0 or self.missile_t > 0 or self.has("shutdown"):
            return []
        self.missiles -= 1
        self.missile_t = MISSILE_COOLDOWN
        return [Missile(self.x, self.y - 8, -0.6, self.damage_mult),
                Missile(self.x, self.y + 8, 0.6, self.damage_mult)]

    # --- drawing ------------------------------------------------------------

    def draw(self, surf):
        if self.invuln > 0 and int(self.invuln * 20) % 2 == 0:
            return                           # blinking during the grace time
        x, y = self.x, self.y
        tilt = self.tilt * 0.22
        shutdown = self.has("shutdown")

        # engine flame
        flicker = 0.75 + 0.25 * math.sin(self.t * 40)
        flame_col = C_NEON_RED if self.has("overheat") else C_NEON_ORANGE
        if not shutdown:
            length = 14 * flicker
            pts = rotate_points([(-10, -3), (-10 - length, 0), (-10, 3)], tilt, x, y)
            pygame.draw.polygon(surf, flame_col, pts)
            blit_glow(surf, x - 16, y, 16, C_NEON_PINK, 0.6 * flicker)

        outline = self.color
        if self.flash > 0:
            outline = (255, 255, 255)
        elif shutdown:
            outline = (90, 110, 130)
        neon_polygon(surf, outline, rotate_points(self.hull_shape, tilt, x, y))
        pygame.draw.polygon(surf, C_NEON_PINK, rotate_points(self.cockpit, tilt, x, y))
        pygame.draw.circle(surf, (255, 255, 255), (int(x), int(y)), 2)   # the hitbox

        if self.shield > 0 and self.shield_flash > 0:
            r = 26
            col = tuple(int(c * self.shield_flash) for c in C_SHIELD)
            pygame.draw.ellipse(surf, col, (x - r, y - r * 0.75, r * 2, r * 1.5), 2)
        if self.has("caustic") and random.random() < 0.3:
            blit_glow(surf, x + random.uniform(-14, 10), y + random.uniform(-8, 8),
                      8, C_CAUSTIC, 0.6)
        if shutdown and random.random() < 0.5:
            a = random.uniform(0, math.tau)
            pygame.draw.line(surf, (190, 220, 255), (x, y),
                             (x + math.cos(a) * 22, y + math.sin(a) * 16), 1)
