"""The scrolling synthwave backdrop of a sector.

Three layers, from far to near:
  - a STATIC image built once per sector: gradient sky, the landmark on the
    horizon (striped sun, ring station, nebula), ground gradient;
  - parallax STARS, each layer sliding at its share of the scroll;
  - the perspective GRID of the ground, whose vertical lines slide left
    faster at the bottom than at the horizon.
The Maelstrom is the only landmark drawn live: its arms turn.
"""

import math
import random

import pygame

from settings.ui import (
    GRID_FAR_SCALE, GRID_ROWS, GRID_SPACING, GRID_SPEED, HEIGHT, HORIZON_FRAC,
    LEVEL_LOOKS, STAR_LAYERS, WIDTH,
)
from maelstrom.neon import blit_glow, draw_sun, lerp_color


class Backdrop:
    def __init__(self, key):
        self.look = LEVEL_LOOKS[key]
        self.horizon = int(HEIGHT * HORIZON_FRAC)
        self.static = self._build_static()
        rng = random.Random(len(key) * 31 + 5)
        self.layers = []
        for share, count, size, bright in STAR_LAYERS:
            stars = [(rng.uniform(0, WIDTH), rng.uniform(0, self.horizon - 8))
                     for _ in range(count)]
            self.layers.append((share, size, bright, stars))
        self.offset = 0.0            # distance scrolled, in pixels
        self.t = 0.0
        grid = self.look["grid"]
        self.grid_far = lerp_color(grid, self.look["ground_far"], 0.65)

    # --- static image -------------------------------------------------------

    def _build_static(self):
        look, h0 = self.look, self.horizon
        surf = pygame.Surface((WIDTH, HEIGHT))
        for y in range(h0):
            t = y / float(h0)
            pygame.draw.line(surf, lerp_color(look["sky_top"], look["sky_low"], t * t),
                             (0, y), (WIDTH, y))
        for y in range(h0, HEIGHT):
            t = (y - h0) / float(HEIGHT - h0)
            pygame.draw.line(surf, lerp_color(look["ground_far"], look["ground_near"], t),
                             (0, y), (WIDTH, y))

        landmark = look["landmark"]
        cx = int(WIDTH * 0.66)
        surf.set_clip((0, 0, WIDTH, h0))         # nothing in the sky goes below the horizon
        if landmark in ("sun", "station"):
            draw_sun(surf, cx, h0 - 30, 96, look["sun_top"], look["sun_bot"])
        if landmark == "station":
            self._draw_station(surf, int(WIDTH * 0.3), h0 - 120)
        elif landmark == "nebula":
            self._draw_nebula(surf, cx, h0 - 120)
        elif landmark == "maelstrom":
            blit_glow(surf, cx, h0 - 110, 190, look["sun_bot"], 0.6)
        surf.set_clip(None)

        blit_glow(surf, cx, h0, 120, look["grid"], 0.35)
        bright = lerp_color(look["grid"], (255, 255, 255), 0.45)
        pygame.draw.line(surf, bright, (0, h0), (WIDTH, h0), 2)
        return surf.convert()

    def _draw_station(self, surf, cx, cy):
        """The broken ring of the Oracle, a silhouette against the sky: a
        tilted wheel, one arc torn away, its spokes and its hub."""
        rim = lerp_color(self.look["sky_low"], (255, 170, 130), 0.4)
        rect = pygame.Rect(0, 0, 240, 64)
        rect.center = (cx, cy)
        pygame.draw.arc(surf, rim, rect, 0.0, 4.6, 5)
        pygame.draw.arc(surf, rim, rect.inflate(-18, -10), 0.0, 4.6, 1)
        for a in (0.4, 1.6, 2.8, 4.0):
            px = cx + math.cos(a) * rect.w / 2
            py = cy - math.sin(a) * rect.h / 2
            pygame.draw.line(surf, rim, (cx, cy), (px, py), 1)
        for dx, dy in ((132, 28), (150, 40), (120, 46)):      # the torn pieces
            pygame.draw.rect(surf, rim, (cx + dx, cy + dy, 6, 3))
        hub = pygame.Rect(0, 0, 26, 18)
        hub.center = (cx, cy)
        pygame.draw.rect(surf, (20, 8, 16), hub)
        pygame.draw.rect(surf, rim, hub, 2)

    def _draw_nebula(self, surf, cx, cy):
        """Blue clouds and the seven sisters, bright and close together."""
        rng = random.Random(7)
        for _ in range(9):
            x = cx + rng.randint(-220, 160)
            y = cy + rng.randint(-60, 70)
            blit_glow(surf, x, y, rng.randint(60, 120),
                      (60, 110, 220) if rng.random() < 0.6 else (150, 90, 230), 0.4)
        for dx, dy in ((0, 0), (26, -14), (48, 6), (14, 22), (-24, 12),
                       (36, 30), (-10, -26)):
            blit_glow(surf, cx + dx, cy + dy, 14, (170, 220, 255), 0.9)
            pygame.draw.circle(surf, (235, 245, 255), (cx + dx, cy + dy), 2)

    # --- live layers --------------------------------------------------------

    def update(self, dt, scroll):
        self.offset += scroll * dt
        self.t += dt

    def draw(self, surf):
        surf.blit(self.static, (0, 0))
        if self.look["landmark"] == "maelstrom":
            self._draw_maelstrom(surf)
        span = WIDTH + 4
        for share, size, bright, stars in self.layers:
            shift = self.offset * share
            col = (bright, bright, min(255, bright + 20))
            for sx, sy in stars:
                pygame.draw.rect(surf, col, ((sx - shift) % span - 2, sy, size, size))
        self._draw_grid(surf)

    def _draw_maelstrom(self, surf):
        """Five spiral arms around a dark eye, turning slowly."""
        cx, cy = int(WIDTH * 0.66), self.horizon - 110
        base = self.t * 0.35
        for arm in range(5):
            prev = None
            for i in range(22):
                r = 10 + i * 5.2
                a = base + arm * math.tau / 5 + r * 0.035
                p = (cx + math.cos(a) * r, cy + math.sin(a) * r * 0.55)
                if prev is not None:
                    fade = 1.0 - i / 22
                    col = lerp_color(self.look["sky_low"], self.look["grid"], fade)
                    pygame.draw.line(surf, col, prev, p, 2)
                prev = p
        pygame.draw.circle(surf, (2, 8, 6), (cx, cy), 9)

    def _draw_grid(self, surf):
        h0, grid = self.horizon, self.look["grid"]
        depth = HEIGHT - h0
        for i in range(1, GRID_ROWS + 1):
            z = (i / GRID_ROWS) ** 2.2
            y = int(h0 + depth * z)
            pygame.draw.line(surf, lerp_color(self.grid_far, grid, z), (0, y), (WIDTH, y))
        cx = WIDTH // 2
        shift = (self.offset * GRID_SPEED) % GRID_SPACING
        reach = int(WIDTH * 3 / GRID_SPACING)
        for i in range(-reach, reach + 1):
            xb = cx + i * GRID_SPACING - shift
            xt = cx + (xb - cx) * GRID_FAR_SCALE
            if max(xt, xb) < 0 or min(xt, xb) > WIDTH:
                continue
            pygame.draw.line(surf, self.grid_far, (xt, h0), (xb, HEIGHT))
