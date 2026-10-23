"""Balance: the game's numbers, with none of its code.

Ship, primary weapons, AX missiles, bonuses and maluses picked up in flight,
permanent hangar upgrades (paid in meta-alloy), Thargoid ships, Interceptors
(the bosses) and the four sectors. Speeds are in logical pixels per second,
times in seconds.
"""


# ----------------------------------------------------------------------
#  Ship
# ----------------------------------------------------------------------

SHIP_SPEED = 300.0
SHIP_HULL = 100
SHIP_SHIELD = 60
SHIELD_REGEN = 8.0             # points per second while recharging
SHIELD_DELAY = 3.0             # seconds without a hit before it recharges
HIT_INVULN = 0.6               # seconds of grace after a hit
SPAWN_INVULN = 1.5             # ... and at the start of an attempt
SHIP_HITBOX = 7                # small on purpose: the shot-dodging genre
PICKUP_RADIUS = 24             # contact radius for a pickup
MAGNET_RADIUS = 70             # bonuses within it drift to the ship
MAGNET_PULL = 360


# Starting ships (Elite Dangerous hulls). Each is a multiplier on the base
# stats above, a starting weapon, and -- for the big slow hulls -- a wider
# hitbox (harder to dodge). The silhouettes are drawn in `player.py`
# (`SHIP_SHAPES`), their names/descriptions in the locales.
SHIPS = {
    "krait":     {"hull": 1.0,  "shield": 1.0,  "speed": 1.05, "damage": 1.10,
                  "rate": 1.05, "hitbox": 1.0,  "weapon": "pulse"},
    "chieftain": {"hull": 1.35, "shield": 0.85, "speed": 1.15, "damage": 0.95,
                  "rate": 1.0,  "hitbox": 1.0,  "weapon": "pulse"},
    "type10":    {"hull": 1.8,  "shield": 1.30, "speed": 0.78, "damage": 1.20,
                  "rate": 0.95, "hitbox": 1.45, "weapon": "rail"},
    "mamba":     {"hull": 0.7,  "shield": 0.70, "speed": 1.30, "damage": 1.35,
                  "rate": 1.10, "hitbox": 0.85, "weapon": "rail"},
}
SHIP_ORDER = ("krait", "chieftain", "type10", "mamba")
DEFAULT_SHIP = "krait"


# ----------------------------------------------------------------------
#  Primary weapons (automatic fire)
# ----------------------------------------------------------------------

# A weapon module picked up raises the level of the weapon in hand, or swaps
# it for another, keeping the level. Per level (1 to WEAPON_MAX_LEVEL):
#   pulse  `levels`: the barrels, as (y offset, angle in degrees);
#   frag   `pellets` and `spread` (total cone, degrees) of a shell;
#   rail   `levels`: y offsets of the rails, `mult`: damage multiplier.
# The rails go through everything they meet.
WEAPON_MAX_LEVEL = 5
WEAPONS = {
    "pulse": {
        "damage": 7, "rate": 7.5, "speed": 950,
        "levels": (
            ((0, 0),),
            ((-6, 0), (6, 0)),
            ((-6, 0), (6, 0), (0, -7), (0, 7)),
            ((-8, 0), (0, 0), (8, 0), (0, -9), (0, 9)),
            ((-8, 0), (0, 0), (8, 0), (0, -7), (0, 7), (0, -15), (0, 15)),
        ),
    },
    "frag": {
        "damage": 6, "rate": 2.6, "speed": 760, "life": 0.55,
        "pellets": (5, 6, 8, 9, 11), "spread": (22, 26, 30, 34, 40),
    },
    "rail": {
        "damage": 34, "rate": 1.6, "speed": 1900,
        "levels": ((0,), (-7, 7), (-7, 7), (-10, 0, 10), (-12, -4, 4, 12)),
        "mult": (1.0, 1.0, 1.35, 1.35, 1.6),
    },
}
WEAPON_ORDER = ("pulse", "frag", "rail")
CAPSULE_CYCLE = 1.6            # a weapon capsule shows each weapon this long


# ----------------------------------------------------------------------
#  AX missiles (Space)
# ----------------------------------------------------------------------

# One stock fires a pair of homing missiles.
MISSILE_START = 3
MISSILE_MAX = 9
MISSILE_DAMAGE = 45
MISSILE_SPEED = 520
MISSILE_TURN = 5.0             # radians per second
MISSILE_COOLDOWN = 0.45
MISSILE_LIFE = 3.0


# ----------------------------------------------------------------------
#  Pickups: bonuses, maluses, unknown containers
# ----------------------------------------------------------------------

# A destroyed ship may drop a container (chance `drop` of its kind, see
# ENEMIES). Its category follows DROP_SPLIT, then its content the weights.
DROP_SPLIT = {"bonus": 0.55, "malus": 0.27, "mystery": 0.18}

BONUSES = {
    "weapon":     {"weight": 24},
    "shield":     {"weight": 15},
    "repair":     {"weight": 14, "hull": 30},     # also cleans the caustic
    "missiles":   {"weight": 15, "count": 2},
    "overcharge": {"weight": 14, "time": 8.0, "rate": 1.7},
    "alloy":      {"weight": 18, "amount": 5},
}
MALUSES = {
    "caustic":  {"weight": 30, "time": 6.0, "dps": 4.0},    # hull, shield or not
    "shutdown": {"weight": 20, "time": 2.5, "slow": 0.5},   # no fire, no regen
    "overheat": {"weight": 25, "time": 6.0, "rate": 0.5},
    "jamming":  {"weight": 25, "time": 5.0, "slow": 0.6},
}
MYSTERY_BONUS = 0.6            # an unknown container hides a bonus this often...
MYSTERY_ALLOY_MULT = 3         # ... and its meta-alloy is worth triple
WEAPON_MAXED_ALLOY = 4         # a weapon module beyond the max level
PICKUP_DRIFT = 70              # pickups drift left at this speed
PICKUP_LIFE = 14.0


# ----------------------------------------------------------------------
#  Hangar: permanent upgrades, paid in meta-alloy
# ----------------------------------------------------------------------

# `step` is the gain per level: points (hull, shield), a share (regen,
# damage, rate, dampers, salvage), missiles at start, or pixels (magnet).
HANGAR = {
    "hull":     {"max": 5, "cost": 15, "step": 20},
    "shield":   {"max": 5, "cost": 15, "step": 15},
    "regen":    {"max": 4, "cost": 20, "step": 0.25},
    "damage":   {"max": 5, "cost": 25, "step": 0.10},
    "rate":     {"max": 5, "cost": 25, "step": 0.08},
    "missiles": {"max": 3, "cost": 20, "step": 1},
    "magnet":   {"max": 3, "cost": 12, "step": 45},
    "dampers":  {"max": 3, "cost": 18, "step": 0.18},
    "salvage":  {"max": 4, "cost": 18, "step": 0.15},
}
HANGAR_GROWTH = 1.7


def hangar_cost(key, level):
    """Price of the next level of an upgrade at `level`."""
    return int(round(HANGAR[key]["cost"] * HANGAR_GROWTH ** level))


# ----------------------------------------------------------------------
#  Thargoids
# ----------------------------------------------------------------------

# hp, collision radius, speed, contact damage, meta-alloy, drop chance;
# `fire` = seconds between two shots, `shot_speed` of those shots.
ENEMIES = {
    "swarm":     {"hp": 5, "radius": 9, "speed": 250, "contact": 14,
                  "alloy": 1, "drop": 0.05},
    "scout":     {"hp": 16, "radius": 14, "speed": 140, "contact": 18,
                  "alloy": 2, "drop": 0.22, "fire": 1.25, "shot_speed": 300},
    "marauder":  {"hp": 26, "radius": 16, "speed": 170, "dash": 680,
                  "contact": 26, "alloy": 3, "drop": 0.30},
    "berserker": {"hp": 70, "radius": 21, "speed": 120, "contact": 30,
                  "alloy": 6, "drop": 0.65, "fire": 0.95, "shot_speed": 285,
                  "stay": 11.0},
    "mine":      {"hp": 10, "radius": 12, "speed": 0, "contact": 20,
                  "alloy": 1, "drop": 0.0},
    "asteroid":  {"hp": 40, "radius": 26, "speed": 0, "contact": 25,
                  "alloy": 0, "drop": 0.12},
}
ENEMY_SHOT_DAMAGE = 18
LEVEL_HP_SCALE = 0.20          # enemy hp +20 % per sector
LEVEL_DAMAGE_SCALE = 0.18      # enemy damage +18 % per sector
CONTACT_SELF_DAMAGE = 30       # what a ship that rams the player takes
# A caustic mine bursts into a cloud: it stains the hull while inside it
CAUSTIC_CLOUD = {"radius": 62, "time": 3.2, "stain": 1.5}


# ----------------------------------------------------------------------
#  Interceptors (one boss per sector)
# ----------------------------------------------------------------------

# An Interceptor alternates an ARMORED phase (petals closed, takes `armor`
# of the damage) and an EXPOSED phase (heart open, full damage). Each heart
# destroyed sets off a shutdown wave and a stagger. Patterns, in turn:
#   aimed   a fan of shots at the ship;     radial  a ring of shots;
#   spiral  a rotating stream;              swarm   it releases Thargons;
#   mines   it drops caustic mines.
# The Titan (the campaign finale, boss of the hidden last sector) is a far
# larger colossus: its `hearts` are the red PODS struck one by one, and it
# adds three patterns of its own: `sweep` (a wall of fire whipped across the
# player's side by its tentacles), `caustic` (a spit of caustic mines) and
# `beam` (a telegraphed DEATH RAY that scythes across the screen). It also
# does not die at once: `forms` is how many times it rises -- each time all
# its pods are destroyed it comes back, recoloured (see BOSS_LOOKS), with its
# pods' health times `form_hp` and its attacks `form_period` as fast. Only the
# last form's death wins the fight.
BOSSES = {
    "cyclops":  {"hearts": 2, "heart_hp": 650, "radius": 56, "period": 1.3,
                 "patterns": ("aimed", "radial", "aimed", "swarm")},
    "basilisk": {"hearts": 3, "heart_hp": 950, "radius": 60, "period": 1.15,
                 "patterns": ("aimed", "radial", "swarm", "spiral")},
    "medusa":   {"hearts": 4, "heart_hp": 1350, "radius": 64, "period": 1.0,
                 "patterns": ("radial", "spiral", "mines", "aimed", "swarm")},
    "hydra":    {"hearts": 5, "heart_hp": 1650, "radius": 70, "period": 0.92,
                 "patterns": ("spiral", "aimed", "radial", "swarm", "mines",
                              "spiral")},
    "titan":    {"hearts": 6, "heart_hp": 1100, "radius": 118, "period": 0.9,
                 "forms": 2, "form_hp": 1.3, "form_period": 0.82,
                 "patterns": ("sweep", "beam", "radial", "caustic", "aimed",
                              "spiral", "sweep", "beam", "swarm")},
}
BOSS_ARMORED_TIME = 5.0
BOSS_EXPOSED_TIME = 6.0        # a shorter opening: the player must make it count
BOSS_ARMOR = 0.09             # less chip damage gets through the closed petals
BOSS_STAGGER = 2.2
BOSS_CONTACT = 46
BOSS_SHOT_SPEED = 260
BOSS_ALLOY_PER_HEART = 8
BOSS_ALLOY = 30
BOSS_SHUTDOWN = 2.0            # shutdown wave of a destroyed heart (dampers apply)
BOSS_WARNING = 3.2             # "Interceptor approaching" before it shows
BOSS_DEATH_TIME = 2.4          # explosions before the "sector cleared" screen
BOSS_BEAM_DAMAGE = 42          # a hit of the Titan's death ray (respects i-frames)


# ----------------------------------------------------------------------
#  Sectors
# ----------------------------------------------------------------------

# Each sector scrolls `duration` seconds before its Interceptor. Its waves
# are drawn from `patterns` (weights) by a random generator SEEDED with
# `seed`: the same sector always plays the same, which is what lets a
# die-and-retry be learned. `gap` = seconds between two waves at the start,
# shrinking by GAP_RAMP towards the end.
# The last sector is the `finale`: the Titan. It is NOT shown in the sector
# picker -- it is reached straight after the Maelstrom is cleared (the "next"
# that follows the Hydra), and only clearing it wins the campaign.
LEVELS = (
    {"key": "merope", "duration": 75, "boss": "cyclops", "scroll": 140,
     "gap": 2.0, "seed": 11,
     "patterns": {"swarm_line": 4, "swarm_wave": 3, "scout_pair": 3,
                  "asteroids": 4, "marauder": 1}},
    {"key": "oracle", "duration": 85, "boss": "basilisk", "scroll": 160,
     "gap": 1.75, "seed": 23,
     "patterns": {"swarm_wave": 3, "swarm_line": 2, "scout_pair": 3,
                  "scout_trio": 2, "marauder": 3, "mines": 2, "asteroids": 2}},
    {"key": "pleiades", "duration": 95, "boss": "medusa", "scroll": 180,
     "gap": 1.55, "seed": 37,
     "patterns": {"swarm_v": 3, "swarm_wave": 2, "scout_trio": 3,
                  "marauder": 3, "berserker": 2, "mines": 3}},
    {"key": "maelstrom", "duration": 105, "boss": "hydra", "scroll": 200,
     "gap": 1.45, "seed": 41,
     "patterns": {"swarm_v": 3, "swarm_wave": 2, "scout_trio": 3,
                  "marauder": 3, "berserker": 3, "mines": 2, "asteroids": 1}},
    {"key": "titan", "duration": 35, "boss": "titan", "scroll": 210,
     "gap": 1.7, "seed": 53, "finale": True,
     "patterns": {"scout_trio": 2, "marauder": 3, "berserker": 2,
                  "swarm_v": 2, "mines": 2}},
)
GAP_RAMP = 0.35
BOSS_CLEAR_WAIT = 5.0          # max wait for the last ships before the boss


# ----------------------------------------------------------------------
#  Two-player co-op (LAN)
# ----------------------------------------------------------------------

COOP_RESPAWN = 6.0             # seconds a downed ship waits before it returns
COOP_REVIVE_HULL = 0.5         # part of its hull it returns with
