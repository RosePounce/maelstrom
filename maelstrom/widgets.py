"""The neon button, shared by the game and the menu."""

import pygame

from settings.ui import (
    C_ALLOY, C_BTN, C_BTN_HOVER, C_BTN_OFF, C_NEON_PINK, C_TEXT, C_TEXT_GRAY,
)
from maelstrom import screen


class Button:
    """`draw(surf, mouse_pos)` and `click(pos)`, the same contract as in the
    other games of the repository."""

    def __init__(self, x, y, w, h, text, color=C_NEON_PINK):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.right = ""          # right-aligned text (cost, level...)
        self.color = color
        self.enabled = True
        self.center = True       # label centred, else left

    def draw(self, surf, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos) and self.enabled
        bg = C_BTN_OFF if not self.enabled else (C_BTN_HOVER if hovered else C_BTN)
        pygame.draw.rect(surf, bg, self.rect, border_radius=5)
        border = self.color if self.enabled else (70, 50, 90)
        pygame.draw.rect(surf, border, self.rect, 2 if hovered else 1, border_radius=5)
        col = C_TEXT if self.enabled else C_TEXT_GRAY
        label = screen.FONT_SMALL.render(self.text, True, col)
        if self.center:
            surf.blit(label, label.get_rect(center=self.rect.center))
        else:
            surf.blit(label, (self.rect.x + 10,
                              self.rect.centery - label.get_height() // 2))
        if self.right:
            rcol = C_ALLOY if self.enabled else C_TEXT_GRAY
            r = screen.FONT_SMALL.render(self.right, True, rcol)
            surf.blit(r, (self.rect.right - 10 - r.get_width(),
                          self.rect.centery - r.get_height() // 2))

    def click(self, pos):
        return self.enabled and self.rect.collidepoint(pos)


def wrap(text, font, width):
    """Splits `text` into lines that fit within `width` pixels."""
    lines, current = [], ""
    for word in text.split():
        attempt = f"{current} {word}".strip()
        if current and font.size(attempt)[0] > width:
            lines.append(current)
            current = word
        else:
            current = attempt
    if current:
        lines.append(current)
    return lines


def stack_buttons(labels, cx, top, w, h, step, color=C_NEON_PINK):
    """A column of centred buttons, one per label, from `top` down."""
    return [Button(cx - w // 2, top + i * step, w, h, text, color)
            for i, text in enumerate(labels)]
