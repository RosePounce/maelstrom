"""The game's adapter to the bug report form.

The form itself lives in `maelstrom/bugform.py` and is shared with the out-of-
sector screens (`menu.py`). The game keeps one instance and, unlike a menu,
drops back onto the PAUSE MENU when the form closes over a flying ship: giving
the sector straight back would throw the player under fire. This mixin keeps
the method names the rest of the game already calls (`showing_bug_form`,
`open_bug_form`, `draw_bug_form`, ...), so `controls.py`, `game.py` and the
loop do not have to know the form moved out.
"""

from maelstrom import bugreport
from maelstrom.bugform import BugForm as _Form


class BugForm:
    """Game methods: open, drive and draw the shared bug report form."""

    def build_bug_form(self):
        """Create the form instance (called in `Game.__init__`)."""
        self.bugform = _Form()

    @property
    def showing_bug_form(self):
        return self.bugform.is_open

    def open_bug_form(self, shot=None):
        """F8 in flight, or the pause menu's "Signaler un bug" button. Over the
        pause menu the shot is the frame taken before its veil was drawn."""
        if not bugreport.ENABLED or self.bugform.is_open:
            return
        if shot is None and self.overlay == "pause":
            shot = self.pause_shot
        self.shake = 0.0                 # a frozen frame must not keep shaking
        self.pointer = None
        self.bugform.open(game=self, shot=shot, screen_name="sector",
                          on_close=self._after_bug_close)

    def _after_bug_close(self):
        """Closing over a flying ship lands on the pause menu, not back in
        the line of fire; over a death/victory screen it stays there."""
        if self.overlay is None:
            self.open_pause()

    def bug_form_key(self, e):
        self.bugform.key(e)

    def click_bug_form(self, pos):
        self.bugform.click(pos)

    def draw_bug_form(self, surf):
        self.bugform.draw(surf)

    def tick_notice(self, dt):
        self.bugform.tick_notice(dt)

    def draw_notice(self, surf):
        self.bugform.draw_notice(surf)
