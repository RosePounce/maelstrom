"""The "report a bug" form: one line of text over a frozen sector.

Opened by F8 (the screenshot is the exact frame the player saw) or by the
pause menu button (the screenshot is the frame taken when the pause menu
opened, before its veil was drawn). Both capture the screen, the attempt
snapshot and the context WHEN THE FORM OPENS, so what is written matches the
moment of the bug and not the form itself. Writing is done by
game/bugreport.py.

While the form is open, `loop.play` no longer calls `Game.update`: nothing
moves at all. Closing it lands on the PAUSE MENU when the ship was flying
(F8 in flight, or the pause button): in a shoot'em up, giving the sector back
at once would throw the player under fire. Over a death or victory screen,
it goes back to that screen.
"""

import os

import pygame

from settings.ui import (
    BUG_BOX_H, BUG_BTN_H, BUG_BTN_W, BUG_FORM_H, BUG_FORM_W, BUG_NOTICE_TIME,
    C_NEON_CYAN, C_NEON_PINK, C_NEON_YELLOW, C_PANEL, C_PANEL_BORDER, C_TEXT,
    C_TEXT_GRAY, FPS, HEIGHT, WIDTH,
)
from maelstrom import bugreport, i18n, screen
from maelstrom.widgets import Button


class BugForm:
    """Game methods: open, type into, submit and draw the bug report form."""

    def build_bug_form(self):
        """The form frame, centred, and its two buttons (in __init__)."""
        self.bug_form_rect = r = pygame.Rect(WIDTH // 2 - BUG_FORM_W // 2,
                                             HEIGHT // 2 - BUG_FORM_H // 2,
                                             BUG_FORM_W, BUG_FORM_H)
        y = r.bottom - BUG_BTN_H - 20
        self.btn_bug_save = Button(r.right - BUG_BTN_W - 24, y, BUG_BTN_W,
                                   BUG_BTN_H, i18n.t("bug.btn_save"), C_NEON_CYAN)
        self.btn_bug_cancel = Button(r.x + 24, y, BUG_BTN_W, BUG_BTN_H,
                                     i18n.t("bug.btn_cancel"), C_NEON_PINK)
        self.showing_bug_form = False
        self.bug_text = ""
        self.bug_caret_t = 0.0
        self.bug_shot = self.bug_state = self.bug_state_error = None
        self.bug_context = None
        self.pause_shot = None           # frame under the pause menu
        self.notice = ""
        self.notice_t = 0.0

    def open_bug_form(self, shot=None):
        """Freeze the sector and open the form. `shot` is an earlier capture
        (the pause menu passes the frame taken before it opened)."""
        if not bugreport.ENABLED or self.showing_bug_form:
            return
        if shot is None and self.overlay == "pause":
            shot = self.pause_shot       # F8 over the pause menu: the frame under it
        self.bug_shot = shot if shot is not None else bugreport.capture_screen()
        self.bug_state, self.bug_state_error = bugreport.game_state(self)
        self.bug_context = bugreport.game_context(self)
        self.shake = 0.0                 # a frozen frame must not keep shaking
        self.pointer = None
        self.bug_text = ""
        self.bug_caret_t = 0.0
        self.showing_bug_form = True

    def close_bug_form(self):
        """Cancel (or after saving): back to the pause menu, or to the death /
        victory screen the form was opened over."""
        self.showing_bug_form = False
        self.bug_shot = self.bug_state = self.bug_state_error = None
        self.bug_context = None
        if self.overlay is None:
            self.open_pause()

    def submit_bug_form(self):
        folder = bugreport.write_report(
            self.bug_text, game=self, shot=self.bug_shot, state=self.bug_state,
            state_error=self.bug_state_error, context=self.bug_context)
        self.close_bug_form()
        if folder:
            self.notify(i18n.t("bug.saved", folder=os.path.basename(folder)))
        else:
            self.notify(i18n.t("bug.failed"))

    def notify(self, text):
        """A line shown at the bottom of the screen for BUG_NOTICE_TIME seconds."""
        self.notice = text
        self.notice_t = BUG_NOTICE_TIME

    def tick_notice(self, dt):
        self.notice_t = max(0.0, self.notice_t - dt)

    def bug_form_key(self, e):
        """A KEYDOWN while the form is open: it takes the whole keyboard."""
        if e.key == pygame.K_ESCAPE:
            self.close_bug_form()
        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.submit_bug_form()
        elif e.key == pygame.K_BACKSPACE:
            self.bug_text = self.bug_text[:-1]
        elif (e.unicode and e.unicode.isprintable()
              and len(self.bug_text) < bugreport.DESCRIPTION_MAX_LEN):
            self.bug_text += e.unicode

    def click_bug_form(self, pos):
        if self.btn_bug_save.click(pos):
            self.submit_bug_form()
        elif self.btn_bug_cancel.click(pos):
            self.close_bug_form()

    def draw_bug_form(self, surf, dt=1 / FPS):
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((10, 4, 22, 214))
        surf.blit(veil, (0, 0))
        r = self.bug_form_rect
        pygame.draw.rect(surf, C_PANEL, r, border_radius=8)
        pygame.draw.rect(surf, C_PANEL_BORDER, r, 2, border_radius=8)
        surf.blit(screen.FONT_TITLE.render(i18n.t("bug.title"), True, C_NEON_PINK),
                  (r.x + 24, r.y + 18))
        surf.blit(screen.FONT_SMALL.render(i18n.t("bug.hint"), True, C_TEXT_GRAY),
                  (r.x + 24, r.y + 54))

        # the field shows the END of a long text: what is being typed stays
        # in view, like a single-line input
        box = pygame.Rect(r.x + 24, r.y + 84, r.width - 48, BUG_BOX_H)
        pygame.draw.rect(surf, (26, 14, 42), box, border_radius=6)
        pygame.draw.rect(surf, C_NEON_CYAN, box, 2, border_radius=6)
        room = box.width - 28
        shown = self.bug_text
        while shown and screen.FONT.size(shown)[0] > room:
            shown = shown[1:]
        if shown:
            txt = screen.FONT.render(shown, True, C_TEXT)
        else:
            txt = screen.FONT.render(i18n.t("bug.placeholder"), True, C_TEXT_GRAY)
        surf.blit(txt, txt.get_rect(midleft=(box.x + 12, box.centery)))
        self.bug_caret_t += dt
        if int(self.bug_caret_t * 2) % 2 == 0:
            cx = box.x + 12 + (screen.FONT.size(shown)[0] if shown else 0)
            pygame.draw.rect(surf, C_TEXT, (cx + 2, box.centery - 11, 2, 22))
        count = screen.FONT_SMALL.render(
            i18n.t("bug.count", count=len(self.bug_text),
                   max=bugreport.DESCRIPTION_MAX_LEN), True, C_TEXT_GRAY)
        surf.blit(count, count.get_rect(topright=(box.right, box.bottom + 6)))

        mouse_pos = pygame.mouse.get_pos()
        self.btn_bug_save.draw(surf, mouse_pos)
        self.btn_bug_cancel.draw(surf, mouse_pos)

    def draw_notice(self, surf):
        """The "report saved" line, at the bottom centre (the top holds the
        progress bar and the banners)."""
        if self.notice_t <= 0 or not self.notice:
            return
        img = screen.FONT_SMALL.render(self.notice, True, C_NEON_YELLOW)
        img.set_alpha(int(255 * min(1.0, self.notice_t)))   # fades on the last second
        surf.blit(img, img.get_rect(midbottom=(WIDTH // 2, HEIGHT - 16)))
