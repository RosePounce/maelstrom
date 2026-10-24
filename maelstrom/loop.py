"""The loop of one sector: `play()`, and of a co-op game: `play_coop()`.

Reads the events, forwards them to the game (`Game`), updates it and draws
it. A death does NOT leave this loop: "Reessayer" starts a new attempt in
the same `Game`, so a die-and-retry costs no loading. F8 opens the bug
report form (desktop), which freezes everything. Asynchronous, like
every loop of the game: pygbag requires it.

A co-op game chains its sectors here rather than in main.py: the link stays
open from one sector to the next, and the client follows the host's "level"
message.
"""

import asyncio

import pygame

from settings.ui import FPS
from maelstrom import audio, i18n, screen
from maelstrom.screen import make_screen, toggle_fullscreen
from maelstrom.session.game import Game


# The sector being played, for the crash net of main.py: a crash report
# attaches its state (see game/bugreport.py). main.py resets it when play()
# returns.
current_game = None


def _prepare_window():
    screen.SCREEN = make_screen()
    pygame.display.set_caption(i18n.window_caption())
    pygame.display.set_icon(screen.ICON)


async def play(level, sid, carry=None):
    """Plays one level (a region's sector or its Titan) until the player leaves
    it. `level` is the level dict, `sid` its records id, `carry` the loadouts
    brought in. Returns `(outcome, game)`: outcome is "menu", "quit", "hangar"
    or "next"; the region flow reads `game.cleared` / `game.carry_out`."""
    _prepare_window()
    game = Game(level, sid, carry=carry)
    outcome = await _run(game)
    return outcome, game


async def play_coop(session, level_index):
    """Plays a co-op game from sector `level_index`, sector after sector,
    until one side leaves. Returns "menu" or "quit"; the session stays open
    (the caller closes it)."""
    global current_game
    _prepare_window()
    carry = None
    while True:
        game = Game(level_index, coop=session, carry=carry)
        outcome = await _run(game)
        current_game = None
        if outcome != "next":
            return outcome
        if session.role == "host":
            session.send({"type": "level", "level": game.next_level})
        level_index, carry = game.next_level, game.carry_out


async def _run(game):
    """The frames of one `Game`, until it asks to leave. Returns "quit" or
    `game.exit_request`."""
    global current_game
    current_game = game
    while True:
        dt = min(screen.CLOCK.tick(FPS) / 1000.0, 0.05)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                game.bank()
                return "quit"
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
            return game.exit_request
        if not game.showing_bug_form:        # the form freezes everything
            game.update(dt)
        game.tick_notice(dt)                 # also runs under the pause menu
        audio.music(game.music_track())
        game.draw()
        pygame.display.flip()
        # pygbag: yield to the browser on every frame, otherwise the tab
        # freezes. On the desktop, an invisible round trip through asyncio.
        await asyncio.sleep(0)
