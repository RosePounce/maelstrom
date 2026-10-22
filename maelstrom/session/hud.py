"""HUD, banners and overlays (pause, death, sector cleared).

The HUD is drawn straight on the screen, over the world and outside the
screen shake:
  top left       sector, then the timed effects (bonus cyan, malus green);
  top centre     sector progress, or the Interceptor's heart;
  top right      meta-alloy of the attempt, Pause button;
  bottom left    hull, shield, weapon and level, AX missiles;
  bottom centre  co-op: the partner's hull and shield;
  bottom right   the AX button (for a finger).
"""

import math
import random

import pygame

from settings.balance import BONUSES, LEVELS, MALUSES, WEAPON_MAX_LEVEL
from settings.ui import (
    C_ALLOY, C_BONUS, C_HEART, C_HEART_COLD, C_HULL, C_HULL_BG, C_HULL_LOW,
    C_MALUS, C_MISSILE, C_NEON_CYAN, C_NEON_PINK, C_NEON_RED, C_NEON_YELLOW,
    C_PANEL, C_PANEL_BORDER, C_SHIELD, C_SHIELD_BG, C_TEXT, C_TEXT_GRAY,
    C_THARG, HEIGHT, HUD_BAR_H, HUD_BAR_W, MARGIN, OVERLAY_BTN_H,
    OVERLAY_BTN_W, OVERLAY_STEP, PAUSE_BTN_H, PAUSE_BTN_W, PROGRESS_W,
    TOUCH_BTN, WIDTH,
)
from maelstrom import bugreport, i18n, screen
from maelstrom.neon import blit_glow, draw_bar
from maelstrom.widgets import Button, stack_buttons


DEAD_DELAY = 1.0                 # the explosion plays before the overlay


class Hud:

    def layout_hud(self):
        self.btn_pause = Button(WIDTH - MARGIN - PAUSE_BTN_W, 6, PAUSE_BTN_W,
                                PAUSE_BTN_H, i18n.t("hud.btn_pause"))
        self.btn_ax = Button(WIDTH - MARGIN - TOUCH_BTN, HEIGHT - MARGIN - TOUCH_BTN,
                             TOUCH_BTN, TOUCH_BTN, i18n.t("hud.btn_ax"), C_MISSILE)

    # --- overlays -----------------------------------------------------------

    def open_overlay(self, kind):
        """Builds the buttons of an overlay as (action, Button) pairs. The
        first one is also the Enter key."""
        if self.coop:
            actions = self.coop_actions(kind)
        elif kind == "pause":
            actions = [("resume", i18n.t("pause.btn_resume")),
                       ("restart", i18n.t("pause.btn_restart"))]
            if bugreport.ENABLED:        # no report files in a browser
                actions.append(("bug", i18n.t("pause.btn_report_bug")))
            actions.append(("menu", i18n.t("pause.btn_menu")))
        elif kind == "dead":
            if self.checkpoint:
                actions = [("retry_boss", i18n.t("dead.btn_retry_boss")),
                           ("retry", i18n.t("dead.btn_retry_start"))]
            else:
                actions = [("retry", i18n.t("dead.btn_retry"))]
            actions += [("hangar", i18n.t("dead.btn_hangar")), ("menu", i18n.t("pause.btn_menu"))]
        else:
            if self.level_index + 1 < len(LEVELS):
                actions = [("next", i18n.t("clear.btn_next")),
                           ("hangar", i18n.t("dead.btn_hangar")),
                           ("menu", i18n.t("pause.btn_menu"))]
            else:
                actions = [("menu", i18n.t("pause.btn_menu"))]
        self.place_overlay(kind, actions)

    def coop_actions(self, kind):
        """Co-op: no hangar and no restart (the session goes on), the
        client leaves or waits for the host."""
        leave = ("menu", i18n.t("coop.btn_leave"))
        if kind == "pause":
            actions = [("resume", i18n.t("pause.btn_resume"))]
            if bugreport.ENABLED:
                actions.append(("bug", i18n.t("pause.btn_report_bug")))
            return actions + [leave]
        if kind == "lost" or self.role == "client":
            return [leave]
        if kind == "dead":
            if self.checkpoint:
                return [("retry_boss", i18n.t("dead.btn_retry_boss")),
                        ("retry", i18n.t("dead.btn_retry_start")), leave]
            return [("retry", i18n.t("dead.btn_retry")), leave]
        if self.level_index + 1 < len(LEVELS):
            return [("next", i18n.t("clear.btn_next")), leave]
        return [leave]

    def place_overlay(self, kind, actions):
        top = HEIGHT - 40 - len(actions) * OVERLAY_STEP
        buttons = stack_buttons([label for _, label in actions], WIDTH // 2, top,
                                OVERLAY_BTN_W, OVERLAY_BTN_H, OVERLAY_STEP)
        buttons[0].color = C_NEON_CYAN
        self.overlay = kind
        self.overlay_buttons = [(a, b) for (a, _), b in zip(actions, buttons)]

    def overlay_ready(self):
        return self.overlay != "dead" or self.phase_t >= DEAD_DELAY

    def draw_overlay(self, surf):
        if not self.overlay_ready():
            return
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((8, 4, 18, 190))
        surf.blit(veil, (0, 0))
        cx = WIDTH // 2
        key = self.level["key"]
        lines = []
        if self.overlay == "pause":
            title, color = i18n.t("pause.title"), C_NEON_PINK
            lines = [i18n.t("hud.sector", n=self.level_index + 1, name=i18n.level_name(key))]
            if self.coop:
                lines.append(i18n.t("coop.pause_running"))
        elif self.overlay == "lost":
            title, color = i18n.t("coop.lost_title"), C_NEON_RED
            lines = [i18n.t("coop.lost_sub"),
                     i18n.t("dead.alloys", alloys=self.attempt_alloys)]
        elif self.overlay == "dead":
            title, color = i18n.t("dead.title"), C_NEON_RED
            if self.boss is not None and self.phase_t >= 0:
                b = self.boss
                left = b.hearts - b.heart + 1
                lines.append(i18n.t("dead.boss", name=i18n.boss_name(b.key), hearts=left))
            else:
                lines.append(i18n.t("dead.progress", pct=self.progress() * 100))
            lines.append(i18n.t("dead.alloys", alloys=self.attempt_alloys))
            if not self.coop:
                lines.append(i18n.t("dead.deaths", deaths=self.meta["deaths"][self.level_index]))
        else:
            last = self.level_index + 1 >= len(LEVELS)
            title, color = ((i18n.t("victory.title"), C_THARG) if last
                            else (i18n.t("clear.title"), C_NEON_CYAN))
            if last:
                lines.append(i18n.t("victory.sub"))
            lines.append(i18n.t("clear.time", time=self.elapsed))
            lines.append(i18n.t("clear.kills", kills=self.kills))
            lines.append(i18n.t("dead.alloys", alloys=self.attempt_alloys))
            if not self.coop:
                lines.append(i18n.t("clear.deaths", deaths=self.meta["deaths"][self.level_index]))

        if self.role == "client" and self.overlay in ("dead", "cleared"):
            lines.append(i18n.t("coop.wait_host"))

        font = screen.FONT_HUGE if screen.FONT_HUGE.size(title)[0] < WIDTH - 60 else screen.FONT_BIG
        img = font.render(title, True, color)
        y = 70
        blit_glow(surf, cx, y, 160, color, 0.25)
        surf.blit(img, img.get_rect(center=(cx, y)))
        y += 56
        for line in lines:
            t = screen.FONT.render(line, True, C_TEXT)
            surf.blit(t, t.get_rect(center=(cx, y)))
            y += 28
        if self.overlay == "pause":
            self._draw_legend(surf, cx)
        mouse = pygame.mouse.get_pos()
        for _, b in self.overlay_buttons:
            b.draw(surf, mouse)

    def _draw_legend(self, surf, cx):
        """A reference of what every bonus and hazard does, on the pause menu:
        two columns, bonuses (cyan) left, hazards (green) right."""
        small, tiny = screen.FONT_SMALL, screen.FONT_TINY
        for x0, keys, color, head in (
                (cx - 350, list(BONUSES), C_BONUS, i18n.t("pause.legend_bonus")),
                (cx + 20, list(MALUSES), C_MALUS, i18n.t("pause.legend_malus"))):
            surf.blit(small.render(head, True, color), (x0, 150))
            y = 176
            for k in keys:
                surf.blit(tiny.render(i18n.pickup_name(k), True, color), (x0, y))
                surf.blit(tiny.render(i18n.pickup_info(k), True, C_TEXT_GRAY), (x0 + 145, y))
                y += 18

    # --- banners ------------------------------------------------------------

    def draw_banner(self, surf):
        b = self.banner
        if not b or self.overlay:
            return
        elapsed = b["max"] - b["t"]
        alpha = min(1.0, elapsed / 0.25, b["t"] / 0.5)
        if b["color"] == C_NEON_RED and int(elapsed * 5) % 2 == 1:
            alpha *= 0.45                        # the boss warning blinks
        cy = HEIGHT // 2 - 60
        img = screen.FONT_HUGE.render(b["title"], True, b["color"])
        if img.get_width() > WIDTH - 60:
            img = screen.FONT_BIG.render(b["title"], True, b["color"])
        img.set_alpha(int(255 * alpha))
        surf.blit(img, img.get_rect(center=(WIDTH // 2, cy)))
        if b["sub"]:
            sub = screen.FONT.render(b["sub"], True, C_TEXT)
            sub.set_alpha(int(255 * alpha))
            surf.blit(sub, sub.get_rect(center=(WIDTH // 2, cy + 44)))

    # --- HUD ----------------------------------------------------------------

    def draw_hud(self, surf):
        ship = self.ship
        key = self.level["key"]
        small, tiny = screen.FONT_SMALL, screen.FONT_TINY

        # top left: sector and effects
        label = small.render(i18n.t("hud.sector", n=self.level_index + 1, name=i18n.level_name(key)),
                             True, C_TEXT_GRAY)
        surf.blit(label, (MARGIN, 10))
        y = 34
        for eff, left in sorted(ship.effects.items()):
            col = C_MALUS if eff in MALUSES else C_BONUS
            t = small.render(i18n.t("hud.effect_line", label=i18n.effect_label(eff),
                                    tag=i18n.pickup_tag(eff), time=math.ceil(left)),
                             True, col)
            surf.blit(t, (MARGIN, y))
            y += 20

        # top centre: progress, or the Interceptor
        x0 = WIDTH // 2 - PROGRESS_W // 2
        if self.boss and self.phase in ("boss", "boss_dying"):
            b = self.boss
            exposed = b.state == "exposed"
            ratio = 0.0 if self.phase == "boss_dying" else b.heart_hp / b.heart_hp_max
            draw_bar(surf, x0, 26, PROGRESS_W, 9, ratio,
                     C_HEART if exposed else C_HEART_COLD, (40, 20, 20))
            t = small.render(i18n.t("banner.boss_hearts", name=i18n.boss_name(b.key),
                                    heart=min(b.heart, b.hearts), hearts=b.hearts), True,
                             C_HEART if exposed else C_TEXT)
            surf.blit(t, t.get_rect(center=(WIDTH // 2, 14)))
        else:
            draw_bar(surf, x0, 16, PROGRESS_W, 7, self.progress(), C_NEON_PINK, (40, 20, 50))
            pygame.draw.circle(surf, C_THARG, (x0 + PROGRESS_W + 10, 19), 6, 2)

        # top right: meta-alloy of the attempt, then Pause
        t = small.render(i18n.t("hud.alloys", alloys=self.attempt_alloys), True, C_ALLOY)
        surf.blit(t, (self.btn_pause.rect.x - 14 - t.get_width(), 12))
        mouse = pygame.mouse.get_pos()
        self.btn_pause.draw(surf, mouse)

        # bottom left: gauges, weapon, missiles
        bx, by = MARGIN, HEIGHT - 86
        panel = pygame.Surface((HUD_BAR_W + 96, 78), pygame.SRCALPHA)
        panel.fill((*C_PANEL, 150))
        surf.blit(panel, (bx - 6, by - 6))
        low = ship.hull < ship.hull_max * 0.3
        surf.blit(tiny.render(i18n.t("hud.hull"), True, C_TEXT_GRAY), (bx, by - 2))
        draw_bar(surf, bx + 70, by, HUD_BAR_W, HUD_BAR_H, ship.hull / ship.hull_max,
                 C_HULL_LOW if low else C_HULL, C_HULL_BG)
        surf.blit(tiny.render(i18n.t("hud.shield"), True, C_TEXT_GRAY), (bx, by + 15))
        shield_col = (90, 110, 130) if ship.has("shutdown") else C_SHIELD
        draw_bar(surf, bx + 70, by + 17, HUD_BAR_W, HUD_BAR_H,
                 ship.shield / ship.shield_max, shield_col, C_SHIELD_BG)
        w = small.render(i18n.t("hud.weapon", name=i18n.weapon_name(ship.weapon), level=ship.level),
                         True, C_NEON_YELLOW)
        surf.blit(w, (bx, by + 34))
        for i in range(WEAPON_MAX_LEVEL):
            col = C_NEON_YELLOW if i < ship.level else (60, 44, 70)
            pygame.draw.rect(surf, col, (bx + 2 + i * 14, by + 56, 10, 6))
        m = small.render(i18n.t("hud.missiles", count=ship.missiles), True, C_MISSILE)
        surf.blit(m, (bx + 90, by + 50))
        if self.coop:
            self._draw_partner(surf, bx + HUD_BAR_W + 110, by)

        # bottom right: AX button, round
        r = self.btn_ax.rect
        hovered = r.collidepoint(mouse)
        ready = ship.missiles > 0 and ship.missile_t <= 0 and not ship.has("shutdown")
        col = C_MISSILE if ready else (90, 80, 60)
        pygame.draw.circle(surf, (46, 24, 72) if not hovered else (74, 38, 112), r.center, r.w // 2)
        pygame.draw.circle(surf, col, r.center, r.w // 2, 2)
        t = small.render(i18n.t("hud.btn_ax"), True, col)
        surf.blit(t, t.get_rect(center=r.center))

    def _draw_partner(self, surf, bx, by):
        """Co-op: the other ship's name, hull and shield (or its return
        countdown), next to the local gauges."""
        i = 1 - self.me
        mate = self.ships[i]
        small, tiny = screen.FONT_SMALL, screen.FONT_TINY
        w = 150
        panel = pygame.Surface((w + 12, 50), pygame.SRCALPHA)
        panel.fill((*C_PANEL, 150))
        surf.blit(panel, (bx - 6, by + 22))
        name = i18n.t("coop.partner", n=i + 1, ship=i18n.ship_name(mate.ship_key))
        surf.blit(tiny.render(name, True, mate.color), (bx, by + 26))
        if mate.down:
            t = small.render(i18n.t("coop.partner_down", time=max(0.0, mate.respawn_t)),
                             True, C_NEON_RED)
            surf.blit(t, (bx, by + 44))
            return
        draw_bar(surf, bx, by + 44, w, 8, mate.hull / mate.hull_max,
                 C_HULL_LOW if mate.hull < mate.hull_max * 0.3 else C_HULL, C_HULL_BG)
        draw_bar(surf, bx, by + 57, w, 8, mate.shield / mate.shield_max,
                 C_SHIELD, C_SHIELD_BG)

    def draw_tags(self, surf):
        """Co-op: "P1" / "P2" over each ship, so that each player finds their own."""
        if not self.coop:
            return
        for i, ship in enumerate(self.ships):
            if ship.down:
                continue
            t = screen.FONT_TINY.render(i18n.t("coop.tag", n=i + 1), True, ship.color)
            surf.blit(t, t.get_rect(center=(int(ship.x), int(ship.y) - 26)))

    def draw_jamming(self, surf):
        """Jamming: torn lines across the picture."""
        if not self.ship.has("jamming") or self.phase not in ("play", "warning", "boss"):
            return
        for _ in range(6):
            y = random.randrange(HEIGHT)
            h = random.randint(2, 7)
            shift = random.randint(-24, 24)
            band = surf.subsurface((0, y, WIDTH, min(h, HEIGHT - y))).copy()
            surf.blit(band, (shift, y))
        if random.random() < 0.2:
            pygame.draw.rect(surf, C_PANEL_BORDER,
                             (0, random.randrange(HEIGHT), WIDTH, 1))
