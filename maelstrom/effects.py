"""Visual effects with no game rule: particles, floating texts, rings."""

import pygame

from maelstrom.neon import blit_glow
from maelstrom import screen


class Particle:
    """Spark from an explosion, an engine or a hit."""

    def __init__(self, x, y, vx, vy, life, color, size=2):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.94
        self.vy *= 0.94
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        t = self.life / self.max_life
        col = (int(self.color[0] * t), int(self.color[1] * t), int(self.color[2] * t))
        s = max(1, int(self.size * t))
        pygame.draw.rect(surf, col, (int(self.x), int(self.y), s, s))
        blit_glow(surf, self.x, self.y, 7, self.color, 0.5 * t)


class FloatText:
    """Small text that rises and fades out (pickups, gains)."""

    def __init__(self, x, y, text, color, life=1.1):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = self.max_life = life

    def update(self, dt):
        self.y -= 30 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        t = max(0.0, self.life / self.max_life)
        img = screen.FONT_SMALL.render(self.text, True, self.color)
        img.set_alpha(int(255 * t))
        surf.blit(img, img.get_rect(center=(int(self.x), int(self.y))))


class Ring:
    """Expanding ring: a shockwave, a heart that bursts, a shield that pops."""

    def __init__(self, x, y, radius_max, color, life=0.6, width=3):
        self.x, self.y = x, y
        self.radius_max = radius_max
        self.color = color
        self.life = self.max_life = life
        self.width = width

    def update(self, dt):
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        t = 1.0 - self.life / self.max_life
        r = int(self.radius_max * (1 - (1 - t) ** 2))
        if r < 2:
            return
        fade = 1.0 - t
        col = (int(self.color[0] * fade), int(self.color[1] * fade),
               int(self.color[2] * fade))
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), r,
                           max(1, int(self.width * fade) + 1))
