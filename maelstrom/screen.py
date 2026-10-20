"""Display: window, fonts, icon and scanlines.

This module holds the values CREATED at runtime: the `SCREEN` canvas, the
fonts, the clock, the scanlines. They are always read through the module
(`screen.SCREEN`, `screen.FONT_SMALL`), never through `from maelstrom.screen
import SCREEN`, which would keep the `None` from before `init()`.

The canvas is a fixed 960 x 540 landscape (`settings.ui.WIDTH / HEIGHT`).

`init()` must be called before the first render: under pygbag, pygame is
reinitialized after the import, and a font created at module load would be
invalid.
"""

import pygame

from settings.ui import (
    C_NEON_CYAN, C_NEON_PINK, C_THARG, FONT_PATH, FONT_SIZES, HEIGHT, WEB, WIDTH,
)
from maelstrom import i18n
from maelstrom.neon import build_scanlines
from maelstrom.storage import setup_logging


def make_screen():
    """Returns the game window, creating it when missing or of another size.

    SCALED scales the logical canvas to the window and converts the mouse;
    RESIZABLE lets the player change the window size. `set_mode()` is not
    called again if the window already has the right size: recreating it
    makes the window manager move it at every switch of screen.
    """
    current = pygame.display.get_surface()
    if current is not None and current.get_size() == (WIDTH, HEIGHT):
        return current
    if WEB:
        # No SDL renderer in the pygbag canvas: SCALED would kill the page.
        # The page scales the canvas itself.
        return pygame.display.set_mode((WIDTH, HEIGHT))
    try:
        return pygame.display.set_mode((WIDTH, HEIGHT),
                                       pygame.SCALED | pygame.RESIZABLE)
    except pygame.error:
        return pygame.display.set_mode((WIDTH, HEIGHT))


def _refit_page():
    """In the browser, ask the pygbag page to fit its canvas to the window
    again, with the proportions of the canvas just created (at startup it is
    still 1 x 1, and the game would be drawn squeezed into a square)."""
    if not WEB:
        return
    try:
        import platform
        platform.window.window_resize()
    except Exception:
        pass


def toggle_fullscreen():
    """F11. No effect in the browser, which has its own fullscreen."""
    if WEB:
        return
    pygame.display.toggle_fullscreen()


def make_icon():
    """Window icon (32x32 surface), drawn like the rest of the game: the
    player's wedge facing a Thargoid heart."""
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.circle(surf, C_THARG, (25, 16), 6, 2)
    pygame.draw.circle(surf, (255, 120, 60), (25, 16), 2)
    pts = [(18, 16), (3, 7), (7, 16), (3, 25)]
    pygame.draw.polygon(surf, (18, 10, 30), pts)
    pygame.draw.polygon(surf, C_NEON_CYAN, pts, 2)
    pygame.draw.line(surf, C_NEON_PINK, (1, 16), (5, 16), 2)
    return surf


SCREEN = None
ICON = None
CLOCK = None
FONT_TITLE = None
FONT_BIG = None
FONT = None
FONT_SMALL = None
FONT_TINY = None
FONT_HUGE = None
SCANLINES = None


def load_font(size, bold=False):
    """The game's monospaced font, shipped with it (no system font in the
    browser). Bold is synthetic. Falls back to `SysFont` if the file is
    missing."""
    try:
        f = pygame.font.Font(FONT_PATH, size)
    except (OSError, pygame.error):
        return pygame.font.SysFont("consolas", size, bold=bold)
    if bold:
        f.set_bold(True)
    return f


def init():
    """Creates the window, the icon, the clock, the fonts and the scanlines.
    To be called once, before any rendering (see main.py)."""
    global SCREEN, ICON, CLOCK, SCANLINES
    global FONT_TITLE, FONT_BIG, FONT, FONT_SMALL, FONT_TINY, FONT_HUGE
    setup_logging()
    pygame.init()
    SCREEN = make_screen()
    _refit_page()
    pygame.display.set_caption(i18n.window_caption())
    ICON = make_icon()
    pygame.display.set_icon(ICON)
    CLOCK = pygame.time.Clock()
    FONT_TITLE = load_font(FONT_SIZES["title"], bold=True)
    FONT_BIG = load_font(FONT_SIZES["big"], bold=True)
    FONT = load_font(FONT_SIZES["normal"])
    FONT_SMALL = load_font(FONT_SIZES["small"])
    FONT_TINY = load_font(FONT_SIZES["tiny"])
    FONT_HUGE = load_font(FONT_SIZES["huge"], bold=True)
    SCANLINES = build_scanlines(WIDTH, HEIGHT)
