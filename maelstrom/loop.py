"""The loop of one sector: `play()`.

Reads the events, forwards them to the game (`Game`), updates it and draws
it. A death does NOT leave this loop: "Reessayer" starts a new attempt in
the same `Game`, so a die-and-retry costs no loading. F8 opens the bug
report form (desktop), which freezes everything. Asynchronous, like
every loop of the game: pygbag requires it.
"""

import asyncio

import pygame

from settings.ui import FPS
from maelstrom import i18n, screen
from maelstrom.screen import make_screen, toggle_fullscreen
from maelstrom.session.game import Game


# The sector being played, for the crash net of main.py: a crash report
# attaches its state (see game/bugreport.py). main.py resets it when play()
# returns.
current_game = None


async def play(level_index):
    """Plays sector `level_index` until the player leaves it. Returns
    `(outcome, level)`: outcome is "menu", "quit", "hangar" or "next", and
    `level` the sector to play next (the same one after a death, the
    following one after a cleared sector)."""
    screen.SCREEN = make_screen()
    pygame.display.set_caption(i18n.window_caption())
    pygame.display.set_icon(screen.ICON)
    global current_game
    game = Game(level_index)
    current_game = game
    while True:
        dt = min(screen.CLOCK.tick(FPS) / 1000.0, 0.05)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                game.bank()
                return "quit", game.next_level
            if e.type == pygame.KEYDOWN:
                if game.showing_bug_form:
                    game.bug_form_key(e)     # the form takes the whole keyboard
                elif e.key == pygame.K_F11:
                    toggle_fullscreen()
                elif e.key == pygame.K_F8:
                    game.open_bug_form()     # captures this very frame
                else:
                    game.key_down(e.key)
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                game.click(e.pos)
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                game.release(e.pos)
            elif e.type == pygame.MOUSEMOTION:
                game.motion(e.pos)
            elif e.type == pygame.WINDOWFOCUSLOST:
                game.focus_lost()
        if game.exit_request:
            game.bank()
            return game.exit_request, game.next_level
        if not game.showing_bug_form:        # the form freezes everything
            game.update(dt)
        game.tick_notice(dt)                 # also runs under the pause menu
        game.draw()
        pygame.display.flip()
        # pygbag: yield to the browser on every frame, otherwise the tab
        # freezes. On the desktop, an invisible round trip through asyncio.
        await asyncio.sleep(0)
