"""Archive: the ORIGINAL Interceptor art (before the Elite Dangerous rework).

Kept for reference only -- this file is imported by nothing and is excluded
from the pygbag web build (`attic` is in `pygbag.ini`'s ignoreDirs). The live
boss art is `Interceptor.draw` in `maelstrom/enemies.py`, driven per variant by
`settings.ui.BOSS_LOOKS`.

This first version drew every Interceptor the SAME way: four green petals
(`C_THARG`) around the heart, only the radius and the number of hearts telling
Cyclops / Basilisk / Medusa / Hydra apart. The rework replaced it with a
per-variant rosette (petal count, colors, round / barbed / spiked tips).

To restore it: paste the body of `draw` below back into `Interceptor.draw`
(`enemies.py`), and make sure that module still imports
`C_THARG, C_THARG_DARK, C_HEART, C_HEART_COLD` from `settings.ui` and
`blit_glow, lerp_color, neon_polygon, rotate_points` from `maelstrom.neon`.
`BOSS_LOOKS` is then unused by the boss (it stays only for the new art).
"""

import math

import pygame

from settings.ui import C_HEART, C_HEART_COLD, C_THARG, C_THARG_DARK
from maelstrom.neon import blit_glow, lerp_color, neon_polygon, rotate_points


def draw(self, surf):
    """The original four-petal Interceptor, one green rosette for all bosses."""
    x, y, r = self.x, self.y, self.radius
    white = self.hit_flash > 0 and self.state == "exposed"
    outline = (255, 255, 255) if white else C_THARG
    rot = self.t * 0.15
    spread = self.open * 0.45 * r
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2 + rot
        w = r * 0.36
        petal = [(r * 0.22 + spread, 0), (r * 0.45 + spread, -w * 0.8),
                 (r * 0.72 + spread, -w), (r * 0.98 + spread, -w * 0.45),
                 (r * 1.08 + spread, 0), (r * 0.98 + spread, w * 0.45),
                 (r * 0.72 + spread, w), (r * 0.45 + spread, w * 0.8)]
        neon_polygon(surf, outline, rotate_points(petal, a, x, y), 2, C_THARG_DARK)
        vein = rotate_points([(r * 0.35 + spread, 0), (r * 0.95 + spread, 0)], a, x, y)
        pygame.draw.line(surf, lerp_color(C_THARG, C_THARG_DARK, 0.5), vein[0], vein[1], 1)
    # the hexagonal ring that holds the heart
    ring = [(math.cos(i * math.tau / 6) * r * 0.42,
             math.sin(i * math.tau / 6) * r * 0.42) for i in range(6)]
    pygame.draw.polygon(surf, lerp_color(C_THARG, C_THARG_DARK, 0.4),
                        rotate_points(ring, -rot * 2, x, y), 2)

    if self.state == "exposed":
        pulse = 0.6 + 0.4 * math.sin(self.t * 9)
        heart_col = C_HEART
    else:
        pulse = 0.4
        heart_col = C_HEART_COLD
    blit_glow(surf, x, y, int(r * (0.5 + self.open * 0.5)), heart_col, 0.4 + 0.4 * pulse)
    pygame.draw.circle(surf, heart_col, (int(x), int(y)), int(r * 0.18 + self.open * 6))

    # the hearts still beating, as small dots on an arc above
    for i in range(self.hearts):
        hx = x + (i - (self.hearts - 1) / 2) * 14
        col = C_HEART if i >= self.heart - 1 else (60, 40, 40)
        pygame.draw.circle(surf, col, (int(hx), int(y - r * 1.15)), 4)
