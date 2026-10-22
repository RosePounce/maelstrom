"""Interface: the look of the game, with none of its rules.

Size of the canvas, synthwave colors, the palette of each sector, sizes of
the HUD and of the overlays.
"""

import os
import sys


# ----------------------------------------------------------------------
#  Platform
# ----------------------------------------------------------------------

# Under pygbag, the game runs in the browser (WebAssembly): no durable file
# system, no system font, no SDL renderer, and the loop must yield to the
# browser on every frame. Everything that follows from it is marked by this
# flag.
WEB = sys.platform == "emscripten"


# ----------------------------------------------------------------------
#  Canvas
# ----------------------------------------------------------------------

# A side scroller reads from left to right: the canvas is LOCKED to a 16:9
# landscape, 960 x 540 logical pixels (an integer x2 on a 1080p screen).
# SCALED stretches it to the window on the desktop; the pygbag page fits it
# to the browser window.
WIDTH, HEIGHT = 960, 540
FPS = 60

HORIZON_FRAC = 0.74            # horizon of the synthwave ground, part of the height
PLAY_TOP = 40                  # the ship cannot climb into the top HUD strip
PLAY_BOTTOM = HEIGHT - 12
PLAY_LEFT, PLAY_RIGHT = 24, WIDTH * 0.72   # the ship keeps room to see ahead


# ----------------------------------------------------------------------
#  Colors
# ----------------------------------------------------------------------

C_BACKGROUND   = (14, 8, 26)
C_PANEL        = (16, 10, 28)
C_PANEL_BORDER = (128, 52, 170)
C_TEXT         = (238, 228, 252)
C_TEXT_GRAY    = (152, 130, 184)
C_NEON_PINK    = (255, 72, 172)
C_NEON_CYAN    = (84, 236, 246)
C_NEON_PURPLE  = (176, 96, 255)
C_NEON_YELLOW  = (255, 206, 92)
C_NEON_RED     = (255, 70, 92)
C_NEON_ORANGE  = (255, 150, 70)
C_HULL         = (94, 232, 200)
C_HULL_LOW     = (255, 92, 92)
C_HULL_BG      = (30, 46, 50)
C_SHIELD       = (96, 178, 255)
C_SHIELD_BG    = (26, 34, 62)
C_BTN          = (46, 24, 72)
C_BTN_HOVER    = (74, 38, 112)
C_BTN_OFF      = (28, 16, 42)
C_ALLOY        = (150, 220, 255)      # persistent meta currency (meta-alloy)

# The Thargoids: organic green, hot hearts
C_THARG        = (80, 255, 170)
C_THARG_DARK   = (10, 34, 26)
C_THARG_SHOT   = (150, 255, 120)
C_HEART        = (255, 120, 60)
C_HEART_COLD   = (70, 140, 110)
C_CAUSTIC      = (170, 255, 60)

# The two ships of a co-op game: player 1 keeps the usual cyan
C_PLAYERS      = (C_NEON_CYAN, (255, 196, 84))

# Player weapons
C_PULSE        = C_NEON_CYAN
C_FRAG         = C_NEON_ORANGE
C_RAIL         = (255, 140, 255)
C_MISSILE      = C_NEON_YELLOW

# Pickups: what helps glows warm, what hurts glows Thargoid
C_BONUS        = C_NEON_CYAN
C_MALUS        = (200, 255, 70)
C_MYSTERY      = C_NEON_PURPLE


# ----------------------------------------------------------------------
#  Sector palettes
# ----------------------------------------------------------------------

# One look per sector (key of balance.LEVELS): sky, ground, grid, and the
# landmark drawn on the horizon ("sun", "station", "nebula", "maelstrom").
LEVEL_LOOKS = {
    "merope": {
        "sky_top": (16, 8, 38), "sky_low": (92, 24, 96),
        "ground_far": (40, 12, 58), "ground_near": (16, 6, 30),
        "grid": (176, 58, 210), "sun_top": (255, 92, 150),
        "sun_bot": (255, 206, 96), "landmark": "sun",
    },
    "oracle": {
        "sky_top": (20, 6, 24), "sky_low": (124, 34, 44),
        "ground_far": (54, 14, 30), "ground_near": (18, 6, 16),
        "grid": (255, 96, 80), "sun_top": (255, 116, 70),
        "sun_bot": (255, 220, 120), "landmark": "station",
    },
    "pleiades": {
        "sky_top": (6, 10, 34), "sky_low": (26, 58, 112),
        "ground_far": (14, 30, 64), "ground_near": (6, 10, 26),
        "grid": (70, 170, 255), "sun_top": (150, 210, 255),
        "sun_bot": (90, 255, 210), "landmark": "nebula",
    },
    "maelstrom": {
        "sky_top": (4, 12, 10), "sky_low": (18, 66, 48),
        "ground_far": (10, 36, 26), "ground_near": (4, 12, 10),
        "grid": (80, 255, 170), "sun_top": (120, 255, 180),
        "sun_bot": (30, 120, 90), "landmark": "maelstrom",
    },
}


# ----------------------------------------------------------------------
#  Interceptor looks
# ----------------------------------------------------------------------

# One look per Interceptor (key of balance.BOSSES). They are flower-like
# rosettes of veined petals spiralling around the heart, true to the Elite
# Dangerous models. "petals" is the count of the outer ring (rising menace),
# "swirl" how far a petal bends tangentially (the pinwheel), "tip" the petal
# end ("round", "barb" hooked sideways like a claw, "spike" a long sharp point).
# "petal"/"petal_dark" outline and fill, "vein" the central rib, "speck" the
# mottled bioluminescence (None = none), "eye" a dark central orb when closed
# (Cyclops) instead of the bright core the others show.
BOSS_LOOKS = {
    "cyclops": {                                   # silver-green, a dark eye
        "petals": 8, "swirl": 0.55, "tip": "round",
        "petal": (150, 235, 180), "petal_dark": (14, 42, 32),
        "vein": (92, 185, 135), "speck": None, "eye": (16, 50, 40),
    },
    "basilisk": {                                  # black petals, copper embers
        "petals": 10, "swirl": 0.60, "tip": "round",
        "petal": (216, 150, 74), "petal_dark": (26, 20, 12),
        "vein": (255, 150, 60), "speck": (255, 120, 44), "eye": None,
    },
    "medusa": {                                    # blue-black, red veins, barbs
        "petals": 11, "swirl": 0.58, "tip": "barb",
        "petal": (122, 134, 214), "petal_dark": (14, 16, 36),
        "vein": (230, 84, 72), "speck": (232, 92, 72), "eye": None,
    },
    "hydra": {                                     # toxic green, spiked star
        "petals": 13, "swirl": 0.42, "tip": "spike",
        "petal": (124, 255, 134), "petal_dark": (14, 44, 38),
        "vein": (96, 214, 150), "speck": (156, 255, 96), "eye": None,
    },
}

# Parallax stars: (share of the scroll speed, count, size, brightness)
STAR_LAYERS = ((0.06, 70, 1, 120), (0.16, 40, 1, 190), (0.34, 18, 2, 240))
GRID_ROWS = 9                  # horizontal lines of the ground
GRID_SPACING = 96              # space between two vertical lines, at the bottom
GRID_FAR_SCALE = 0.06          # how much the vertical lines converge at the horizon
GRID_SPEED = 1.6               # the ground scrolls faster than the play scroll


# ----------------------------------------------------------------------
#  Asset files
# ----------------------------------------------------------------------

# the project folder: this file is in settings/, the assets next to it
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_DIR = os.path.join(PROJECT_DIR, "assets")
FONT_PATH = os.path.join(ASSET_DIR, "DejaVuSansMono.ttf")


# ----------------------------------------------------------------------
#  Music
# ----------------------------------------------------------------------

# One track per key: file name in MUSIC_DIR WITHOUT extension (".ogg" is
# tried first, the only format sure to play in the browser, then ".mp3"),
# and whether it loops. A missing file is silence, not an error. The prompts
# that made them, and the phase each one goes with: docs/musique.md.
# A sector plays the track named after its key (balance.LEVELS), an
# Interceptor the one named after its key (balance.BOSSES).
MUSIC_DIR = os.path.join(ASSET_DIR, "music")
MUSIC = {
    "title":     ("title", True),
    "credits":   ("credits", False),
    "pause":     ("pause", True),
    "hangar":    ("hangar", True),
    "merope":    ("sector_1", True),
    "oracle":    ("sector_2", True),
    "pleiades":  ("sector_3", True),
    "maelstrom": ("sector_4", True),
    "warning":   ("warning", False),
    "cyclops":   ("boss_cyclops_basilisk", True),
    "basilisk":  ("boss_cyclops_basilisk", True),
    "medusa":    ("boss_medusa", True),
    "hydra":     ("boss_hydra", True),
    "dead":      ("dead", False),
    "cleared":   ("cleared", False),            # the sector-cleared fanfare
}
MUSIC_VOLUMES = (0.0, 0.25, 0.5, 0.75, 1.0)   # the steps of the options button
MUSIC_VOLUME = 0.5             # until the player picks one
MUSIC_FADE_IN = 400            # ms, when a looping track starts
MUSIC_JINGLE_FADE_IN = 180     # ms, when a one-shot jingle starts (warning,
                               # dead, cleared): short, so it still hits, but
                               # no hard click at the start
MUSIC_FADE_OUT = 1500          # ms, under the Interceptor's explosions
MUSIC_CROSSFADE = 450          # ms: a track change fades the old one out this
                               # long, then the new one fades in (one stream,
                               # so a bridge, not an overlap) -- no hard cut at
                               # the Interceptor's arrival (sector -> warning -> boss)


# ----------------------------------------------------------------------
#  Fonts (sizes in logical pixels)
# ----------------------------------------------------------------------

FONT_SIZES = {"title": 26, "big": 32, "normal": 19, "small": 16, "tiny": 12,
              "huge": 52}


# ----------------------------------------------------------------------
#  HUD and overlays
# ----------------------------------------------------------------------

MARGIN = 12
HUD_BAR_W, HUD_BAR_H = 190, 10  # hull and shield gauges, bottom left
PROGRESS_W = 300                # level progress / boss hearts, top centre
TOUCH_BTN = 58                  # side of the AX button (bottom right)
PAUSE_BTN_W, PAUSE_BTN_H = 76, 30
OVERLAY_BTN_W, OVERLAY_BTN_H = 320, 44
OVERLAY_STEP = 54
SHAKE_DECAY = 18.0              # pixels of shake lost per second
BANNER_TIME = 2.6               # seconds a sector / boss banner stays

# Bug report form (F8 or the pause menu, desktop only): centered frame
BUG_FORM_W, BUG_FORM_H = 640, 236
BUG_BOX_H = 44                 # the one-line text field
BUG_BTN_W, BUG_BTN_H = 180, 36
BUG_NOTICE_TIME = 5.0          # seconds the "report saved" notice stays

# Drag control (mouse held or finger): the ship follows the pointer motion,
# times this gain, capped per frame to this share of its speed. The cap only
# smooths: what it leaves unspent carries over, so a fast flick is not lost.
DRAG_GAIN = 1.25
DRAG_SPEED_CAP = 3.5
