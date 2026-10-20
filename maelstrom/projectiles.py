"""What flies and hurts: shots (both sides), AX missiles, caustic clouds."""

import math

import pygame

from settings.balance import (
    CAUSTIC_CLOUD, MISSILE_DAMAGE, MISSILE_LIFE, MISSILE_SPEED, MISSILE_TURN,
)
from settings.ui import (
    C_CAUSTIC, C_FRAG, C_MISSILE, C_PULSE, C_RAIL, C_THARG_SHOT, HEIGHT, WIDTH,
)
from maelstrom.neon import blit_glow


class Shot:
    """A straight shot. `friendly` ones are the player's; a `pierce` shot
    (rail) goes through what it hits, hitting each target only once."""

    COLORS = {"pulse": C_PULSE, "frag": C_FRAG, "rail": C_RAIL,
              "enemy": C_THARG_SHOT}

    def __init__(self, x, y, vx, vy, damage, kind, radius=3, life=3.0,
                 pierce=False):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.damage = damage
        self.kind = kind
        self.friendly = kind != "enemy"
        self.radius = radius
        self.life = life
        self.pierce = pierce
        self.hits = set()            # ids already hit by a piercing shot
        self.dead = False
        self.color = self.COLORS[kind]

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        if (self.life <= 0 or self.x < -40 or self.x > WIDTH + 40
                or self.y < -40 or self.y > HEIGHT + 40):
            self.dead = True
        return not self.dead

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        if self.kind == "pulse":
            pygame.draw.line(surf, (220, 255, 255), (x - 9, y), (x + 3, y), 3)
            blit_glow(surf, x - 3, y, 9, self.color, 0.6)
        elif self.kind == "frag":
            pygame.draw.circle(surf, (255, 220, 160), (x, y), 2)
            blit_glow(surf, x, y, 6, self.color, 0.6)
        elif self.kind == "rail":
            speed = math.hypot(self.vx, self.vy) or 1
            tail = (x - self.vx / speed * 34, y - self.vy / speed * 34)
            pygame.draw.line(surf, self.color, tail, (x, y), 3)
            pygame.draw.line(surf, (255, 255, 255), tail, (x, y), 1)
            blit_glow(surf, x, y, 12, self.color, 0.7)
        else:
            blit_glow(surf, x, y, 11, self.color, 0.7)
            pygame.draw.circle(surf, (20, 60, 30), (x, y), self.radius)
            pygame.draw.circle(surf, self.color, (x, y), self.radius, 2)


class Missile:
    """AX missile: homes in on the nearest target, turning at MISSILE_TURN."""

    def __init__(self, x, y, angle, damage_mult):
        self.x, self.y = x, y
        self.angle = angle
        self.damage = MISSILE_DAMAGE * damage_mult
        self.radius = 6
        self.life = MISSILE_LIFE
        self.dead = False
        self.trail_t = 0.0

    def update(self, dt, target):
        """`target` is an (x, y) point or None (then it flies straight)."""
        if target is not None:
            want = math.atan2(target[1] - self.y, target[0] - self.x)
            diff = (want - self.angle + math.pi) % math.tau - math.pi
            turn = MISSILE_TURN * dt
            self.angle += max(-turn, min(turn, diff))
        self.x += math.cos(self.angle) * MISSILE_SPEED * dt
        self.y += math.sin(self.angle) * MISSILE_SPEED * dt
        self.life -= dt
        if self.life <= 0 or not (-60 < self.x < WIDTH + 60 and -60 < self.y < HEIGHT + 60):
            self.dead = True
        return not self.dead

    def draw(self, surf):
        ca, sa = math.cos(self.angle), math.sin(self.angle)
        head = (self.x + ca * 7, self.y + sa * 7)
        tail = (self.x - ca * 7, self.y - sa * 7)
        pygame.draw.line(surf, (255, 240, 200), tail, head, 3)
        blit_glow(surf, tail[0], tail[1], 10, C_MISSILE, 0.7)


class CausticCloud:
    """Green cloud left by a caustic mine: it stains the hull inside it."""

    def __init__(self, x, y, drift):
        self.x, self.y = x, y
        self.radius = CAUSTIC_CLOUD["radius"]
        self.life = self.max_life = CAUSTIC_CLOUD["time"]
        self.drift = drift
        self.t = 0.0

    def update(self, dt):
        self.x -= self.drift * dt
        self.life -= dt
        self.t += dt
        return self.life > 0

    def draw(self, surf):
        fade = min(1.0, self.life / 0.8, (self.max_life - self.life) / 0.3 + 0.2)
        for i in range(4):
            a = self.t * 0.8 + i * math.tau / 4
            ox = math.cos(a) * self.radius * 0.35
            oy = math.sin(a) * self.radius * 0.25
            blit_glow(surf, self.x + ox, self.y + oy, int(self.radius * 0.8),
                      C_CAUSTIC, 0.35 * fade)
