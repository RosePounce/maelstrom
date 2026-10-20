"""Controls: keyboard, mouse and finger.

Movement is read CONTINUOUSLY (`input_axes`, arrows + ZQSD + WASD, so both
AZERTY and QWERTY work without a setting). The rest arrives as events,
forwarded by `loop.play()`: `key_down`, `click`, `release`, `motion`.
A press that lands on no button starts a DRAG: the ship follows the
pointer's motion (relative, so the finger never hides the ship).
"""

import math

import pygame

from settings.ui import DRAG_GAIN
from maelstrom import bugreport


UP = (pygame.K_UP, pygame.K_z, pygame.K_w)
DOWN = (pygame.K_DOWN, pygame.K_s)
LEFT = (pygame.K_LEFT, pygame.K_q, pygame.K_a)
RIGHT = (pygame.K_RIGHT, pygame.K_d)
CONFIRM = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_r)
MISSILE_KEYS = (pygame.K_SPACE, pygame.K_x)


class Controls:

    def input_axes(self):
        keys = pygame.key.get_pressed()
        ax = any(keys[k] for k in RIGHT) - any(keys[k] for k in LEFT)
        ay = any(keys[k] for k in DOWN) - any(keys[k] for k in UP)
        if ax and ay:
            ax, ay = ax / math.sqrt(2), ay / math.sqrt(2)
        return ax, ay

    def key_down(self, key):
        if key in (pygame.K_ESCAPE, pygame.K_p):
            if self.overlay == "pause":
                self.close_pause()
            elif self.overlay is None:
                self.open_pause()
            return
        if self.overlay in ("dead", "cleared"):
            if key in CONFIRM and self.overlay_ready():
                self.do_action(self.overlay_buttons[0][0])
            return
        if self.overlay is None and key in MISSILE_KEYS:
            self.fire_missiles()

    def click(self, pos):
        if self.showing_bug_form:        # the form captures every click
            self.click_bug_form(pos)
            return
        if self.overlay:
            if not self.overlay_ready():
                return
            for action, button in self.overlay_buttons:
                if button.click(pos):
                    self.do_action(action)
                    return
            return
        if self.btn_pause.click(pos):
            self.open_pause()
        elif self.btn_ax.click(pos):
            self.fire_missiles()
        else:
            self.pointer = pos

    def release(self, pos):
        self.pointer = None

    def motion(self, pos):
        if self.pointer is None or self.overlay or self.showing_bug_form:
            return
        self.drag[0] += (pos[0] - self.pointer[0]) * DRAG_GAIN
        self.drag[1] += (pos[1] - self.pointer[1]) * DRAG_GAIN
        self.pointer = pos

    # --- pause and overlays -------------------------------------------------

    def open_pause(self):
        if self.phase in ("dead", "cleared"):
            return
        # the frame under the pause menu, not yet drawn over: what its
        # "Signaler un bug" button will attach
        self.pause_shot = bugreport.capture_screen()
        self.paused = True
        self.pointer = None
        self.open_overlay("pause")

    def close_pause(self):
        self.paused = False
        self.overlay = None
        self.overlay_buttons = []

    def focus_lost(self):
        """The window (or the browser tab) lost the focus: pause, so that the
        ship does not die alone."""
        if self.overlay is None and not self.showing_bug_form:
            self.open_pause()

    def do_action(self, action):
        if action == "resume":
            self.close_pause()
        elif action in ("restart", "retry"):
            self.start(from_boss=False)
        elif action == "retry_boss":
            self.start(from_boss=True)
        elif action == "bug":
            self.open_bug_form(self.pause_shot)
        elif action == "hangar":
            self.exit_request = "hangar"
        elif action == "next":
            self.exit_request = "next"
        elif action == "menu":
            self.exit_request = "menu"
