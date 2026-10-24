"""
Maelstrom screens outside a sector: home, sectors, hangar, options, and the
co-op lobby (desktop only).

The menu borrows from the game its window and fonts (`maelstrom.screen`), its
colors (`settings.ui`), its neon drawing (`maelstrom.neon`), its scrolling
backdrop (`maelstrom.backdrop`) and its Button class (`maelstrom.widgets`).

Each screen has its own loop and RETURNS a string (or a sector index)
instead of exiting on its own: "campaign", "coop", "hangar", "options",
"menu", "quit".
"""

import asyncio
import copy
import math

import pygame

from settings import GAME_NAME, VERSION_LABEL
from settings.balance import HANGAR, LEVELS, SHIP_ORDER, SHIPS, hangar_cost
from settings.ui import (
    C_ALLOY, C_HEART, C_HULL, C_NEON_CYAN, C_NEON_ORANGE, C_NEON_PINK,
    C_NEON_PURPLE, C_NEON_YELLOW, C_PANEL, C_PANEL_BORDER, C_SHIELD, C_TEXT,
    C_TEXT_GRAY, C_NEON_RED, C_PLAYERS, C_THARG, C_THARG_DARK, FPS, HEIGHT,
    LEVEL_LOOKS, WEB, WIDTH,
)
from maelstrom import audio, bugform, i18n, screen
from maelstrom.galaxy import BG_MODES, BORDER, COLS, EMPTY, GalaxyMap, RINGS
from maelstrom.galaxy_layout import (
    adjacency, load_layout, new_region, region_id, save_layout, sector_id,
    titan_id,
)
from maelstrom.backdrop import Backdrop
from maelstrom.neon import blit_glow, draw_bar, draw_sun, neon_polygon
from maelstrom.player import COCKPIT, HULL_SHAPE, SHIP_SHAPES
from maelstrom.screen import make_screen, toggle_fullscreen
from maelstrom.storage import read_meta, write_meta
from maelstrom.widgets import Button, wrap


BTN_W, BTN_H = 300, 44
MENU_SCROLL = 60                 # the backdrop drifts slowly behind the menus


_bug = None                      # the bug report form shared by every screen


def init():
    """Prepares the game. To be called first (main.py)."""
    global _bug
    i18n.set_language(i18n.detect())
    screen.init()
    audio.init()
    _bug = bugform.BugForm()     # built after the language and fonts are ready


def _bug_intercept(e, name):
    """F8 opens the report form over any menu (desktop; it self-guards on the
    web). While it is open it takes every key and left click, so the screen
    underneath cannot navigate. Returns True when the event was consumed."""
    if _bug.is_open:
        if e.type == pygame.KEYDOWN:
            _bug.key(e)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            _bug.click(e.pos)
        return e.type != pygame.QUIT      # let QUIT through, swallow the rest
    if e.type == pygame.KEYDOWN and e.key == pygame.K_F8:
        _bug.open(screen_name=name, shot=screen.SCREEN.copy())
        return _bug.is_open
    return False


def _bug_overlay(surf, dt):
    """Draw the form and its notice, after the screen has drawn itself."""
    _bug.tick_notice(dt)
    if _bug.is_open:
        _bug.draw(surf, dt)
    _bug.draw_notice(surf)


# ----------------------------------------------------------------------
#  Shared pieces
# ----------------------------------------------------------------------

_backdrops = {}


def backdrop(key):
    """The backdrop of a sector, built once and kept: it scrolls behind the
    menu screens."""
    if key not in _backdrops:
        _backdrops[key] = Backdrop(key)
    return _backdrops[key]


def _veil(surf, alpha=150):
    veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    veil.fill((10, 4, 22, alpha))
    surf.blit(veil, (0, 0))


def _background(surf, key, dt, alpha=150):
    b = backdrop(key)
    b.update(dt, MENU_SCROLL)
    b.draw(surf)
    _veil(surf, alpha)


def _title(surf, title, subtitle=None, y=58):
    cx = WIDTH // 2
    t = screen.FONT_HUGE.render(title, True, C_NEON_PINK)
    blit_glow(surf, cx, y, 200, C_NEON_PINK, 0.2)
    surf.blit(t, t.get_rect(center=(cx, y)))
    if subtitle:
        s = screen.FONT.render(subtitle, True, C_TEXT_GRAY)
        surf.blit(s, s.get_rect(center=(cx, y + 44)))


def _foot(surf):
    t = screen.FONT_TINY.render(VERSION_LABEL, True, C_TEXT_GRAY)
    surf.blit(t, t.get_rect(center=(WIDTH // 2, HEIGHT - 12)))


def _balance(surf, meta):
    t = screen.FONT.render(i18n.t("menu.alloy_balance", alloys=meta["alloys"]), True, C_ALLOY)
    surf.blit(t, (WIDTH - 20 - t.get_width(), 16))


def _finish(surf):
    surf.blit(screen.SCANLINES, (0, 0))
    pygame.display.flip()


def _tick():
    return screen.CLOCK.tick(FPS) / 1000.0


class Card:
    """A big clickable card: a drawing, a title, a few lines. Same contract
    as Button (`draw(surf, mouse_pos)` / `click(pos)`). On hover it lifts by
    LIFT pixels, but its click rectangle does not move."""

    LIFT = 6
    ART_H = 120

    def __init__(self, rect, title, lines, draw_art, accent, enabled=True):
        self.rect = pygame.Rect(rect)
        self.title = title
        self.lines = lines
        self.draw_art = draw_art
        self.accent = accent
        self.enabled = enabled

    def draw(self, surf, mouse_pos):
        hovered = self.enabled and self.rect.collidepoint(mouse_pos)
        frame = self.rect.move(0, -self.LIFT if hovered else 0)
        panel = pygame.Surface(frame.size, pygame.SRCALPHA)
        panel.fill((*C_PANEL, 220))
        surf.blit(panel, frame.topleft)
        border = self.accent if self.enabled else (70, 50, 90)
        pygame.draw.rect(surf, border, frame, 2 if hovered else 1, border_radius=8)
        if hovered:
            blit_glow(surf, frame.centerx, frame.y + self.ART_H // 2, 80, self.accent, 0.25)
        art = pygame.Rect(frame.x + 8, frame.y + 8, frame.w - 16, self.ART_H)
        self.draw_art(surf, art, self.enabled)
        y = art.bottom + 10
        col = C_TEXT if self.enabled else C_TEXT_GRAY
        for font in (screen.FONT_TITLE, screen.FONT, screen.FONT_SMALL):
            if font.size(self.title)[0] <= frame.w - 16:
                break                    # a title too wide takes a smaller font
        t = font.render(self.title, True, self.accent if self.enabled else col)
        surf.blit(t, t.get_rect(midtop=(frame.centerx, y)))
        y += t.get_height() + 6
        for line, line_col in self.lines:
            for part in wrap(line, screen.FONT_SMALL, frame.w - 20):
                img = screen.FONT_SMALL.render(part, True, line_col if self.enabled else C_TEXT_GRAY)
                surf.blit(img, img.get_rect(midtop=(frame.centerx, y)))
                y += 19

    def click(self, pos):
        return self.enabled and self.rect.collidepoint(pos)


def _row_rects(count, w, h, top, gap=18):
    total = count * w + (count - 1) * gap
    x0 = WIDTH // 2 - total // 2
    return [(x0 + i * (w + gap), top, w, h) for i in range(count)]


# ----------------------------------------------------------------------
#  Card drawings
# ----------------------------------------------------------------------

def _draw_ship(surf, x, y, scale, color=C_NEON_CYAN):
    pts = [(x + px * scale, y + py * scale) for px, py in HULL_SHAPE]
    neon_polygon(surf, color, pts)
    pygame.draw.polygon(surf, C_NEON_PINK, [(x + px * scale, y + py * scale) for px, py in COCKPIT])
    blit_glow(surf, x - 16 * scale, y, int(14 * scale), C_NEON_PINK, 0.6)


def _art_campaign(surf, art, enabled):
    t = pygame.time.get_ticks() / 1000.0
    _draw_ship(surf, art.x + art.w * 0.3, art.centery + math.sin(t * 2) * 6, 1.8)
    for i in range(3):
        sx = art.x + art.w * 0.45 + ((t * 160 + i * 40) % (art.w * 0.3))
        pygame.draw.line(surf, C_NEON_CYAN, (sx, art.centery), (sx + 10, art.centery), 2)
    hx, hy = art.x + art.w * 0.8, art.centery
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2 + t * 0.3
        tip = (hx + math.cos(a) * 34, hy + math.sin(a) * 34)
        side1 = (hx + math.cos(a + 0.5) * 18, hy + math.sin(a + 0.5) * 18)
        side2 = (hx + math.cos(a - 0.5) * 18, hy + math.sin(a - 0.5) * 18)
        neon_polygon(surf, C_THARG, [(hx, hy), side1, tip, side2], 2, C_THARG_DARK)
    blit_glow(surf, hx, hy, 24, C_HEART, 0.7)


def _art_coop(surf, art, enabled):
    t = pygame.time.get_ticks() / 1000.0
    for i, color in enumerate(C_PLAYERS):
        y = art.centery + (i * 2 - 1) * 26 + math.sin(t * 2 + i * 1.7) * 5
        _draw_ship(surf, art.x + art.w * (0.32 - i * 0.08), y, 1.4, color)
    hx, hy = art.x + art.w * 0.8, art.centery
    pygame.draw.circle(surf, C_THARG, (int(hx), int(hy)), 22, 2)
    blit_glow(surf, hx, hy, 24, C_HEART, 0.7)


def _art_hangar(surf, art, enabled):
    _draw_ship(surf, art.centerx, art.centery - 6, 2.2)
    for i in range(5):
        x = art.centerx - 50 + i * 22
        h = 6 + i * 4
        pygame.draw.rect(surf, C_ALLOY, (x, art.bottom - 10 - h, 14, h), 1)


def _sector_art(index):
    look = LEVEL_LOOKS[LEVELS[index]["key"]]

    def draw(surf, art, enabled):
        pygame.draw.rect(surf, look["sky_top"], art)
        h0 = art.y + int(art.h * 0.72)
        pygame.draw.rect(surf, look["sky_low"], (art.x, h0 - 24, art.w, 24))
        pygame.draw.rect(surf, look["ground_near"], (art.x, h0, art.w, art.bottom - h0))
        clip = surf.get_clip()
        surf.set_clip(pygame.Rect(art.x, art.y, art.w, h0 - art.y))   # the sky only
        if look["landmark"] == "maelstrom":
            t = pygame.time.get_ticks() / 1000.0
            cx, cy = art.centerx, h0 - 40
            for arm in range(5):
                pts = []
                for i in range(14):
                    r = 4 + i * 3.4
                    a = t * 0.4 + arm * math.tau / 5 + r * 0.05
                    pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r * 0.55))
                pygame.draw.lines(surf, look["grid"], False, pts, 1)
        elif look["landmark"] == "nebula":
            blit_glow(surf, art.centerx, h0 - 44, 50, (70, 110, 220), 0.5)
            for dx, dy in ((0, 0), (12, -7), (22, 3), (6, 11), (-11, 6)):
                pygame.draw.circle(surf, (230, 240, 255), (art.centerx + dx, h0 - 44 + dy), 2)
        else:
            draw_sun(surf, art.centerx, h0 - 10, 34, look["sun_top"], look["sun_bot"])
        surf.set_clip(art)
        for i in range(-6, 7):
            pygame.draw.line(surf, look["grid"], (art.centerx + i * 4, h0),
                             (art.centerx + i * 40, art.bottom), 1)
        pygame.draw.line(surf, look["grid"], (art.x, h0), (art.right, h0), 2)
        surf.set_clip(clip)
        if not enabled:
            _veil_rect(surf, art)

    return draw


def _veil_rect(surf, rect):
    veil = pygame.Surface(rect.size, pygame.SRCALPHA)
    veil.fill((8, 4, 16, 170))
    surf.blit(veil, rect.topleft)


# ----------------------------------------------------------------------
#  Home
# ----------------------------------------------------------------------

async def _confirm_quit(surf, under):
    """Escape on the home screen: confirm before closing."""
    cx = WIDTH // 2
    ok = Button(cx - 160, HEIGHT // 2 + 10, 150, BTN_H, i18n.t("menu.btn_quit"))
    no = Button(cx + 10, HEIGHT // 2 + 10, 150, BTN_H, i18n.t("menu.btn_cancel"), C_NEON_CYAN)
    while True:
        _tick()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return True
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_F11:
                    toggle_fullscreen()
                elif e.key == pygame.K_ESCAPE:
                    return False
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return True
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if ok.click(e.pos):
                    return True
                if no.click(e.pos):
                    return False
        surf.blit(under, (0, 0))
        _veil(surf, 170)
        box = pygame.Rect(cx - 200, HEIGHT // 2 - 70, 400, 150)
        pygame.draw.rect(surf, C_PANEL, box, border_radius=8)
        pygame.draw.rect(surf, C_PANEL_BORDER, box, 2, border_radius=8)
        t = screen.FONT_TITLE.render(i18n.t("menu.confirm_quit"), True, C_TEXT)
        surf.blit(t, t.get_rect(center=(cx, HEIGHT // 2 - 28)))
        mouse = pygame.mouse.get_pos()
        ok.draw(surf, mouse)
        no.draw(surf, mouse)
        _finish(surf)
        await asyncio.sleep(0)


async def home():
    """Returns "campaign", "coop", "hangar", "options" or "quit"."""
    audio.music("title")
    surf = screen.SCREEN = make_screen()
    pygame.display.set_caption(i18n.window_caption())
    pygame.display.set_icon(screen.ICON)
    meta = read_meta()
    cards = [
        ("campaign", i18n.t("menu.card_campaign"),
         [(i18n.t("menu.card_campaign_sub"), C_TEXT)], _art_campaign, C_NEON_CYAN),
        ("hangar", i18n.t("menu.card_hangar"),
         [(i18n.t("menu.card_hangar_sub"), C_TEXT),
          (i18n.t("menu.alloy_balance", alloys=meta["alloys"]), C_ALLOY)],
         _art_hangar, C_ALLOY),
    ]
    if not WEB:                      # no sockets in a browser page
        cards.insert(1, ("coop", i18n.t("menu.card_coop"),
                         [(i18n.t("menu.card_coop_sub"), C_TEXT)], _art_coop, C_PLAYERS[1]))
    w, gap = (300, 30) if len(cards) == 2 else (264, 22)
    rects = _row_rects(len(cards), w, 250, 140, gap)
    cards = [(key, Card(rect, title, lines, art, accent))
             for rect, (key, title, lines, art, accent) in zip(rects, cards)]
    cx = WIDTH // 2
    buttons = [("options", Button(cx - 160 if not WEB else cx - 75, 412, 150, 40,
                                  i18n.t("menu.btn_options")))]
    if not WEB:                      # quitting a browser page = closing the tab
        buttons.append(("quit", Button(cx + 10, 412, 150, 40, i18n.t("menu.btn_quit"))))
    while True:
        dt = _tick()
        for e in pygame.event.get():
            if _bug_intercept(e, "home"):
                continue
            if e.type == pygame.QUIT:
                return "quit"
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_F11:
                    toggle_fullscreen()
                elif e.key == pygame.K_ESCAPE and not WEB:
                    if await _confirm_quit(surf, surf.copy()):
                        return "quit"
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return "campaign"
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for key, c in cards + buttons:
                    if c.click(e.pos):
                        return key
        _background(surf, "merope", dt)
        _title(surf, GAME_NAME.upper(), i18n.t("menu.home_subtitle"))
        mouse = pygame.mouse.get_pos()
        for _, c in cards + buttons:
            c.draw(surf, mouse)
        _foot(surf)
        _bug_overlay(surf, dt)
        _finish(surf)
        await asyncio.sleep(0)


# ----------------------------------------------------------------------
#  Ship selection
# ----------------------------------------------------------------------

SHIP_STATS = ("hull", "shield", "speed", "damage")
_STAT_MAX = {"hull": 1.8, "shield": 1.3, "speed": 1.3, "damage": 1.35}
_STAT_COL = {"hull": C_HULL, "shield": C_SHIELD, "speed": C_NEON_YELLOW,
             "damage": C_NEON_ORANGE}


def _draw_ship_shape(surf, key, box, max_scale=2.4):
    """The ship silhouette (from player.SHIP_SHAPES), nose to the right,
    scaled down to fit `box` and centred in it: the shapes neither share a
    size nor sit on their origin."""
    shape = SHIP_SHAPES[key]
    xs = [px for px, _py in shape["hull"]]
    ys = [py for _px, py in shape["hull"]]
    scale = min(max_scale, box.w / (max(xs) - min(xs)), box.h / (max(ys) - min(ys)))
    cx = box.centerx - (min(xs) + max(xs)) / 2 * scale
    cy = box.centery - (min(ys) + max(ys)) / 2 * scale
    hull = [(cx + px * scale, cy + py * scale) for px, py in shape["hull"]]
    blit_glow(surf, cx - 15 * scale, cy, int(9 * scale), C_NEON_PINK, 0.5)
    neon_polygon(surf, C_NEON_CYAN, hull)
    cock = [(cx + px * scale, cy + py * scale) for px, py in shape["cockpit"]]
    pygame.draw.polygon(surf, C_NEON_PINK, cock)


def _ship_panel(surf, rect, key, selected, mouse):
    hovered = rect.collidepoint(mouse)
    r = rect.move(0, -6 if (hovered or selected) else 0)
    panel = pygame.Surface(r.size, pygame.SRCALPHA)
    panel.fill((*C_PANEL, 230))
    surf.blit(panel, r.topleft)
    accent = C_NEON_CYAN if selected else (C_NEON_PINK if hovered else C_PANEL_BORDER)
    pygame.draw.rect(surf, accent, r, 2 if (selected or hovered) else 1, border_radius=8)
    cx = r.centerx
    _draw_ship_shape(surf, key, pygame.Rect(r.x + 14, r.y + 12, r.w - 28, 56))
    name = i18n.ship_name(key)
    # the same size for every name, smaller only when one does not fit
    for font in (screen.FONT, screen.FONT_SMALL):
        if font.size(name)[0] <= r.w - 16:
            break
    t = font.render(name, True, C_NEON_CYAN if selected else C_TEXT)
    surf.blit(t, t.get_rect(midtop=(cx, r.y + 76)))
    by = r.y + 108
    p = SHIPS[key]
    for stat in SHIP_STATS:
        lbl = screen.FONT_TINY.render(i18n.t("ships.stat_" + stat), True, C_TEXT_GRAY)
        surf.blit(lbl, (r.x + 12, by - 1))
        bx = r.x + 76
        draw_bar(surf, bx, by + 1, r.right - 12 - bx, 7,
                 min(1.0, p[stat] / _STAT_MAX[stat]), _STAT_COL[stat], (30, 20, 42))
        by += 18
    dy = by + 8
    for line in wrap(i18n.ship_desc(key), screen.FONT_SMALL, r.w - 20):
        img = screen.FONT_SMALL.render(line, True, C_TEXT_GRAY)
        surf.blit(img, img.get_rect(midtop=(cx, dy)))
        dy += 19


async def ships():
    """Pick the starting hull (also the one flown in co-op). Returns "start",
    "menu" or "quit"; the choice is written to the meta on confirm."""
    audio.music("title")
    surf = screen.SCREEN = make_screen()
    meta = read_meta()
    selected = meta["ship"] if meta["ship"] in SHIP_ORDER else SHIP_ORDER[0]
    w, h = 198, 334
    # below the subtitle, and the buttons above the version line
    rects = [pygame.Rect(rr) for rr in _row_rects(len(SHIP_ORDER), w, h, 108, 14)]
    start_w, back_w, gap = 320, 110, 16
    x0 = WIDTH // 2 - (start_w + gap + back_w) // 2
    start = Button(x0, HEIGHT - 88, start_w, 40, "", C_NEON_CYAN)
    back = Button(x0 + start_w + gap, HEIGHT - 88, back_w, 40, "")

    def confirm():
        meta["ship"] = selected
        write_meta(meta)

    while True:
        dt = _tick()
        for e in pygame.event.get():
            if _bug_intercept(e, "ships"):
                continue
            if e.type == pygame.QUIT:
                return "quit"
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_F11:
                    toggle_fullscreen()
                elif e.key == pygame.K_ESCAPE:
                    return "menu"
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    confirm()
                    return "start"
                elif pygame.K_1 <= e.key <= pygame.K_9:
                    i = e.key - pygame.K_1
                    if i < len(SHIP_ORDER):
                        selected = SHIP_ORDER[i]
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, rr in enumerate(rects):
                    if rr.collidepoint(e.pos):
                        selected = SHIP_ORDER[i]
                if start.click(e.pos):
                    confirm()
                    return "start"
                if back.click(e.pos):
                    return "menu"
        _background(surf, "pleiades", dt, 170)
        _title(surf, i18n.t("ships.title"), i18n.t("ships.subtitle"), 40)
        mouse = pygame.mouse.get_pos()
        for i, rr in enumerate(rects):
            _ship_panel(surf, rr, SHIP_ORDER[i], SHIP_ORDER[i] == selected, mouse)
        start.text = i18n.t("ships.start")
        back.text = i18n.t("menu.btn_back")
        start.draw(surf, mouse)
        back.draw(surf, mouse)
        _foot(surf)
        _bug_overlay(surf, dt)
        _finish(surf)
        await asyncio.sleep(0)


# ----------------------------------------------------------------------
#  Sectors: the galaxy map
# ----------------------------------------------------------------------

async def galaxy_map(regions):
    """The galaxy: its REGIONS, red (invaded) or blue (freed). The start Bubble
    and the neighbours of freed regions can be entered. Returns the chosen
    region index, "menu" or "quit". TAB cycles the backgrounds; E opens the
    editor."""
    audio.music("title")
    surf = screen.SCREEN = make_screen()
    meta = read_meta()
    gmap = GalaxyMap(regions)
    adj = adjacency(regions)
    bg = 0                           # index into BG_MODES
    panel = pygame.Rect(600, 150, 330, 286)
    state_color = {"free": C_NEON_CYAN, "open": C_NEON_ORANGE, "invaded": C_NEON_RED}

    def freed(i):
        return region_id(regions[i]) in meta["liberated"]

    def is_open(i):
        return bool(regions[i].get("start")) or any(freed(j) for j in adj[i])

    def state(i):
        return "free" if freed(i) else ("open" if is_open(i) else "invaded")

    def sectors_done(region):
        return sum(1 for s in range(len(region["sectors"]))
                   if meta["progress"].get(sector_id(region, s), {}).get("cleared"))

    def draw_regions(hov):
        gmap.draw_frame(surf, hov, state_color[state(hov)] if hov is not None else C_NEON_CYAN)
        for i in range(len(regions)):
            col = state_color[state(i)]
            nx, ny = (int(v) for v in gmap.node(i))
            lit = i == hov
            blit_glow(surf, nx, ny, 24 if lit else 16, col, 0.6 if lit else 0.3)
            pygame.draw.circle(surf, col, (nx, ny), 8 if lit else 6)
            pygame.draw.circle(surf, (10, 6, 20), (nx, ny), 3)
            lx, ly = gmap.label_pos(i)
            for k, line in enumerate(wrap(regions[i].get("name", "?"), screen.FONT_TINY, 150)):
                t = screen.FONT_TINY.render(line, True, col if lit else BORDER)
                surf.blit(t, t.get_rect(center=(int(lx), int(ly) + k * 15)))

    def draw_panel(i):
        pygame.draw.rect(surf, C_PANEL, panel, border_radius=8)
        pygame.draw.rect(surf, C_PANEL_BORDER, panel, 2, border_radius=8)
        if i is None:
            for k, line in enumerate(wrap(i18n.t("map.pick"), screen.FONT_SMALL, panel.w - 28)):
                surf.blit(screen.FONT_SMALL.render(line, True, C_TEXT_GRAY),
                          (panel.x + 14, panel.y + 16 + k * 22))
            return
        region, st = regions[i], state(i)
        col = state_color[st]
        x, y = panel.x + 14, panel.y + 14
        surf.blit(screen.FONT.render(region.get("name", "?"), True, col), (x, y))
        surf.blit(screen.FONT_TINY.render(i18n.t("map.state_" + st), True, col), (x, y + 30))
        n = len(region["sectors"])
        rows = [(i18n.t("map.sectors_done", done=sectors_done(region), total=n), C_TEXT),
                (i18n.t("map.locked_sub") if st == "invaded" else i18n.t("map.enter_hint"),
                 C_TEXT_GRAY)]
        yy = y + 58
        for text, tcol in rows:
            for line in wrap(text, screen.FONT_SMALL, panel.w - 28):
                surf.blit(screen.FONT_SMALL.render(line, True, tcol), (x, yy))
                yy += 22
            yy += 4

    back = Button(40, HEIGHT - 60, 150, 40, i18n.t("menu.btn_back"))
    while True:
        dt = _tick()
        mouse = pygame.mouse.get_pos()
        hov = gmap.sector_at(mouse)
        for e in pygame.event.get():
            if _bug_intercept(e, "map"):
                continue
            if e.type == pygame.QUIT:
                return "quit"
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_F11:
                    toggle_fullscreen()
                elif e.key == pygame.K_ESCAPE:
                    return "menu"
                elif e.key == pygame.K_TAB:
                    bg = (bg + 1) % len(BG_MODES)
                elif e.key == pygame.K_e:
                    if await galaxy_editor() == "quit":
                        return "quit"
                    regions[:] = load_layout()       # pick up what the editor saved
                    gmap = GalaxyMap(regions)
                    adj = adjacency(regions)
                    meta = read_meta()
                elif pygame.K_1 <= e.key <= pygame.K_9:
                    i = e.key - pygame.K_1
                    if i < len(regions) and state(i) != "invaded":
                        return i
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if hov is not None and state(hov) != "invaded":
                    return hov
                if back.click(e.pos):
                    return "menu"
        surf.fill((6, 4, 16))
        gmap.draw_background(surf, BG_MODES[bg])
        _title(surf, i18n.t("map.title"), i18n.t("map.subtitle"), 40)
        _balance(surf, meta)
        draw_regions(hov)
        draw_panel(hov)
        back.draw(surf, mouse)
        surf.blit(screen.FONT_TINY.render(
            i18n.t("map.toggle", mode=i18n.t("map.bg_" + BG_MODES[bg])), True, C_TEXT_GRAY),
            (40, HEIGHT - 76))
        surf.blit(screen.FONT_TINY.render(i18n.t("map.edit_hint"), True, C_TEXT_GRAY),
                  (40, HEIGHT - 92))
        _foot(surf)
        _bug_overlay(surf, dt)
        _finish(surf)
        await asyncio.sleep(0)


def _encounter_art(level, is_titan):
    def draw(surf, rect, enabled):
        col = C_HEART if is_titan else LEVEL_LOOKS.get(level["key"], {}).get("grid", C_NEON_CYAN)
        blit_glow(surf, rect.centerx, rect.centery, 42, col, 0.4 if enabled else 0.12)
        pygame.draw.circle(surf, col if enabled else (70, 50, 90), rect.center,
                           22 if is_titan else 16, 2)
    return draw


async def region_screen(regions, ri):
    """A region's four sectors and its Titan. Sectors unlock in order; the Titan
    once the four are freed. Returns a sector index, "titan", "menu" or "quit"."""
    region = regions[ri]
    audio.music("title")
    surf = screen.SCREEN = make_screen()
    meta = read_meta()
    n = len(region["sectors"])
    items = list(range(n)) + ["titan"]
    rects = _row_rects(len(items), 180, 250, 150, 14)

    def done(s):
        return meta["progress"].get(sector_id(region, s), {}).get("cleared")

    def is_open(item):
        if item == "titan":
            return all(done(s) for s in range(n))
        return item == 0 or done(item - 1)

    def build(idx, item):
        if item == "titan":
            level, open_, sid = region["titan"], is_open("titan"), titan_id(region)
            title = i18n.boss_name("titan")
        else:
            level, open_, sid = region["sectors"][item], is_open(item), sector_id(region, item)
            title = i18n.level_name(level["key"]) if open_ else i18n.t("sectors.number", n=item + 1)
        e = meta["progress"].get(sid, {})
        best = e.get("best")
        if open_:
            lines = [(i18n.t("sectors.boss", name=i18n.boss_name(level["boss"])), C_HEART),
                     (i18n.t("sectors.deaths", deaths=e.get("deaths", 0)), C_TEXT_GRAY),
                     (i18n.t("sectors.best", time=best) if best is not None
                      else i18n.t("sectors.not_cleared"),
                      C_NEON_CYAN if best is not None else C_TEXT_GRAY)]
        else:
            lines = [(i18n.t("sectors.locked"), C_TEXT_GRAY),
                     (i18n.t("sectors.locked_sub"), C_TEXT_GRAY)]
        accent = C_HEART if item == "titan" else C_NEON_CYAN
        return Card(rects[idx], title, lines, _encounter_art(level, item == "titan"), accent, open_)

    cards = [build(idx, item) for idx, item in enumerate(items)]
    back = Button(WIDTH // 2 - BTN_W // 2, HEIGHT - 62, BTN_W, 40, i18n.t("menu.btn_back"))
    while True:
        dt = _tick()
        mouse = pygame.mouse.get_pos()
        for e in pygame.event.get():
            if _bug_intercept(e, "region"):
                continue
            if e.type == pygame.QUIT:
                return "quit"
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_F11:
                    toggle_fullscreen()
                elif e.key == pygame.K_ESCAPE:
                    return "menu"
                elif pygame.K_1 <= e.key <= pygame.K_9:
                    i = e.key - pygame.K_1
                    if i < len(cards) and cards[i].enabled:
                        return items[i]
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for idx, c in enumerate(cards):
                    if c.click(e.pos):
                        return items[idx]
                if back.click(e.pos):
                    return "menu"
        _background(surf, region["sectors"][0]["key"], dt, 165)
        _title(surf, region.get("name", "?"), i18n.t("region.subtitle"), 40)
        _balance(surf, meta)
        for c in cards:
            c.draw(surf, mouse)
        back.draw(surf, mouse)
        _foot(surf)
        _bug_overlay(surf, dt)
        _finish(surf)
        await asyncio.sleep(0)


async def galaxy_editor():
    """Paint your own REGIONS onto the galaxy grid. Returns "menu" or "quit".

    Left-drag paints the active region's cells, right-drag erases. N adds a
    region, X removes it, R renames it, B marks it the start Bubble, S saves the
    layout to saves/galaxy_layout.json (read back by the map and the campaign).
    Each region keeps its four sectors + Titan (edited elsewhere for now)."""
    audio.music("title")
    surf = screen.SCREEN = make_screen()
    regions = copy.deepcopy(load_layout())
    gmap = GalaxyMap(regions)                 # geometry only; `owner` holds edits
    owner = [[EMPTY] * COLS for _ in range(RINGS)]
    for idx, reg in enumerate(regions):
        for k, m in reg["cells"]:
            if 0 <= k < RINGS and 0 <= m < COLS:
                owner[k][m] = idx
    active = 0
    paint = None                              # "set"/"erase" while a button is held
    renaming = False
    notice = [None, 0.0]
    palette = (C_NEON_CYAN, C_NEON_ORANGE, C_NEON_PINK, C_NEON_YELLOW,
               C_NEON_PURPLE, C_THARG, C_SHIELD, C_HEART)
    panel = pygame.Rect(600, 92, 342, 380)

    def color(idx):
        return palette[idx % len(palette)]

    def flash(key):
        notice[0], notice[1] = i18n.t(key), 2.0

    def add():
        nonlocal active
        regions.append(new_region(i18n.t("editor.new_name", n=len(regions) + 1)))
        active = len(regions) - 1

    def remove():
        nonlocal active
        if len(regions) <= 1:
            return
        for k in range(RINGS):
            for m in range(COLS):
                if owner[k][m] == active:
                    owner[k][m] = EMPTY
                elif owner[k][m] > active:
                    owner[k][m] -= 1
        del regions[active]
        active = max(0, min(active, len(regions) - 1))

    def set_start():
        for idx, reg in enumerate(regions):
            reg["start"] = idx == active

    def save():
        for idx, reg in enumerate(regions):
            reg["cells"] = [[k, m] for k in range(RINGS) for m in range(COLS)
                            if owner[k][m] == idx]
        flash("editor.saved" if save_layout(regions) else "editor.save_failed")

    while True:
        dt = _tick()
        mouse = pygame.mouse.get_pos()
        cell = gmap.cell_at(mouse)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return "quit"
            if e.type == pygame.KEYDOWN:
                if renaming:
                    reg = regions[active]
                    if e.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                        renaming = False
                    elif e.key == pygame.K_BACKSPACE:
                        reg["name"] = reg.get("name", "")[:-1]
                    elif e.unicode.isprintable() and len(reg.get("name", "")) < 22:
                        reg["name"] = reg.get("name", "") + e.unicode
                    continue
                if e.key == pygame.K_F11:
                    toggle_fullscreen()
                elif e.key == pygame.K_ESCAPE:
                    return "menu"
                elif e.key == pygame.K_TAB:
                    active = (active + 1) % len(regions)
                elif pygame.K_1 <= e.key <= pygame.K_9 and e.key - pygame.K_1 < len(regions):
                    active = e.key - pygame.K_1
                elif e.key == pygame.K_n:
                    add()
                elif e.key in (pygame.K_x, pygame.K_DELETE):
                    remove()
                elif e.key == pygame.K_b:
                    set_start()
                elif e.key in (pygame.K_r, pygame.K_F2):
                    renaming, regions[active]["name"] = True, regions[active].get("name", "")
                elif e.key == pygame.K_s:
                    save()
            elif e.type == pygame.MOUSEBUTTONDOWN:
                paint = "set" if e.button == 1 else "erase" if e.button == 3 else paint
            elif e.type == pygame.MOUSEBUTTONUP:
                paint = None
        if paint and cell and not panel.collidepoint(mouse):
            owner[cell[0]][cell[1]] = active if paint == "set" else EMPTY
        if notice[1] > 0:
            notice[1] -= dt

        surf.fill((6, 4, 16))
        blit_glow(surf, *gmap.center, int(gmap.core * 2.2), C_NEON_YELLOW, 0.3)
        grid = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for k in range(RINGS):
            for m in range(COLS):
                poly = [(int(x), int(y)) for x, y in gmap.cell_polygon(k, m)]
                if owner[k][m] != EMPTY:
                    pygame.draw.polygon(grid, (*color(owner[k][m]),
                                               150 if owner[k][m] == active else 70), poly)
                pygame.draw.polygon(grid, (90, 80, 140, 80), poly, 1)
        surf.blit(grid, (0, 0))
        if cell and not panel.collidepoint(mouse):
            pygame.draw.polygon(surf, (255, 255, 255),
                                [(int(x), int(y)) for x, y in gmap.cell_polygon(*cell)], 2)
        _title(surf, i18n.t("editor.title"), i18n.t("editor.subtitle"), 36)
        pygame.draw.rect(surf, C_PANEL, panel, border_radius=8)
        pygame.draw.rect(surf, C_PANEL_BORDER, panel, 2, border_radius=8)
        y = panel.y + 12
        for idx in range(len(regions)):
            sw = pygame.Rect(panel.x + 12, y + 2, 14, 14)
            pygame.draw.rect(surf, color(idx), sw)
            if idx == active:
                pygame.draw.rect(surf, (255, 255, 255), sw.inflate(6, 6), 1)
            tag = "  " + i18n.t("editor.bubble_tag") if regions[idx].get("start") else ""
            name = (regions[idx].get("name", "?") + tag
                    + ("_" if renaming and idx == active else ""))
            surf.blit(screen.FONT_SMALL.render(f"{idx + 1}. {name}", True,
                                               C_TEXT if idx == active else C_TEXT_GRAY),
                      (panel.x + 36, y))
            y += 22
        hy = panel.bottom - 96
        for line in i18n.lines("editor.help"):
            surf.blit(screen.FONT_TINY.render(line, True, C_TEXT_GRAY), (panel.x + 12, hy))
            hy += 15
        if notice[0] and notice[1] > 0:
            surf.blit(screen.FONT_SMALL.render(notice[0], True, C_NEON_CYAN),
                      (panel.x + 12, panel.bottom - 26))
        _foot(surf)
        _finish(surf)
        await asyncio.sleep(0)


# ----------------------------------------------------------------------
#  Hangar
# ----------------------------------------------------------------------

async def hangar():
    """Permanent upgrades. Returns "menu" or "quit"."""
    audio.music("hangar")
    surf = screen.SCREEN = make_screen()
    meta = read_meta()
    keys = list(HANGAR)
    row_w, row_h, step = 560, 32, 36
    top = 106
    rows = [Button(WIDTH // 2 - row_w // 2, top + i * step, row_w, row_h, "", C_ALLOY)
            for i in range(len(keys))]
    for b in rows:
        b.center = False
    back = Button(WIDTH // 2 - BTN_W // 2, HEIGHT - 66, BTN_W, 40, i18n.t("menu.btn_back"))

    def refresh():
        for key, b in zip(keys, rows):
            lvl = meta["hangar"].get(key, 0)
            top_lvl = HANGAR[key]["max"]
            b.text = i18n.t("hangar.line", name=i18n.hangar_name(key), level=lvl, max=top_lvl)
            if lvl >= top_lvl:
                b.right, b.enabled = i18n.t("hangar.maxed"), False
            else:
                cost = hangar_cost(key, lvl)
                b.right = str(cost)
                b.enabled = meta["alloys"] >= cost

    def buy(i):
        key = keys[i]
        lvl = meta["hangar"].get(key, 0)
        if lvl >= HANGAR[key]["max"]:
            return
        cost = hangar_cost(key, lvl)
        if meta["alloys"] < cost:
            return
        meta["alloys"] -= cost
        meta["hangar"][key] = lvl + 1
        write_meta(meta)
        refresh()

    refresh()
    while True:
        dt = _tick()
        for e in pygame.event.get():
            if _bug_intercept(e, "hangar"):
                continue
            if e.type == pygame.QUIT:
                return "quit"
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_F11:
                    toggle_fullscreen()
                elif e.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                    return "menu"
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, b in enumerate(rows):
                    if b.click(e.pos):
                        buy(i)
                if back.click(e.pos):
                    return "menu"
        _background(surf, "oracle", dt, 175)
        _title(surf, i18n.t("hangar.title"), i18n.t("hangar.subtitle"), 40)
        _balance(surf, meta)
        mouse = pygame.mouse.get_pos()
        hovered = None
        for i, b in enumerate(rows):
            b.draw(surf, mouse)
            if b.rect.collidepoint(mouse):
                hovered = keys[i]
        text = i18n.hangar_desc(hovered) if hovered else i18n.t("hangar.hint")
        t = screen.FONT_SMALL.render(text, True, C_TEXT if hovered else C_TEXT_GRAY)
        surf.blit(t, t.get_rect(center=(WIDTH // 2, top + len(rows) * step + 14)))
        back.draw(surf, mouse)
        _foot(surf)
        _bug_overlay(surf, dt)
        _finish(surf)
        await asyncio.sleep(0)


# ----------------------------------------------------------------------
#  Options
# ----------------------------------------------------------------------

async def options():
    """Fullscreen, language and music volume. Returns "menu" or "quit"."""
    audio.music("title")
    surf = screen.SCREEN = make_screen()
    cx = WIDTH // 2
    full = Button(cx - BTN_W // 2, 190, BTN_W, BTN_H, "", C_NEON_CYAN)
    lang = Button(cx - BTN_W // 2, 246, BTN_W, BTN_H, "", C_NEON_CYAN)
    vol = Button(cx - BTN_W // 2, 302, BTN_W, BTN_H, "", C_NEON_CYAN)
    back = Button(cx - BTN_W // 2, 358, BTN_W, BTN_H, "")

    def cycle_language():
        """Next installed language, remembered for the next launches."""
        i18n.remember(i18n.set_language(i18n.next_language()))

    while True:
        dt = _tick()
        for e in pygame.event.get():
            if _bug_intercept(e, "options"):
                continue
            if e.type == pygame.QUIT:
                return "quit"
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_F11:
                    toggle_fullscreen()
                elif e.key == pygame.K_ESCAPE:
                    return "menu"
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if full.click(e.pos):
                    toggle_fullscreen()
                elif lang.click(e.pos):
                    cycle_language()
                elif vol.click(e.pos):
                    audio.next_volume()
                elif back.click(e.pos):
                    return "menu"
        # read again on every frame: F11 and the language button change these
        is_full = bool(pygame.display.get_surface().get_flags() & pygame.FULLSCREEN)
        full.text = i18n.t("menu.fullscreen_on") if is_full else i18n.t("menu.fullscreen_off")
        full.enabled = not WEB
        lang.text = i18n.t("menu.language", name=i18n.language_name())
        vol.text = i18n.t("menu.music", pct=round(audio.volume() * 100))
        back.text = i18n.t("menu.btn_back")
        _background(surf, "pleiades", dt, 170)
        _title(surf, i18n.t("menu.options_title"))
        mouse = pygame.mouse.get_pos()
        full.draw(surf, mouse)
        lang.draw(surf, mouse)
        vol.draw(surf, mouse)
        back.draw(surf, mouse)
        _foot(surf)
        _bug_overlay(surf, dt)
        _finish(surf)
        await asyncio.sleep(0)


# ----------------------------------------------------------------------
#  Co-op lobby (desktop only)
# ----------------------------------------------------------------------

LOBBY_HELLO_WAIT = 5.0           # seconds a host waits for the partner's hello
_ADDRESS_CHARS = set("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-")


def _connect_in_background(net, address):
    """Joins `address` in a thread, so the screen keeps drawing. Returns a
    dict that gets "link" or "error"; setting "cancel" closes a late link."""
    import threading

    result = {}

    def run():
        try:
            link = net.connect(address)
        except OSError as exc:
            result["error"] = exc.strerror or str(exc)
            return
        if result.get("cancel"):
            link.close(farewell=False)
        else:
            result["link"] = link

    threading.Thread(target=run, daemon=True).start()
    return result


async def lobby():
    """Host a co-op game or join one on the local network. Returns a
    `coop.Session`, "menu" or "quit".

    A host gets its session as soon as a partner said hello (it then picks
    the sector); a client once the host started, with `session.start_level`.
    """
    import socket

    from maelstrom import net    # desktop only: never imported in the browser
    from maelstrom.session.coop import Session, clean_profile, profile

    surf = screen.SCREEN = make_screen()
    meta = read_meta()
    me = profile(meta)
    my_name = socket.gethostname()[:24]
    my_ip = net.local_ip()
    browser = net.Browser()
    state = "idle"               # idle, hosting, greeting, connecting, joined
    host = link = pending = None
    typed = ""
    error = None
    joined_name = ""
    greet_t = 0.0

    cx = WIDTH // 2
    host_btn = Button(60, 150, 380, 52, "", C_PLAYERS[0])
    join_btn = Button(770, 404, 130, 40, "", C_PLAYERS[1])
    field = pygame.Rect(500, 404, 258, 40)
    back = Button(cx - BTN_W // 2, HEIGHT - 62, BTN_W, 40, "")
    cancel = Button(cx - 110, HEIGHT // 2 + 60, 220, 40, "")
    found_btns = []

    def reset(message=None):
        nonlocal state, host, link, pending, error
        if host:
            host.close()
        if link:
            link.close()
        if pending is not None:
            pending["cancel"] = True
        state, host, link, pending, error = "idle", None, None, None, message

    def start_hosting():
        nonlocal state, host, error
        try:
            host = net.Host(i18n.t("lan.default_host_name", host=my_name))
        except OSError as exc:
            error = i18n.t("coop.error_port", error=exc.strerror or exc)
            return
        state, error = "hosting", None

    def join(address):
        nonlocal state, pending, error, joined_name
        address = address.strip()
        if not address:
            return
        pending = _connect_in_background(net, address)
        state, error, joined_name = "connecting", None, address

    def leave(outcome):
        browser.close()
        reset()
        return outcome

    while True:
        dt = _tick()
        for e in pygame.event.get():
            if _bug_intercept(e, "lobby"):
                continue
            if e.type == pygame.QUIT:
                return leave("quit")
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_F11:
                    toggle_fullscreen()
                elif e.key == pygame.K_ESCAPE:
                    if state == "idle":
                        return leave("menu")
                    reset()
                elif state == "idle":
                    if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        join(typed)
                    elif e.key == pygame.K_BACKSPACE:
                        typed = typed[:-1]
                    elif e.unicode in _ADDRESS_CHARS and len(typed) < 40:
                        typed += e.unicode
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if state == "idle":
                    if host_btn.click(e.pos):
                        start_hosting()
                    elif join_btn.click(e.pos):
                        join(typed)
                    elif back.click(e.pos):
                        return leave("menu")
                    else:
                        for address, b in found_btns:
                            if b.click(e.pos):
                                join(address)
                elif cancel.click(e.pos):
                    reset()

        # --- the network side of each state ----------------------------
        if state == "hosting" and host.link is not None:
            link = host.release()
            host, state, greet_t = None, "greeting", 0.0
        elif state == "greeting":
            greet_t += dt
            for msg in link.poll():
                if msg.get("type") != "hello":
                    continue
                if msg.get("protocol") != net.PROTOCOL:
                    link.send({"type": "refuse", "reason": "version"})
                    reset(i18n.t("coop.error_version"))
                    break
                link.send({"type": "welcome", "name": my_name})
                session = Session(link, "host", [me, clean_profile(msg.get("profile"))],
                                  str(msg.get("name", "?"))[:24])
                link = None              # the session owns it now
                browser.close()
                return session
            if state == "greeting" and (not link.alive or greet_t > LOBBY_HELLO_WAIT):
                reset(i18n.t("coop.error_lost"))
        elif state == "connecting":
            if "error" in pending:
                reset(i18n.t("coop.error_connect", error=pending["error"]))
            elif "link" in pending:
                link, pending = pending["link"], None
                link.send({"type": "hello", "protocol": net.PROTOCOL,
                           "name": my_name, "profile": me})
                state = "joined"
        elif state == "joined":
            for msg in link.poll():
                kind = msg.get("type")
                if kind == "welcome":
                    joined_name = str(msg.get("name", joined_name))[:24]
                elif kind == "refuse":
                    reset(i18n.t("coop.error_version"))
                    break
                elif kind == "bye":
                    reset(i18n.t("coop.error_lost"))
                    break
                elif kind == "start":
                    players = msg.get("players")
                    if not isinstance(players, list) or len(players) != 2:
                        continue
                    session = Session(link, "client",
                                      [clean_profile(p) for p in players], joined_name)
                    try:
                        level = int(msg.get("level", 0))
                    except (TypeError, ValueError):
                        level = 0
                    session.start_level = max(0, min(len(LEVELS) - 1, level))
                    link = None
                    browser.close()
                    return session
            if state == "joined" and not link.alive:
                reset(i18n.t("coop.error_lost"))

        # --- drawing -----------------------------------------------------
        _background(surf, "maelstrom", dt, 170)
        _title(surf, i18n.t("coop.title"), i18n.t("coop.subtitle"), 40)
        mouse = pygame.mouse.get_pos()
        if state == "idle":
            host_btn.text = i18n.t("coop.btn_host")
            host_btn.draw(surf, mouse)
            for k, line in enumerate(wrap(i18n.t("coop.host_help"), screen.FONT_SMALL, 380)):
                t = screen.FONT_SMALL.render(line, True, C_TEXT_GRAY)
                surf.blit(t, (60, 216 + k * 20))

            t = screen.FONT.render(i18n.t("coop.found"), True, C_TEXT)
            surf.blit(t, (500, 120))
            found_btns = []
            for k, (address, info) in enumerate(browser.hosts()[:4]):
                b = Button(500, 150 + k * 48, 400, 40,
                           i18n.t("coop.found_line", name=info["name"], ip=address),
                           C_PLAYERS[1])
                b.center = False
                b.enabled = info["protocol"] == net.PROTOCOL
                if not b.enabled:
                    b.right = i18n.t("coop.other_version")
                b.draw(surf, mouse)
                found_btns.append((address, b))
            if not found_btns:
                t = screen.FONT_SMALL.render(i18n.t("coop.none_found"), True, C_TEXT_GRAY)
                surf.blit(t, (500, 160))

            t = screen.FONT_SMALL.render(i18n.t("coop.address"), True, C_TEXT)
            surf.blit(t, (500, 380))
            pygame.draw.rect(surf, C_PANEL, field, border_radius=5)
            pygame.draw.rect(surf, C_PANEL_BORDER, field, 2, border_radius=5)
            caret = "_" if int(pygame.time.get_ticks() / 500) % 2 == 0 else " "
            t = screen.FONT.render(typed + caret, True, C_TEXT)
            surf.blit(t, (field.x + 10, field.centery - t.get_height() // 2))
            join_btn.text = i18n.t("coop.btn_join")
            join_btn.draw(surf, mouse)

            if error:
                for k, line in enumerate(wrap(error, screen.FONT_SMALL, WIDTH - 120)):
                    t = screen.FONT_SMALL.render(line, True, C_NEON_RED)
                    surf.blit(t, t.get_rect(center=(cx, HEIGHT - 110 + k * 20)))
            back.text = i18n.t("menu.btn_back")
            back.draw(surf, mouse)
        else:
            if state in ("hosting", "greeting"):
                lines = [(i18n.t("coop.hosting"), C_TEXT),
                         (i18n.t("coop.hosting_ip", ip=my_ip, port=net.PORT),
                          C_PLAYERS[0])]
            elif state == "connecting":
                lines = [(i18n.t("coop.connecting", ip=joined_name), C_TEXT)]
            else:
                lines = [(i18n.t("coop.joined", name=joined_name), C_PLAYERS[1]),
                         (i18n.t("coop.wait_sector"), C_TEXT_GRAY)]
            box = pygame.Rect(cx - 280, HEIGHT // 2 - 90, 560, 210)
            pygame.draw.rect(surf, C_PANEL, box, border_radius=8)
            pygame.draw.rect(surf, C_PANEL_BORDER, box, 2, border_radius=8)
            dots = "." * (1 + int(pygame.time.get_ticks() / 400) % 3)
            for k, (line, col) in enumerate(lines):
                t = screen.FONT.render(line + (dots if k == 0 else ""), True, col)
                surf.blit(t, t.get_rect(center=(cx, box.y + 50 + k * 36)))
            cancel.text = i18n.t("menu.btn_cancel")
            cancel.draw(surf, mouse)
        _foot(surf)
        _bug_overlay(surf, dt)
        _finish(surf)
        await asyncio.sleep(0)
