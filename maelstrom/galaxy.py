"""The galactic map: the Milky Way carved into territories (sectors).

Geometry and background rendering only -- the screen that uses it
(`menu.galaxy_map`) owns the sector states, labels and input; the territory
shapes come from a layout (`galaxy_layout`, authored or default). The look is
the Mass Effect galaxy map (`docs/mass_effect_sector.jpg`): a faint POLAR GRID
(concentric rings and radial spokes), territories whose borders follow that
grid in bold staircases fanning out from a bright core, and a blocky, notched
outer rim -- all over the galaxy photo. Adapted to the game's canvas (960x540),
fonts and neon.

Three backgrounds are offered so the look can be compared and then chosen (see
the TODO "Campagne etendue"):
  - "reduced"  the Gaia photo, shipped small (`assets/galaxy.jpg`);
  - "proc"     a neon spiral drawn in code, no asset (lightest for the web);
  - "platform" the full-resolution Gaia photo on desktop, "proc" on the web.
Each image mode falls back to "proc" when its file is missing.
"""

import math
import os
import random

import pygame

from settings.ui import (
    ASSET_DIR, C_NEON_CYAN, C_NEON_PURPLE, C_NEON_YELLOW, HEIGHT,
    PROJECT_DIR, WEB, WIDTH,
)
from maelstrom.neon import blit_glow


BG_MODES = ("reduced", "proc", "platform")   # cycled on the map screen (TAB)

REDUCED_IMAGE = os.path.join(ASSET_DIR, "galaxy.jpg")
FULL_IMAGE = os.path.join(PROJECT_DIR, "docs", "voie_lactee_gaia.jpg")

BORDER = (236, 240, 255)         # the territory outlines, bone-white like ME
GRID = (118, 108, 170)           # the faint polar grid under them

RINGS = 6                        # concentric bands between core and rim
COLS = 48                        # angular grid cells (7.5 deg each)
EMPTY = -1                       # a grid cell owned by no sector


class GalaxyMap:
    """The disk, its bright core and its territories, built from a layout (a
    list of sectors each owning a set of grid cells). Placed left of a side
    info panel."""

    def __init__(self, layout, center=None, radius=None):
        self.sectors = layout
        self.n = len(layout)
        self.da = math.tau / COLS
        self.offset = -math.pi / 2                 # column 0 starts pointing up
        # left of the side panel, clear of the title above and the hint below
        self.center = center or (int(WIDTH * 0.34), HEIGHT // 2 + 20)
        self.radius = radius or (HEIGHT // 2 - 72)
        self.core = self.radius * 0.16
        self.rings = [self.core + (self.radius - self.core) * k / RINGS
                      for k in range(RINGS + 1)]
        self._cache = {}                           # mode -> the disk surface
        self._frame = None                         # grid + white borders, built once
        self._build_from_layout()

    # --- geometry -----------------------------------------------------------

    def point(self, angle, r):
        cx, cy = self.center
        return cx + math.cos(angle) * r, cy + math.sin(angle) * r

    def _build_from_layout(self):
        """Own grid from the layout: which sector holds each cell, how far each
        column reaches, and each territory's label/node point (its centroid)."""
        self.cell = [[EMPTY] * COLS for _ in range(RINGS)]
        self.outer = [0] * COLS
        for idx, sector in enumerate(self.sectors):
            for k, m in sector["cells"]:
                if 0 <= k < RINGS and 0 <= m < COLS:
                    self.cell[k][m] = idx
                    self.outer[m] = max(self.outer[m], k + 1)
        self._nodes, self._labels = [], []
        for idx in range(self.n):
            cx = cy = 0.0
            cells = self.sectors[idx]["cells"]
            for k, m in cells:
                a = self.offset + (m + 0.5) * self.da
                r = (self.rings[k] + self.rings[k + 1]) / 2
                cx += math.cos(a) * r
                cy += math.sin(a) * r
            if cells:
                a = math.atan2(cy, cx)
                r = min(math.hypot(cx, cy) / len(cells), self.radius * 0.72)
            else:
                a, r = self.offset, self.radius * 0.5
            self._nodes.append(self.point(a, r))
            self._labels.append(self.point(a, min(r * 1.3, self.radius * 0.86)))

    def _owner(self, k, m):
        if 0 <= k < RINGS:
            owner = self.cell[k][m % COLS]
            return owner if owner != EMPTY else None
        return None

    def _arc(self, a0, a1, r, steps=4):
        return [self.point(a0 + (a1 - a0) * s / steps, r) for s in range(steps + 1)]

    def _edges(self):
        """Yield (polyline, {territory either side}) for every bold border: a
        cell edge between two territories, or the outer rim (None on one side)."""
        for m in range(COLS):
            a0 = self.offset + m * self.da
            a1 = a0 + self.da
            for k in range(RINGS):
                reg = self._owner(k, m)
                if reg is None:
                    continue
                if self._owner(k, m + 1) != reg:           # radial edge (spoke)
                    yield [self.point(a1, self.rings[k]),
                           self.point(a1, self.rings[k + 1])], {reg, self._owner(k, m + 1)}
                if self._owner(k + 1, m) != reg:           # arc edge (ring)
                    yield self._arc(a0, a1, self.rings[k + 1]), {reg, self._owner(k + 1, m)}

    def node(self, i):
        return self._nodes[i]

    def label_pos(self, i):
        return self._labels[i]

    def sector_at(self, pos):
        """The territory index under `pos`, or None if in the core or outside."""
        cell = self.cell_at(pos)
        return self._owner(*cell) if cell else None

    def cell_at(self, pos):
        """The grid cell (ring, col) under `pos`, or None if in the core or past
        the rim. Pure geometry -- used by the editor, whatever owns the cell."""
        cx, cy = self.center
        dx, dy = pos[0] - cx, pos[1] - cy
        r = math.hypot(dx, dy)
        if r < self.core or r >= self.rings[RINGS]:
            return None
        m = int((math.atan2(dy, dx) - self.offset) % math.tau / self.da)
        for k in range(RINGS):
            if self.rings[k] <= r < self.rings[k + 1]:
                return k, m
        return None

    def cell_polygon(self, k, m):
        """The fillable quad of cell (ring, col): inner arc then outer arc."""
        a0 = self.offset + m * self.da
        a1 = a0 + self.da
        return self._arc(a0, a1, self.rings[k]) + self._arc(a1, a0, self.rings[k + 1])

    # --- drawing ------------------------------------------------------------

    def draw_background(self, surf, mode):
        """The galaxy photo (or spiral) masked to the notched rim, plus the
        glowing core."""
        disk = self._disk(mode)
        surf.blit(disk, disk.get_rect(center=self.center))
        pulse = 0.4 + 0.1 * math.sin(pygame.time.get_ticks() / 500.0)
        blit_glow(surf, *self.center, int(self.core * 2.4), C_NEON_YELLOW, pulse)

    def draw_frame(self, surf, hovered=None, accent=C_NEON_CYAN):
        """The faint grid and the white territory borders (cached), then the
        hovered territory's own border repainted in `accent`."""
        if self._frame is None:
            self._frame = self._build_frame()
        surf.blit(self._frame, (0, 0))
        if hovered is not None:
            for poly, regs in self._edges():
                if hovered in regs:
                    pygame.draw.lines(surf, accent, False,
                                      [(int(x), int(y)) for x, y in poly], 2)

    def _build_frame(self):
        frame = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for m in range(COLS):                      # the faint polar grid
            a0 = self.offset + m * self.da
            for k in range(self.outer[m] + 1):
                pygame.draw.lines(frame, GRID, False,
                                  [(int(x), int(y)) for x, y in
                                   self._arc(a0, a0 + self.da, self.rings[k])], 1)
            for k in range(self.outer[m]):
                pygame.draw.line(frame, GRID, self.point(a0, self.rings[k]),
                                 self.point(a0, self.rings[k + 1]), 1)
        pygame.draw.circle(frame, GRID, self.center, int(self.core), 1)
        for poly, _ in self._edges():              # the bold white borders
            pygame.draw.lines(frame, BORDER, False,
                              [(int(x), int(y)) for x, y in poly], 2)
        return frame

    # --- background disk ----------------------------------------------------

    def _rim_polygon(self):
        pts = []
        for m in range(COLS):
            a0 = self.offset + m * self.da
            r = self.rings[self.outer[m]]
            pts.append(self.point(a0, r))
            pts.append(self.point(a0 + self.da, r))
        return pts

    def _disk(self, mode):
        if mode not in self._cache:
            self._cache[mode] = self._build_disk(mode)
        return self._cache[mode]

    def _build_disk(self, mode):
        d = self.radius * 2
        if mode == "proc" or (mode == "platform" and WEB):
            base = self._procedural(d)
        else:
            path = FULL_IMAGE if mode == "platform" else REDUCED_IMAGE
            base = self._load_image(path, d)
            if base is None:
                base = self._procedural(d)
        return self._rim_mask(base, d)

    def _load_image(self, path, d):
        if not os.path.isfile(path):
            return None
        try:
            img = pygame.image.load(path)
        except pygame.error:
            return None
        return pygame.transform.smoothscale(img, (d, d)).convert_alpha()

    def _rim_mask(self, src, d):
        """Keep only what lies inside the notched rim (rim points are relative
        to the disk centre, so shift them into the disk surface)."""
        cx, cy = self.center
        local = [(x - cx + d // 2, y - cy + d // 2) for x, y in self._rim_polygon()]
        mask = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.polygon(mask, (255, 255, 255, 255), local)
        out = src.copy()
        out.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return out

    def _procedural(self, d):
        """A spiral of stars drawn once: a warm core fading to cyan/purple arms.
        Seeded, so the galaxy looks the same every time."""
        surf = pygame.Surface((d, d), pygame.SRCALPHA)
        c = d // 2
        rng = random.Random(0xA17)
        blit_glow(surf, c, c, int(d * 0.22), C_NEON_YELLOW, 0.5)
        for _ in range(2600):
            rr = rng.uniform(0.04, 1.0) ** 0.7
            a = rng.uniform(0, math.tau) + rr * 5.0 + rng.gauss(0, 0.18)
            r = rr * (c - 2)
            x, y = c + r * math.cos(a), c + r * math.sin(a)
            if rr < 0.22:
                col = C_NEON_YELLOW
            elif rr < 0.6:
                col = C_NEON_CYAN
            else:
                col = C_NEON_PURPLE
            size = rng.choice((1, 1, 1, 2, 2, 3))
            if size == 1:
                surf.set_at((int(x), int(y)), col)
            else:
                pygame.draw.circle(surf, col, (int(x), int(y)), size)
        return surf
