"""The player's ship: movement, hull and shield, weapons, timed effects."""

import math
import random

import pygame

from settings.balance import (
    BONUSES, HANGAR, HIT_INVULN, MALUSES, MAGNET_RADIUS, MISSILE_COOLDOWN,
    MISSILE_MAX, SHIELD_DELAY, SHIELD_REGEN, SHIP_HULL, SHIP_SHIELD,
    SHIP_SPEED, SPAWN_INVULN, WEAPONS,
)
from settings.ui import (
    C_CAUSTIC, C_NEON_CYAN, C_NEON_ORANGE, C_NEON_PINK, C_NEON_RED, C_SHIELD,
    DRAG_SPEED_CAP, PLAY_BOTTOM, PLAY_LEFT, PLAY_RIGHT, PLAY_TOP,
)
from maelstrom.neon import blit_glow, neon_polygon, rotate_points
from maelstrom.projectiles import Missile, Shot


# The ship's outline, nose to the right (x forward, y down)
HULL_SHAPE = [(20, 0), (-4, -6), (-14, -14), (-10, -3), (-10, 3), (-14, 14), (-4, 6)]
COCKPIT = [(10, 0), (2, -3), (2, 3)]


class Ship:
    def __init__(self, x, y, hangar, loadout):
        def lv(key):
            return hangar.get(key, 0)

        def step(key):
            return HANGAR[key]["step"] * lv(key)

        self.x, self.y = x, y
        self.hull_max = SHIP_HULL + step("hull")
        self.shield_max = SHIP_SHIELD + step("shield")
        self.regen = SHIELD_REGEN * (1 + step("regen"))
        self.damage_mult = 1 + step("damage")
        self.rate_mult = 1 + step("rate")
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

    def loadout(self):
        """What carries over to the next sector (and to a checkpoint)."""
        return {"weapon": self.weapon, "level": self.level,
                "missiles": self.missiles}

    def has(self, key):
        return self.effects.get(key, 0.0) > 0

    def speed(self):
        s = SHIP_SPEED
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
            # maluses): a flick does not teleport it
            cap = speed * DRAG_SPEED_CAP * dt
            mx, my = drag[0] * speed / SHIP_SPEED, drag[1] * speed / SHIP_SPEED
            dist = math.hypot(mx, my)
            if dist > cap:
                mx, my = mx / dist * cap, my / dist * cap
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

        outline = C_NEON_CYAN
        if self.flash > 0:
            outline = (255, 255, 255)
        elif shutdown:
            outline = (90, 110, 130)
        neon_polygon(surf, outline, rotate_points(HULL_SHAPE, tilt, x, y))
        pygame.draw.polygon(surf, C_NEON_PINK, rotate_points(COCKPIT, tilt, x, y))
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
