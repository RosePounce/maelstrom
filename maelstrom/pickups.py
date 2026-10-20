"""Containers dropped by destroyed ships: bonuses, maluses, unknown ones.

A container drifts left with the scroll. Only BONUSES are pulled by the
magnet: a malus is avoided, an unknown container is a choice.
A weapon module cycles through the weapons (`CAPSULE_CYCLE`): what it shows
when caught is what the player gets.
"""

import math
import random

import pygame

from settings.balance import (
    BONUSES, CAPSULE_CYCLE, DROP_SPLIT, MAGNET_PULL, MALUSES, PICKUP_DRIFT,
    PICKUP_LIFE, WEAPON_ORDER,
)
from settings.ui import (
    C_ALLOY, C_BONUS, C_FRAG, C_MALUS, C_MYSTERY, C_PULSE, C_RAIL, C_TEXT,
    PLAY_BOTTOM, PLAY_TOP,
)
from maelstrom.neon import blit_glow
from maelstrom import i18n, screen


WEAPON_COLOR = {"pulse": C_PULSE, "frag": C_FRAG, "rail": C_RAIL}


def weighted(table):
    """A key of a {key: {"weight": w}} table, drawn by weight."""
    keys = list(table)
    return random.choices(keys, [table[k]["weight"] for k in keys])[0]


def roll_container():
    """(category, key) of a new container."""
    cats = list(DROP_SPLIT)
    cat = random.choices(cats, [DROP_SPLIT[c] for c in cats])[0]
    if cat == "bonus":
        return cat, weighted(BONUSES)
    if cat == "malus":
        return cat, weighted(MALUSES)
    return cat, "mystery"


class Pickup:
    def __init__(self, x, y, cat, key):
        self.x, self.y = x, y
        self.cat = cat
        self.key = key
        self.vx = random.uniform(-40, 40)
        self.vy = random.uniform(-50, 50)
        self.life = PICKUP_LIFE
        self.t = random.uniform(0, 10)
        self.taken = False

    @property
    def weapon(self):
        """The weapon a module shows right now."""
        i = int(self.t / CAPSULE_CYCLE) % len(WEAPON_ORDER)
        return WEAPON_ORDER[i]

    def update(self, dt, ship, magnet):
        self.t += dt
        self.life -= dt
        self.vx *= 0.96
        self.vy *= 0.96
        self.x += (self.vx - PICKUP_DRIFT) * dt
        self.y += self.vy * dt
        self.y = max(PLAY_TOP, min(PLAY_BOTTOM, self.y))
        if self.cat == "bonus" and ship is not None:
            dx, dy = ship.x - self.x, ship.y - self.y
            dist = math.hypot(dx, dy)
            if 0 < dist < magnet:
                pull = MAGNET_PULL * (1 - dist / magnet) + 60
                self.x += dx / dist * pull * dt
                self.y += dy / dist * pull * dt
        return self.life > 0 and self.x > -30 and not self.taken

    def color(self):
        if self.key == "weapon":
            return WEAPON_COLOR[self.weapon]
        if self.key == "alloy":
            return C_ALLOY
        return {"bonus": C_BONUS, "malus": C_MALUS, "mystery": C_MYSTERY}[self.cat]

    def draw(self, surf):
        if self.life < 3 and int(self.life * 8) % 2 == 0:
            return                       # blinks before it is lost
        x, y = int(self.x), int(self.y + math.sin(self.t * 4) * 2)
        col = self.color()
        blit_glow(surf, x, y, 20, col, 0.5)
        if self.key == "alloy":
            pts = [(x, y - 11), (x + 7, y), (x, y + 11), (x - 7, y)]
            pygame.draw.polygon(surf, (20, 30, 50), pts)
            pygame.draw.polygon(surf, col, pts, 2)
            pygame.draw.line(surf, (255, 255, 255), (x, y - 7), (x + 3, y), 1)
            return
        if self.cat == "malus":
            # a jagged Thargoid fragment
            pts = []
            for i in range(10):
                a = i * math.tau / 10 + self.t * 1.5
                rr = 12 if i % 2 == 0 else 7
                pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
            pygame.draw.polygon(surf, (30, 40, 10), pts)
            pygame.draw.polygon(surf, col, pts, 2)
        else:
            # a hexagonal capsule
            pts = [(x + math.cos(i * math.tau / 6) * 12, y + math.sin(i * math.tau / 6) * 12)
                   for i in range(6)]
            pygame.draw.polygon(surf, (18, 10, 30), pts)
            pygame.draw.polygon(surf, col, pts, 2)
        letter = i18n.weapon_letter(self.weapon) if self.key == "weapon" else i18n.pickup_letter(self.key)
        if letter:
            img = screen.FONT_TINY.render(letter, True, C_TEXT)
            surf.blit(img, img.get_rect(center=(x, y)))
