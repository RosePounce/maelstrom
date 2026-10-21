"""
Maelstrom screens outside a sector: home, sectors, hangar, options.

The menu borrows from the game its window and fonts (`maelstrom.screen`), its
colors (`settings.ui`), its neon drawing (`maelstrom.neon`), its scrolling
backdrop (`maelstrom.backdrop`) and its Button class (`maelstrom.widgets`).

Each screen has its own loop and RETURNS a string (or a sector index)
instead of exiting on its own: "campaign", "hangar", "options", "menu",
"quit".
"""

import asyncio
import math

import pygame

from settings import GAME_NAME, VERSION_LABEL
from settings.balance import HANGAR, LEVELS, SHIP_ORDER, SHIPS, hangar_cost
from settings.ui import (
    C_ALLOY, C_HEART, C_HULL, C_NEON_CYAN, C_NEON_ORANGE, C_NEON_PINK,
    C_NEON_YELLOW, C_PANEL, C_PANEL_BORDER, C_SHIELD, C_TEXT, C_TEXT_GRAY,
    C_THARG, C_THARG_DARK, FPS, HEIGHT, LEVEL_LOOKS, WEB, WIDTH,
)
from maelstrom import i18n, screen
from maelstrom.backdrop import Backdrop
from maelstrom.neon import blit_glow, draw_bar, draw_sun, neon_polygon
from maelstrom.player import COCKPIT, HULL_SHAPE, SHIP_SHAPES
from maelstrom.screen import make_screen, toggle_fullscreen
from maelstrom.storage import read_meta, write_meta
from maelstrom.widgets import Button, wrap


BTN_W, BTN_H = 300, 44
MENU_SCROLL = 60                 # the backdrop drifts slowly behind the menus


def init():
    """Prepares the game. To be called first (main.py)."""
    i18n.set_language(i18n.detect())
    screen.init()


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

def _draw_ship(surf, x, y, scale):
    pts = [(x + px * scale, y + py * scale) for px, py in HULL_SHAPE]
    neon_polygon(surf, C_NEON_CYAN, pts)
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
    """Returns "campaign", "hangar", "options" or "quit"."""
    surf = screen.SCREEN = make_screen()
    pygame.display.set_caption(i18n.window_caption())
    pygame.display.set_icon(screen.ICON)
    meta = read_meta()
    w, h = 300, 250
    rects = _row_rects(2, w, h, 140, 30)
    cards = [
        ("campaign", Card(rects[0], i18n.t("menu.card_campaign"),
                          [(i18n.t("menu.card_campaign_sub"), C_TEXT)],
                          _art_campaign, C_NEON_CYAN)),
        ("hangar", Card(rects[1], i18n.t("menu.card_hangar"),
                        [(i18n.t("menu.card_hangar_sub"), C_TEXT),
                         (i18n.t("menu.alloy_balance", alloys=meta["alloys"]), C_ALLOY)],
                        _art_hangar, C_ALLOY)),
    ]
    cx = WIDTH // 2
    buttons = [("options", Button(cx - 160 if not WEB else cx - 75, 412, 150, 40,
                                  i18n.t("menu.btn_options")))]
    if not WEB:                      # quitting a browser page = closing the tab
        buttons.append(("quit", Button(cx + 10, 412, 150, 40, i18n.t("menu.btn_quit"))))
    while True:
        dt = _tick()
        for e in pygame.event.get():
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
    """Pick the starting hull. Returns "start", "menu" or "quit"; the choice is
    written to the meta on confirm."""
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
        _finish(surf)
        await asyncio.sleep(0)


# ----------------------------------------------------------------------
#  Sectors
# ----------------------------------------------------------------------

async def sectors():
    """Returns the index of the sector chosen, "menu" or "quit"."""
    surf = screen.SCREEN = make_screen()
    meta = read_meta()
    w, h = 214, 318
    rects = _row_rects(len(LEVELS), w, h, 110, 14)
    cards = []
    for i, level in enumerate(LEVELS):
        open_ = i < meta["unlocked"]
        key = level["key"]
        if open_:
            best = meta["best"][i]
            lines = [(i18n.level_lore(key), C_TEXT),
                     (i18n.t("sectors.boss", name=i18n.boss_name(level["boss"])), C_HEART),
                     (i18n.t("sectors.deaths", deaths=meta["deaths"][i]), C_TEXT_GRAY),
                     (i18n.t("sectors.best", time=best) if best is not None
                      else i18n.t("sectors.not_cleared"),
                      C_NEON_CYAN if best is not None else C_TEXT_GRAY)]
            title = i18n.level_name(key)
        else:
            lines = [(i18n.t("sectors.locked"), C_TEXT_GRAY),
                     (i18n.t("sectors.locked_sub"), C_TEXT_GRAY)]
            title = i18n.t("sectors.number", n=i + 1)
        cards.append(Card(rects[i], title, lines, _sector_art(i),
                          LEVEL_LOOKS[key]["grid"], open_))
    back = Button(WIDTH // 2 - BTN_W // 2, HEIGHT - 110, BTN_W, 40, i18n.t("menu.btn_back"))
    shown = LEVELS[min(meta["unlocked"], len(LEVELS)) - 1]["key"]
    while True:
        dt = _tick()
        for e in pygame.event.get():
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
                        return i
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, c in enumerate(cards):
                    if c.click(e.pos):
                        return i
                if back.click(e.pos):
                    return "menu"
        mouse = pygame.mouse.get_pos()
        for i, c in enumerate(cards):
            if c.enabled and c.rect.collidepoint(mouse):
                shown = LEVELS[i]["key"]
        _background(surf, shown, dt, 165)
        _title(surf, i18n.t("sectors.title"), i18n.t("sectors.subtitle"), 40)
        _balance(surf, meta)
        for c in cards:
            c.draw(surf, mouse)
        back.draw(surf, mouse)
        for k, line in enumerate(i18n.lines("sectors.controls_help")):
            t = screen.FONT_TINY.render(line, True, C_TEXT_GRAY)
            surf.blit(t, t.get_rect(center=(WIDTH // 2, HEIGHT - 56 + k * 16)))
        _foot(surf)
        _finish(surf)
        await asyncio.sleep(0)


# ----------------------------------------------------------------------
#  Hangar
# ----------------------------------------------------------------------

async def hangar():
    """Permanent upgrades. Returns "menu" or "quit"."""
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
        _finish(surf)
        await asyncio.sleep(0)


# ----------------------------------------------------------------------
#  Options
# ----------------------------------------------------------------------

async def options():
    """Fullscreen and language. Returns "menu" or "quit"."""
    surf = screen.SCREEN = make_screen()
    cx = WIDTH // 2
    full = Button(cx - BTN_W // 2, 190, BTN_W, BTN_H, "", C_NEON_CYAN)
    lang = Button(cx - BTN_W // 2, 246, BTN_W, BTN_H, "", C_NEON_CYAN)
    back = Button(cx - BTN_W // 2, 302, BTN_W, BTN_H, "")

    def cycle_language():
        """Next installed language, remembered for the next launches."""
        i18n.remember(i18n.set_language(i18n.next_language()))

    while True:
        dt = _tick()
        for e in pygame.event.get():
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
                elif back.click(e.pos):
                    return "menu"
        # read again on every frame: F11 and the language button change these
        is_full = bool(pygame.display.get_surface().get_flags() & pygame.FULLSCREEN)
        full.text = i18n.t("menu.fullscreen_on") if is_full else i18n.t("menu.fullscreen_off")
        full.enabled = not WEB
        lang.text = i18n.t("menu.language", name=i18n.language_name())
        back.text = i18n.t("menu.btn_back")
        _background(surf, "pleiades", dt, 170)
        _title(surf, i18n.t("menu.options_title"))
        mouse = pygame.mouse.get_pos()
        full.draw(surf, mouse)
        lang.draw(surf, mouse)
        back.draw(surf, mouse)
        _foot(surf)
        _finish(surf)
        await asyncio.sleep(0)
