"""Synthwave drawing: glows, neon polygons, bars, striped sun, scanlines.

`glow()` caches its halos: they are expensive to build.
"""

import math

import pygame


_GLOW_CACHE = {}


def glow(radius, color, strength=0.55):
    """Small neon halo surface, cached, to be blitted additively.

    The key is deliberately quantized (integer radius, color in steps of 16,
    strength to the tenth): otherwise interpolated colors (impact flash,
    particle fade) would fill the cache forever.
    """
    radius = max(1, int(radius))
    color = (color[0] // 16 * 16, color[1] // 16 * 16, color[2] // 16 * 16)
    strength = round(max(0.05, min(1.0, strength)), 1)
    key = (radius, color, strength)
    surf = _GLOW_CACHE.get(key)
    if surf is None:
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for i in range(radius, 0, -1):
            f = (1.0 - i / radius) ** 2 * strength
            col = (int(color[0] * f), int(color[1] * f), int(color[2] * f))
            pygame.draw.circle(surf, col, (radius, radius), i)
        surf = surf.convert()
        _GLOW_CACHE[key] = surf
    return surf


def blit_glow(surf, x, y, radius, color, strength=0.55):
    """Draws an additive halo centered on (x, y)."""
    g = glow(radius, color, strength)
    surf.blit(g, (int(x) - radius, int(y) - radius), special_flags=pygame.BLEND_RGB_ADD)


def lerp_color(a, b, t):
    """Linear interpolation between two colors."""
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def rotate_points(points, angle, cx, cy):
    """Rotates a list of points around (cx, cy), then moves them there."""
    ca, sa = math.cos(angle), math.sin(angle)
    return [(cx + px * ca - py * sa, cy + px * sa + py * ca) for px, py in points]


def neon_polygon(surf, color, points, width=2, fill=(18, 10, 30)):
    """Dark polygon outlined with a neon stroke."""
    pygame.draw.polygon(surf, fill, points)
    pygame.draw.polygon(surf, color, points, width)


def draw_bar(surf, x, y, w, h, ratio, color, bg):
    """Simple horizontal gauge bar."""
    pygame.draw.rect(surf, bg, (x, y, w, h), border_radius=3)
    fill = int(w * max(0.0, min(1.0, ratio)))
    if fill > 0:
        pygame.draw.rect(surf, color, (x, y, fill, h), border_radius=3)
    pygame.draw.rect(surf, (70, 44, 96), (x, y, w, h), 1, border_radius=3)


def draw_sun(surf, cx, cy, r, top, bottom):
    """The synthwave sun: a top -> bottom gradient disc, striped horizontally,
    the stripes thicker towards the bottom."""
    sun = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    for y in range(r * 2):
        dy = y - r
        half = r * r - dy * dy
        if half <= 0:
            continue
        half = math.sqrt(half)
        pygame.draw.line(sun, lerp_color(top, bottom, y / float(r * 2)),
                         (r - half, y), (r + half, y))
    y = int(r * 1.05)
    gap, thick = 12, 2
    while y < r * 2:
        pygame.draw.rect(sun, (0, 0, 0, 0), (0, y, r * 2, thick))
        y += gap + thick
        thick += 1
        gap = max(5, gap - 1)
    blit_glow(surf, cx, cy, int(r * 1.4), top, 0.45)
    surf.blit(sun, (cx - r, cy - r))


def build_scanlines(width, height):
    """Veil of scanlines, old-monitor style, over a width x height canvas."""
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    for y in range(0, height, 3):
        pygame.draw.line(surf, (0, 0, 0, 26), (0, y), (width, y))
    return surf.convert_alpha()
