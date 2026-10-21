"""The "report a bug" form: one line of text over a frozen screen.

Usable anywhere. In a sector the game passes itself (`open(game=self)`); on a
menu screen there is no game (`open(screen_name="home")`). The host loop drives
it: while `is_open`, feed every key to `key(e)` and every left click to
`click(pos)` (the form takes the whole input); after its own drawing, call
`draw(surf, dt)`; and `tick_notice(dt)` every frame. The screenshot, the
attempt snapshot and the context are captured WHEN THE FORM OPENS, so what is
written matches the moment of the bug and not the form itself.

`on_close` (optional) is called once the form closes, cancelled or submitted:
the game uses it to drop back onto the pause menu; the menus pass nothing and
simply stay on their screen. Writing is done by `maelstrom/bugreport.py`;
sending to the relay, when a relay is configured and the box is ticked, by
`maelstrom/bugsend.py`.
"""

import os

import pygame

from settings.ui import (
    BUG_BOX_H, BUG_BTN_H, BUG_BTN_W, BUG_FORM_H, BUG_FORM_W, BUG_NOTICE_TIME,
    C_NEON_CYAN, C_NEON_PINK, C_NEON_YELLOW, C_PANEL, C_PANEL_BORDER, C_TEXT,
    C_TEXT_GRAY, FPS, HEIGHT, WIDTH,
)
from maelstrom import bugreport, bugsend, i18n, screen
from maelstrom.widgets import Button

# the outcome of a send -> the notice key that tells the player
_SEND_NOTICE = {bugsend.SENT: "bug.sent", bugsend.QUEUED: "bug.queued",
                bugsend.REJECTED: "bug.send_failed"}


class BugForm:
    """Open, type into, submit and draw the bug report form. One instance per
    host (the game keeps one, the menus share one)."""

    def __init__(self):
        r = pygame.Rect(WIDTH // 2 - BUG_FORM_W // 2, HEIGHT // 2 - BUG_FORM_H // 2,
                        BUG_FORM_W, BUG_FORM_H)
        self.rect = r
        y = r.bottom - BUG_BTN_H - 20
        self.btn_save = Button(r.right - BUG_BTN_W - 24, y, BUG_BTN_W, BUG_BTN_H,
                               i18n.t("bug.btn_save"), C_NEON_CYAN)
        self.btn_cancel = Button(r.x + 24, y, BUG_BTN_W, BUG_BTN_H,
                                 i18n.t("bug.btn_cancel"), C_NEON_PINK)
        # the "send the report" checkbox, left of the text field's bottom edge
        self.check_rect = pygame.Rect(r.x + 24, r.y + 150, 20, 20)

        self.is_open = False
        self.game = None
        self.screen_name = None
        self.on_close = None
        self.text = ""
        self.caret_t = 0.0
        self.shot = self.state = self.state_error = self.context = None
        self.send = bugsend.consent()      # ticked by default when a relay is set
        self.ticket = None                 # the outbox ticket of the report sent
        self.status = None                 # None / "sending" / a bugsend outcome
        self.notice = ""
        self.notice_t = 0.0

    # --- open / close -------------------------------------------------------

    def open(self, game=None, shot=None, screen_name=None, on_close=None):
        """Freeze the screen and open the form. `shot` is an earlier capture
        (the pause menu passes the frame taken before its veil was drawn)."""
        if not bugreport.ENABLED or self.is_open:
            return
        # re-read the labels: the language may have changed since __init__
        self.btn_save.text = i18n.t("bug.btn_save")
        self.btn_cancel.text = i18n.t("bug.btn_cancel")
        self.game = game
        self.screen_name = screen_name
        self.on_close = on_close
        self.shot = shot if shot is not None else bugreport.capture_screen()
        self.state, self.state_error = bugreport.game_state(game)
        self.context = bugreport.game_context(game)
        self.send = bugsend.consent()
        self.text = ""
        self.caret_t = 0.0
        self.ticket = None
        self.status = None
        self.is_open = True

    def close(self):
        """Cancel (or after saving). Calls `on_close` if one was given."""
        self.is_open = False
        self.shot = self.state = self.state_error = self.context = None
        callback = self.on_close
        self.game = self.on_close = None
        if callback:
            callback()

    def submit(self):
        """Write the report, then send it when a relay is set and the box is
        ticked. The report is always on disk even if sending is off."""
        context = self.context
        if self.screen_name and context is not None:
            context = context + [("screen", self.screen_name)]
        folder = bugreport.write_report(
            self.text, game=self.game, shot=self.shot, state=self.state,
            state_error=self.state_error, context=context)
        wants_send = self.send and bugsend.enabled()
        self.close()
        if not folder:
            self.notify(i18n.t("bug.failed"))
            return
        bugsend.remember_consent(self.send)
        if not wants_send:
            self.notify(i18n.t("bug.saved", folder=os.path.basename(folder)))
            return
        try:
            self.ticket = bugsend.queue_report(folder, self.text)
        except OSError:
            self.notify(i18n.t("bug.saved", folder=os.path.basename(folder)))
            return
        self.status = "sending"
        bugsend.send_async([self.ticket])
        self.notify(i18n.t("bug.sending"))

    # --- input --------------------------------------------------------------

    def key(self, e):
        """A KEYDOWN while the form is open: it takes the whole keyboard."""
        if e.key == pygame.K_ESCAPE:
            self.close()
        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.submit()
        elif e.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
        elif (e.unicode and e.unicode.isprintable()
              and len(self.text) < bugreport.DESCRIPTION_MAX_LEN):
            self.text += e.unicode

    def click(self, pos):
        if self.btn_save.click(pos):
            self.submit()
        elif self.btn_cancel.click(pos):
            self.close()
        elif bugsend.enabled() and self.check_rect.inflate(220, 8).collidepoint(pos):
            self.send = not self.send

    # --- notice (also the send status) --------------------------------------

    def notify(self, text):
        """A line shown at the bottom of the screen for BUG_NOTICE_TIME seconds."""
        self.notice = text
        self.notice_t = BUG_NOTICE_TIME

    def tick_notice(self, dt):
        self.notice_t = max(0.0, self.notice_t - dt)
        if self.ticket is None:
            return
        for ticket, outcome in bugsend.results():
            if ticket != self.ticket:
                continue                 # an older report, retried at startup
            self.status, self.ticket = outcome, None
            self.notify(i18n.t(_SEND_NOTICE.get(outcome, "bug.send_failed")))

    # --- drawing ------------------------------------------------------------

    def draw(self, surf, dt=1 / FPS):
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((10, 4, 22, 214))
        surf.blit(veil, (0, 0))
        r = self.rect
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
        shown = self.text
        while shown and screen.FONT.size(shown)[0] > room:
            shown = shown[1:]
        if shown:
            txt = screen.FONT.render(shown, True, C_TEXT)
        else:
            txt = screen.FONT.render(i18n.t("bug.placeholder"), True, C_TEXT_GRAY)
        surf.blit(txt, txt.get_rect(midleft=(box.x + 12, box.centery)))
        self.caret_t += dt
        if int(self.caret_t * 2) % 2 == 0:
            cx = box.x + 12 + (screen.FONT.size(shown)[0] if shown else 0)
            pygame.draw.rect(surf, C_TEXT, (cx + 2, box.centery - 11, 2, 22))
        count = screen.FONT_SMALL.render(
            i18n.t("bug.count", count=len(self.text),
                   max=bugreport.DESCRIPTION_MAX_LEN), True, C_TEXT_GRAY)
        surf.blit(count, count.get_rect(topright=(box.right, box.bottom + 6)))

        self._draw_send_row(surf)
        mouse_pos = pygame.mouse.get_pos()
        self.btn_save.draw(surf, mouse_pos)
        self.btn_cancel.draw(surf, mouse_pos)

    def _draw_send_row(self, surf):
        """The 'send the report' checkbox, or a one-line reason it is off."""
        cb = self.check_rect
        if not bugsend.enabled():
            t = screen.FONT_SMALL.render(i18n.t("bug.offline"), True, C_TEXT_GRAY)
            surf.blit(t, (cb.x, cb.y + 1))
            return
        pygame.draw.rect(surf, C_NEON_CYAN, cb, 2, border_radius=4)
        if self.send:
            inner = cb.inflate(-8, -8)
            pygame.draw.rect(surf, C_NEON_CYAN, inner, border_radius=2)
        label = screen.FONT_SMALL.render(i18n.t("bug.send_label"), True, C_TEXT)
        surf.blit(label, (cb.right + 10, cb.y + 1))

    def draw_notice(self, surf):
        """The "report saved / sent" line, at the bottom centre."""
        if self.notice_t <= 0 or not self.notice:
            return
        img = screen.FONT_SMALL.render(self.notice, True, C_NEON_YELLOW)
        img.set_alpha(int(255 * min(1.0, self.notice_t)))   # fades on the last second
        surf.blit(img, img.get_rect(midbottom=(WIDTH // 2, HEIGHT - 16)))
