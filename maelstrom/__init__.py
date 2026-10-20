"""The Maelstrom game, settings aside.

From the bottom up:
  - storage.py     meta-progression (files on the desktop, localStorage in
                   the browser), the log;
  - neon.py        synthwave drawing: glows, neon polygons, bars, sun;
  - screen.py      window, fonts, scanlines, `init()`;
  - widgets.py     the button;
  - effects.py     particles, floating texts, rings;
  - backdrop.py    the scrolling backdrop of a sector;
  - projectiles.py shots, AX missiles, caustic clouds;
  - player.py      the player's ship;
  - enemies.py     the Thargoids and the Interceptors;
  - pickups.py     containers: bonuses, maluses, unknown;
  - levels.py      the seeded waves of a sector;
  - bugreport.py   bug reports written to saves/bugs/ (desktop only);
  - session/       the Game class, split by responsibility;
  - loop.py        `play()`, the loop of one sector.

A module only imports those above it in this list, never the reverse.
"""
