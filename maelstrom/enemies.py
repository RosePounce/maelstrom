"""The Thargoids: the common ships, and the Interceptors (the bosses).

An enemy never imports the session: it receives `game` in argument and asks
it to fire (`game.enemy_fire`) or to spawn (`game.spawn_enemy`).
"""

import math
import random

import pygame

from settings.balance import (
    BOSS_ARMOR, BOSS_ARMORED_TIME, BOSS_EXPOSED_TIME, BOSS_SHOT_SPEED,
    BOSS_STAGGER, BOSSES, ENEMIES, LEVEL_DAMAGE_SCALE, LEVEL_HP_SCALE,
)
from settings.ui import (
    BOSS_LOOKS, C_CAUSTIC, C_HEART, C_HEART_COLD, C_NEON_PURPLE, C_NEON_RED,
    C_THARG, C_THARG_DARK, HEIGHT, PLAY_BOTTOM, PLAY_TOP, WIDTH,
)
from maelstrom.neon import blit_glow, lerp_color, neon_polygon, rotate_points


# Outlines, nose to the LEFT: the Thargoids come from the right
SHAPES = {
    "swarm": [(-9, 0), (0, -7), (8, -4), (8, 4), (0, 7)],
    "scout": [(-16, 0), (-4, -6), (6, -14), (4, -4), (12, 0), (4, 4), (6, 14), (-4, 6)],
    "marauder": [(-22, 0), (-2, -7), (14, -12), (8, 0), (14, 12), (-2, 7)],
    "berserker": [(-24, 0), (-8, -13), (8, -20), (18, -7), (18, 7), (8, 20), (-8, 13)],
}


def petal_points(cx, cy, ang, inner, outer, width, swirl, tip):
    """An Interceptor petal: a veined leaf from `inner` to `outer`, bending by
    `swirl` radians along its length (the pinwheel sweep of the models). `tip`
    shapes the end: "round" tapers to a point, "spike" extends a long sharp
    point (Hydra), "barb" hooks it sideways like a claw (Medusa). Returns a
    closed polygon outline in world coordinates."""
    left, right = [], []
    steps = 6
    for i in range(1, steps):
        t = i / steps
        d = inner + (outer - inner) * t
        a = ang + swirl * t
        w = width * math.sin(math.pi * t)          # 0 at base and tip, wide mid
        nx, ny = -math.sin(a), math.cos(a)
        px, py = cx + math.cos(a) * d, cy + math.sin(a) * d
        left.append((px + nx * w, py + ny * w))
        right.append((px - nx * w, py - ny * w))
    base = (cx + math.cos(ang) * inner, cy + math.sin(ang) * inner)
    a_tip = ang + swirl
    if tip == "spike":
        d_tip = outer + width * 1.7
        tip_pt = (cx + math.cos(a_tip) * d_tip, cy + math.sin(a_tip) * d_tip)
    elif tip == "barb":
        bx = cx + math.cos(a_tip) * (outer + width * 0.3)
        by = cy + math.sin(a_tip) * (outer + width * 0.3)
        nx, ny = -math.sin(a_tip), math.cos(a_tip)
        tip_pt = (bx + nx * width * 1.5, by + ny * width * 1.5)   # hooked to one side
    else:
        tip_pt = (cx + math.cos(a_tip) * outer, cy + math.sin(a_tip) * outer)
    return [base] + left + [tip_pt] + right[::-1]


class Enemy:
    """A Thargoid ship (or a mine, or an asteroid). Its behaviour is the
    method `_<kind>`, called on every frame."""

    def __init__(self, kind, x, y, level_index, params=None):
        d = ENEMIES[kind]
        p = params or {}
        self.kind = kind
        self.x, self.y = x, y
        self.y0 = y
        self.radius = p.get("radius", d["radius"])
        size = (self.radius / d["radius"]) ** 2          # big asteroids last
        self.hp_max = d["hp"] * (1 + LEVEL_HP_SCALE * level_index) * size
        self.hp = self.hp_max
        self.speed = d["speed"] * p.get("speed_mult", 1.0)
        self.contact = d["contact"] * (1 + LEVEL_DAMAGE_SCALE * level_index)
        self.alloy = d["alloy"]
        self.drop = d["drop"]
        self.fire_every = d.get("fire", 0.0)
        self.fire_t = self.fire_every * random.uniform(0.4, 1.0)
        self.shot_speed = d.get("shot_speed", 0)
        self.amp = p.get("amp", 0.0)
        self.freq = p.get("freq", 1.6)
        self.phase = p.get("phase", 0.0)
        self.drift = p.get("drift", 1.0)
        self.home = p.get("home", 0.0)       # px/s the path bends towards the ship
        self.vy = p.get("vy", 0.0)
        self.target_x = p.get("target_x", WIDTH * 0.8)
        self.age = 0.0
        self.state = "enter"
        self.state_t = 0.0
        self.hit_flash = 0.0
        self.angle = 0.0
        self.spin = random.uniform(-1.2, 1.2)
        self.gone = False            # left the screen: removed without a kill
        if kind == "asteroid":
            rng = random.Random(int(x * 7 + y * 13))
            n = 9
            self.shape = [(math.cos(i * math.tau / n) * self.radius * rng.uniform(0.75, 1.1),
                           math.sin(i * math.tau / n) * self.radius * rng.uniform(0.75, 1.1))
                          for i in range(n)]

    # --- behaviour ----------------------------------------------------------

    def update(self, dt, game):
        self.age += dt
        self.state_t += dt
        self.hit_flash = max(0.0, self.hit_flash - dt * 5)
        getattr(self, "_" + self.kind)(dt, game)
        if self.x < -90 or self.x > WIDTH + 260 or not -140 < self.y < HEIGHT + 140:
            self.gone = True

    def _sine(self, dt):
        self.x -= self.speed * dt
        self.y = self.y0 + self.amp * math.sin(self.freq * self.age + self.phase)

    def _swarm(self, dt, game):
        if self.home and self.x > game.ship.x + 60:
            step = self.home * dt
            self.y0 += max(-step, min(step, game.ship.y - self.y0))
        self._sine(dt)

    def _scout(self, dt, game):
        self._sine(dt)
        self._fire_aimed(dt, game, 1, 0.0)

    def _marauder(self, dt, game):
        if self.state == "enter":
            self.x -= self.speed * 1.4 * dt
            if self.x <= self.target_x:
                self.state, self.state_t = "track", 0.0
        elif self.state == "track":                 # lines up with the ship
            dy = game.ship.y - self.y
            step = 170 * dt
            self.y += max(-step, min(step, dy))
            if self.state_t > 1.1:
                self.state, self.state_t = "aim", 0.0
        elif self.state == "aim":                   # telegraph, then charge
            if self.state_t > 0.45:
                self.state, self.state_t = "dash", 0.0
        else:
            self.x -= ENEMIES["marauder"]["dash"] * dt

    def _berserker(self, dt, game):
        if self.state == "enter":
            self.x -= self.speed * 1.5 * dt
            if self.x <= self.target_x:
                self.state, self.state_t = "hover", 0.0
        elif self.state == "hover":
            self.y = self.y0 + 70 * math.sin(self.state_t * 0.9)
            self.y = max(PLAY_TOP + 30, min(PLAY_BOTTOM - 30, self.y))
            self._fire_aimed(dt, game, 3, 0.26)
            if self.state_t > ENEMIES["berserker"]["stay"]:
                self.state, self.state_t = "leave", 0.0
        else:
            self.x -= self.speed * (1.0 + self.state_t * 2.5) * dt

    def _mine(self, dt, game):
        self.x -= game.scroll * self.drift * dt
        self.y = self.y0 + 10 * math.sin(self.age * 2.2 + self.phase)
        self.y0 += self.vy * dt

    def _asteroid(self, dt, game):
        self.x -= game.scroll * self.drift * dt
        self.y += self.vy * dt
        self.angle += self.spin * dt

    def _fire_aimed(self, dt, game, count, spread):
        if self.x > WIDTH - 10 or self.x < 80:
            return
        self.fire_t -= dt
        if self.fire_t > 0:
            return
        self.fire_t = self.fire_every
        base = math.atan2(game.ship.y - self.y, game.ship.x - self.x)
        for i in range(count):
            a = base + (i - (count - 1) / 2) * spread
            game.enemy_fire(self.x - self.radius, self.y, a, self.shot_speed)

    # --- drawing ------------------------------------------------------------

    def draw(self, surf):
        x, y = self.x, self.y
        white = self.hit_flash > 0
        if self.kind == "asteroid":
            col = (255, 255, 255) if white else lerp_color(C_NEON_PURPLE, (90, 70, 110), 0.45)
            neon_polygon(surf, col, rotate_points(self.shape, self.angle, x, y),
                         2, (24, 16, 34))
            return
        if self.kind == "mine":
            pulse = 0.5 + 0.5 * math.sin(self.age * 6)
            col = (255, 255, 255) if white else lerp_color(C_THARG, C_CAUSTIC, pulse)
            for i in range(8):
                a = i * math.tau / 8 + self.age
                pygame.draw.line(surf, col, (x + math.cos(a) * 8, y + math.sin(a) * 8),
                                 (x + math.cos(a) * 15, y + math.sin(a) * 15), 2)
            pygame.draw.circle(surf, C_THARG_DARK, (int(x), int(y)), 9)
            pygame.draw.circle(surf, col, (int(x), int(y)), 9, 2)
            blit_glow(surf, x, y, 18, C_CAUSTIC, 0.3 + 0.3 * pulse)
            return

        tilt = 0.0
        if self.kind in ("swarm", "scout"):
            tilt = math.cos(self.freq * self.age + self.phase) * self.amp * 0.004
        col = (255, 255, 255) if white else C_THARG
        neon_polygon(surf, col, rotate_points(SHAPES[self.kind], tilt, x, y), 2, C_THARG_DARK)
        core = 3 if self.kind == "swarm" else 5
        blit_glow(surf, x + 2, y, core * 4, C_HEART, 0.55)
        pygame.draw.circle(surf, C_HEART, (int(x + 2), int(y)), core)
        if self.kind == "marauder" and self.state == "aim":
            # the charge line: the player has under half a second
            if int(self.state_t * 16) % 2 == 0:
                pygame.draw.line(surf, C_NEON_RED, (x - 24, y), (0, y), 1)


class Interceptor:
    """A Thargoid Interceptor: a rosette of veined petals around a heart.

    Its look -- petal count, colors, petal tips -- comes from `BOSS_LOOKS[key]`,
    true to the Elite Dangerous models (Cyclops, Basilisk, Medusa, Hydra).
    ARMORED (petals closed, takes BOSS_ARMOR of the damage) and EXPOSED (heart
    open, full damage) alternate; each heart destroyed staggers it (no
    damage) before the next heart. It fires its patterns in turn."""

    def __init__(self, key, level_index):
        b = BOSSES[key]
        self.key = key
        self.hearts = b["hearts"]
        self.heart = 1                       # the heart being shot, 1-based
        self.heart_hp_max = b["heart_hp"]
        self.heart_hp = self.heart_hp_max
        self.radius = b["radius"]
        self.period = b["period"]
        self.patterns = b["patterns"]
        self.pattern_i = 0
        self.level_index = level_index
        self.x, self.y = WIDTH + self.radius * 2.5, HEIGHT * 0.45
        self.target_x = WIDTH * 0.8
        self.state = "enter"
        self.state_t = 0.0
        self.open = 0.0                      # petals: 0 closed .. 1 open
        self.attack_t = 1.6
        self.spin = 0.0                      # rotation of the radial rings
        self.spiral_t = 0.0
        self.spiral_a = 0.0
        self.spiral_emit = 0.0
        self.hit_flash = 0.0
        self.t = 0.0

    def set_state(self, state):
        self.state, self.state_t = state, 0.0

    def update(self, dt, game):
        self.t += dt
        self.state_t += dt
        self.hit_flash = max(0.0, self.hit_flash - dt * 5)
        if self.state == "enter":
            self.x -= 120 * dt
            if self.x <= self.target_x:
                self.set_state("armored")
                game.on_boss_ready()
        else:
            self.y = HEIGHT * 0.47 + math.sin(self.t * 0.55) * HEIGHT * 0.26
            self.x = self.target_x + math.sin(self.t * 0.9) * 26
        if self.state == "armored" and self.state_t >= BOSS_ARMORED_TIME:
            self.set_state("exposed")
            game.on_boss_exposed()
        elif self.state == "exposed" and self.state_t >= BOSS_EXPOSED_TIME:
            self.set_state("armored")
        elif self.state == "stagger" and self.state_t >= BOSS_STAGGER:
            self.set_state("armored")

        want = {"exposed": 1.0, "stagger": 0.55}.get(self.state, 0.0)
        self.open += (want - self.open) * min(1.0, dt * 4)

        if self.state in ("armored", "exposed"):
            self.attack_t -= dt
            if self.attack_t <= 0:
                # slower while exposed: the opening is the player's turn
                self.attack_t = self.period * (1.35 if self.state == "exposed" else 1.0)
                pattern = self.patterns[self.pattern_i % len(self.patterns)]
                self.pattern_i += 1
                getattr(self, "_" + pattern)(game)
        if self.spiral_t > 0:
            self.spiral_t -= dt
            self.spiral_emit -= dt
            while self.spiral_emit <= 0 and self.spiral_t > 0:
                self.spiral_emit += 0.055
                self.spiral_a += 0.42
                for k in (0, math.pi):
                    game.enemy_fire(self.x, self.y, self.spiral_a + k, BOSS_SHOT_SPEED)

    def damage(self, amount):
        """Returns "heart" when a heart breaks, "dead" when it was the last,
        else None."""
        if self.state in ("enter", "stagger", "dying"):
            return None
        if self.state == "armored":
            amount *= BOSS_ARMOR
        self.heart_hp -= amount
        self.hit_flash = 1.0
        if self.heart_hp > 0:
            return None
        if self.heart >= self.hearts:
            self.set_state("dying")
            return "dead"
        self.heart += 1
        self.heart_hp = self.heart_hp_max
        self.set_state("stagger")
        return "heart"

    def hit_test(self, x, y, r):
        reach = self.radius * 0.85 + r
        return (x - self.x) ** 2 + (y - self.y) ** 2 < reach * reach

    # --- patterns -----------------------------------------------------------

    def _aimed(self, game):
        base = math.atan2(game.ship.y - self.y, game.ship.x - self.x)
        n = 5 + self.level_index // 2 * 2
        for i in range(n):
            game.enemy_fire(self.x, self.y, base + (i - (n - 1) / 2) * 0.15,
                            BOSS_SHOT_SPEED * 1.15)

    def _radial(self, game):
        n = 14 + 2 * self.level_index
        self.spin += 0.21
        for i in range(n):
            game.enemy_fire(self.x, self.y, self.spin + i * math.tau / n,
                            BOSS_SHOT_SPEED)

    def _spiral(self, game):
        self.spiral_t = 1.5
        self.spiral_emit = 0.0

    def _swarm(self, game):
        for i in range(5):
            game.spawn_enemy("swarm", self.x - self.radius, self.y + (i - 2) * 26,
                             {"amp": 40, "freq": 2.4, "phase": i * 0.9})

    def _mines(self, game):
        for vy in (-60, 60):
            game.spawn_enemy("mine", self.x - self.radius, self.y,
                             {"vy": vy, "drift": 0.9, "phase": vy})

    # --- drawing ------------------------------------------------------------

    def draw(self, surf):
        x, y, r = self.x, self.y, self.radius
        look = BOSS_LOOKS[self.key]
        white = self.hit_flash > 0 and self.state == "exposed"
        petal_col = (255, 255, 255) if white else look["petal"]
        dark = look["petal_dark"]
        n = look["petals"]
        swirl, tip = look["swirl"], look["tip"]
        rot = self.t * 0.16
        spread = self.open * 0.28 * r

        # two interleaved rings of petals: long outer, shorter inner
        for layer in (0, 1):
            outer = (r * 1.12 if layer == 0 else r * 0.76) + spread * (1.0 if layer == 0 else 0.55)
            inner = r * (0.15 if layer == 0 else 0.11)
            width = r * (0.17 if layer == 0 else 0.13)
            off = 0.0 if layer == 0 else math.pi / n          # fill the gaps
            turn = rot if layer == 0 else -rot * 0.6          # the rings counter-rotate
            edge = petal_col if layer == 0 else lerp_color(petal_col, dark, 0.35)
            for k in range(n):
                a = k * math.tau / n + off + turn
                neon_polygon(surf, edge,
                             petal_points(x, y, a, inner, outer, width, swirl, tip), 2, dark)
                v0 = (x + math.cos(a) * inner, y + math.sin(a) * inner)
                v1 = (x + math.cos(a + swirl * 0.9) * outer * 0.9,
                      y + math.sin(a + swirl * 0.9) * outer * 0.9)
                pygame.draw.line(surf, look["vein"], v0, v1, 1)
                if look["speck"] and layer == 0:
                    for t, s in ((0.42, 1), (0.64, -1), (0.8, 1)):   # fixed spots: no flicker
                        d = inner + (outer - inner) * t
                        aa = a + swirl * t
                        sx = x + math.cos(aa) * d - math.sin(aa) * width * 0.45 * s
                        sy = y + math.sin(aa) * d + math.cos(aa) * width * 0.45 * s
                        pygame.draw.circle(surf, look["speck"], (int(sx), int(sy)), 2)

        # the collar that holds the heart
        collar = [(math.cos(i * math.tau / 8) * r * 0.34,
                   math.sin(i * math.tau / 8) * r * 0.34) for i in range(8)]
        pygame.draw.polygon(surf, lerp_color(look["petal"], dark, 0.5),
                            rotate_points(collar, -rot * 2, x, y), 2)

        # the heart: the orange target when exposed, cold (or a dark eye) when closed
        core_r = int(r * 0.17 + self.open * 6)
        if look["eye"] and self.state != "exposed":
            blit_glow(surf, x, y, int(r * 0.45), look["petal"], 0.18)
            pygame.draw.circle(surf, look["eye"], (int(x), int(y)), core_r)
            pygame.draw.circle(surf, lerp_color(look["petal"], dark, 0.3),
                               (int(x), int(y)), core_r, 2)
        else:
            if self.state == "exposed":
                pulse = 0.6 + 0.4 * math.sin(self.t * 9)
                heart_col = C_HEART
            else:
                pulse, heart_col = 0.4, C_HEART_COLD
            blit_glow(surf, x, y, int(r * (0.5 + self.open * 0.5)), heart_col, 0.4 + 0.4 * pulse)
            pygame.draw.circle(surf, heart_col, (int(x), int(y)), core_r)
            if self.state == "exposed":
                pygame.draw.circle(surf, (255, 255, 255), (int(x), int(y)), max(2, core_r // 2))

        # the hearts still beating, as small dots on an arc above
        for i in range(self.hearts):
            hx = x + (i - (self.hearts - 1) / 2) * 14
            col = C_HEART if i >= self.heart - 1 else (60, 40, 40)
            pygame.draw.circle(surf, col, (int(hx), int(y - r * 1.28)), 4)
