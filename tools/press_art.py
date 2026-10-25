"""Store art drawn by the game itself: banner, cover and page background.

    python tools/press_art.py [out_dir] [--lang fr|en]

Default output: `docs/press/`.

Nothing here is an upscaled screenshot. Each piece renders the synthwave
backdrop of `maelstrom.backdrop` AT ITS OWN SIZE -- sky gradient, striped
sun, parallax stars, perspective grid -- then lays the player's wedge, an
Interceptor and the title over it, in the game's own font and colors.

The ship and the Interceptor are drawn on black and blitted ADDITIVELY:
black adds nothing, so only their neon lands on the backdrop, and a sprite
drawn small then scaled up keeps strokes thick enough for a 1920 banner.

`maelstrom.backdrop` and `maelstrom.screen` read the canvas size from
`settings.ui` at import time, so a piece must patch that size BEFORE the
first import: one piece per process, and the script without a piece name
re-runs itself once per piece.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

PIECES = {
    "banner":     {"file": "banniere-1920x480.png",  "size": (1920, 480)},
    "cover":      {"file": "couverture-630x500.png", "size": (630, 500)},
    "background": {"file": "fond-1920x1080.png",     "size": (1920, 1080)},
}


# ----------------------------------------------------------------------
#  Pieces of the composition
# ----------------------------------------------------------------------

def veil(surf, alpha, color=(10, 4, 22)):
    """The menus' veil: the backdrop steps back, the title reads."""
    layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    layer.fill((*color, alpha))
    surf.blit(layer, (0, 0))


def vignette(surf, part=0.34, alpha=190):
    """Darkens the four edges, so a page background never fights with the
    text laid over it and a banner keeps its eye in the middle.

    Built small (one pixel per cell of a coarse grid, alpha = the strongest
    of the four falloffs) then scaled up: drawn edge by edge at full size,
    the horizontal strokes would overwrite the vertical ones -- `draw.line`
    replaces the pixel, alpha and all -- and leave a seam across the image.
    """
    w, h = surf.get_size()
    cells = 96
    small = pygame.Surface((cells, cells), pygame.SRCALPHA)
    for ix in range(cells):
        fx = max(0.0, 1 - (ix + 0.5) / (cells * part))
        fx = max(fx, 1 - (cells - ix - 0.5) / (cells * part))
        for iy in range(cells):
            fy = max(0.0, 1 - (iy + 0.5) / (cells * part))
            fy = max(fy, 1 - (cells - iy - 0.5) / (cells * part))
            small.set_at((ix, iy), (0, 0, 0, int(alpha * max(fx, fy) ** 2)))
    surf.blit(pygame.transform.smoothscale(small, (w, h)), (0, 0))


def neon_sprite(size, draw, scale):
    """Draws on black and scales up, for an ADDITIVE blit."""
    surf = pygame.Surface(size)
    draw(surf)
    w, h = size
    return pygame.transform.smoothscale(surf, (round(w * scale), round(h * scale)))


def blit_add(dst, sprite, center):
    dst.blit(sprite, sprite.get_rect(center=center), special_flags=pygame.BLEND_RGB_ADD)


def ship_sprite(scale, key="krait"):
    """The player's wedge, engine lit, nose to the right."""
    from maelstrom.player import Ship
    from maelstrom.storage import base_loadout

    box = (160, 120)
    ship = Ship(box[0] * 0.5, box[1] * 0.5, {}, base_loadout(key), key)
    ship.invuln = 0.0
    ship.t = 0.4
    ship.tilt = -0.3
    return neon_sprite(box, ship.draw, scale)


def boss_sprite(key, scale, level_index=3):
    """An Interceptor, petals open on its heart."""
    from maelstrom.enemies import make_boss

    boss = make_boss(key, level_index)
    side = int(boss.radius * 5.4)
    boss.x = boss.y = side * 0.5
    boss.state, boss.open, boss.t = "exposed", 1.0, 2.4
    return neon_sprite((side, side), boss.draw, scale)


def spaced_text(font, text, spacing, color):
    """The title, letter by letter: a monospaced font set tight reads like a
    terminal, set loose like a logo."""
    glyphs = [font.render(ch, True, color) for ch in text]
    width = sum(g.get_width() for g in glyphs) + spacing * (len(glyphs) - 1)
    surf = pygame.Surface((width, font.get_height()), pygame.SRCALPHA)
    x = 0
    for g in glyphs:
        surf.blit(g, (x, 0))
        x += g.get_width() + spacing
    return surf


def title(surf, center, text, size, color, glow=0.55):
    """Neon title: a halo of the same color, then the letters over it."""
    from maelstrom import screen
    from maelstrom.neon import blit_glow

    font = screen.load_font(size, bold=True)
    art = spaced_text(font, text, max(2, size // 10), color)
    rect = art.get_rect(center=center)
    radius = int(size * 1.3)
    for x in range(rect.left + radius // 2, rect.right, radius):
        blit_glow(surf, x, center[1], radius, color, glow)
    surf.blit(art, rect)


def subtitle(surf, center, text, size, color):
    from maelstrom import screen

    font = screen.load_font(size)
    art = spaced_text(font, text, max(1, size // 8), color)
    surf.blit(art, art.get_rect(center=center))


# ----------------------------------------------------------------------
#  The three pieces
# ----------------------------------------------------------------------

def make_backdrop(key, seconds=6.0, scroll=140):
    """A backdrop of the game, scrolled a few seconds so the stars sit where
    they would in play and the Maelstrom has turned."""
    from maelstrom.backdrop import Backdrop

    b = Backdrop(key)
    for _ in range(int(seconds * 60)):
        b.update(1 / 60.0, scroll)
    return b


def banner(surf, lang):
    from settings import GAME_NAME
    from maelstrom import i18n
    from settings.ui import C_NEON_CYAN, C_NEON_PINK

    make_backdrop("merope").draw(surf)
    veil(surf, 96)
    vignette(surf, 0.22, 150)
    blit_add(surf, boss_sprite("hydra", 1.55), (1590, 215))
    blit_add(surf, ship_sprite(3.2), (330, 300))
    title(surf, (880, 176), GAME_NAME.upper(), 124, C_NEON_PINK)
    subtitle(surf, (880, 268), i18n.t("menu.home_subtitle"), 24, C_NEON_CYAN)


def cover(surf, lang):
    from settings import GAME_NAME
    from maelstrom import i18n
    from settings.ui import C_NEON_CYAN, C_NEON_PINK

    make_backdrop("merope").draw(surf)
    veil(surf, 104)
    vignette(surf, 0.3, 170)
    blit_add(surf, boss_sprite("hydra", 1.0), (452, 258))
    blit_add(surf, ship_sprite(1.9), (142, 400))
    title(surf, (315, 88), GAME_NAME.upper(), 54, C_NEON_PINK)
    subtitle(surf, (315, 132), i18n.t("menu.home_subtitle"), 13, C_NEON_CYAN)


def background(surf, lang):
    """The page background: the same sky, pushed far back -- it must stay
    under the text, not compete with it."""
    make_backdrop("merope", scroll=180).draw(surf)
    veil(surf, 150)
    vignette(surf, 0.38, 210)


MAKERS = {"banner": banner, "cover": cover, "background": background}


# ----------------------------------------------------------------------

def render(name, out_dir, lang):
    """Renders one piece. Patches the canvas size FIRST: every module below
    binds it at import."""
    piece = PIECES[name]
    width, height = piece["size"]

    import settings.ui as ui
    ui.WIDTH, ui.HEIGHT = width, height

    from maelstrom import i18n, screen
    i18n.set_language(lang)
    screen.init()

    surf = pygame.Surface((width, height)).convert()
    MAKERS[name](surf, lang)
    surf.blit(screen.SCANLINES, (0, 0))

    path = os.path.join(out_dir, piece["file"])
    pygame.image.save(surf, path)
    print("  " + os.path.relpath(path, ROOT))
    pygame.quit()


def main(argv):
    lang = "fr"
    if "--lang" in argv:
        i = argv.index("--lang")
        lang = argv[i + 1]
        del argv[i:i + 2]
    names = [a for a in argv if a in PIECES]
    rest = [a for a in argv if a not in PIECES]
    out_dir = rest[0] if rest else os.path.join(ROOT, "docs", "press")
    os.makedirs(out_dir, exist_ok=True)

    if names:
        for name in names:
            render(name, out_dir, lang)
        return 0
    print(f"store art -> {out_dir}")
    for name in PIECES:                  # one process per size (see the header)
        code = subprocess.call([sys.executable, os.path.abspath(__file__),
                                out_dir, "--lang", lang, name])
        if code:
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
