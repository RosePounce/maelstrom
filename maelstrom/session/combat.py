"""Combat: hits, kills, drops and what a container does, the Interceptor."""

import math
import random

from settings.balance import (
    BONUSES, BOSS_ALLOY, BOSS_ALLOY_PER_HEART, BOSS_CONTACT, BOSS_DEATH_TIME,
    BOSS_SHUTDOWN, CAUSTIC_CLOUD, CONTACT_SELF_DAMAGE, ENEMY_SHOT_DAMAGE,
    LEVEL_DAMAGE_SCALE, MALUSES, MISSILE_MAX, MYSTERY_ALLOY_MULT,
    MYSTERY_BONUS, PICKUP_RADIUS, WEAPON_MAX_LEVEL,
    WEAPON_MAXED_ALLOY,
)
from settings.ui import (
    C_ALLOY, C_BONUS, C_HEART, C_MALUS, C_NEON_CYAN, C_NEON_ORANGE,
    C_NEON_PURPLE, C_THARG, C_THARG_SHOT, WIDTH,
)
from maelstrom import i18n
from maelstrom.effects import FloatText, Particle, Ring
from maelstrom.pickups import Pickup, roll_container, weighted
from maelstrom.projectiles import CausticCloud, Shot


def _close(ax, ay, bx, by, reach):
    return (ax - bx) ** 2 + (ay - by) ** 2 < reach * reach


class Combat:

    # --- shots --------------------------------------------------------------

    def enemy_fire(self, x, y, angle, speed):
        dmg = ENEMY_SHOT_DAMAGE * (1 + LEVEL_DAMAGE_SCALE * self.level_index)
        self.enemy_shots.append(Shot(x, y, math.cos(angle) * speed,
                                     math.sin(angle) * speed, dmg, "enemy",
                                     radius=5, life=8.0))

    def fire_missiles(self):
        if self.phase in ("play", "warning", "boss"):
            self.missiles.extend(self.ship.launch_missiles())

    def missile_target(self, missile):
        """The nearest Thargoid (asteroids aside), or the Interceptor."""
        best, best_d = None, 1e12
        for e in self.enemies:
            if e.hp <= 0 or e.kind == "asteroid" or e.x > WIDTH:
                continue
            d = (e.x - missile.x) ** 2 + (e.y - missile.y) ** 2
            if d < best_d:
                best, best_d = (e.x, e.y), d
        if self.boss and self.phase == "boss":
            d = (self.boss.x - missile.x) ** 2 + (self.boss.y - missile.y) ** 2
            if d < best_d:
                best = (self.boss.x, self.boss.y)
        return best

    # --- collisions ---------------------------------------------------------

    def collide(self):
        boss = self.boss if self.phase == "boss" else None
        for s in self.shots + self.missiles:
            if s.dead:
                continue
            pierce = getattr(s, "pierce", False)
            for e in self.enemies:
                if e.hp <= 0 or (pierce and id(e) in s.hits):
                    continue
                if _close(e.x, e.y, s.x, s.y, e.radius + s.radius):
                    self.hit_enemy(e, s.damage, s.x, s.y)
                    if pierce:
                        s.hits.add(id(e))
                    else:
                        s.dead = True
                        break
            if not s.dead and boss and boss.hit_test(s.x, s.y, s.radius):
                if not (pierce and id(boss) in s.hits):
                    self.hit_boss(s.damage, s.x, s.y)
                    if pierce:
                        s.hits.add(id(boss))
                    else:
                        s.dead = True

        ship = self.ship
        if self.phase != "boss_dying":
            for s in self.enemy_shots:
                if _close(s.x, s.y, ship.x, ship.y, ship.hitbox + s.radius):
                    if ship.hit(s.damage):
                        s.dead = True
                        self.on_ship_hit()
            for e in self.enemies:
                if e.hp > 0 and _close(e.x, e.y, ship.x, ship.y, ship.hitbox + e.radius * 0.8):
                    if ship.hit(e.contact):
                        self.on_ship_hit()
                        e.hp -= CONTACT_SELF_DAMAGE
                    if e.kind == "mine":
                        e.hp = 0
            if boss and boss.hit_test(ship.x, ship.y, ship.hitbox):
                if ship.hit(BOSS_CONTACT):
                    self.on_ship_hit()
            for c in self.clouds:
                if _close(c.x, c.y, ship.x, ship.y, c.radius * 0.8):
                    ship.add_effect("caustic", CAUSTIC_CLOUD["stain"], malus=True)
        for p in self.pickups:
            if _close(p.x, p.y, ship.x, ship.y, PICKUP_RADIUS):
                p.taken = True
                self.take_pickup(p)

        for e in self.enemies:
            if e.hp <= 0:
                self.kill(e)
        self.enemies = [e for e in self.enemies if e.hp > 0]

    def on_ship_hit(self):
        self.shake = max(self.shake, 6)
        for _ in range(8):
            self.spark(self.ship.x, self.ship.y, C_NEON_CYAN)

    def hit_enemy(self, e, damage, x, y):
        e.hp -= damage
        e.hit_flash = 1.0
        self.spark(x, y, C_THARG_SHOT)

    def kill(self, e):
        color = C_NEON_PURPLE if e.kind == "asteroid" else C_THARG
        self.explode(e.x, e.y, color, 10 + int(e.radius), 60 + e.radius * 6)
        self.kills += 1
        if e.alloy:
            self.gain_alloys(e.alloy)
        if e.kind == "mine":
            self.clouds.append(CausticCloud(e.x, e.y, self.scroll * 0.5))
        if e.radius >= 18:
            self.shake = max(self.shake, 4)
        if random.random() < e.drop * self.ship.drop_mult:
            self.pickups.append(Pickup(e.x, e.y, *roll_container()))

    # --- effects ------------------------------------------------------------

    def spark(self, x, y, color):
        a = random.uniform(0, math.tau)
        v = random.uniform(40, 160)
        self.particles.append(Particle(x, y, math.cos(a) * v, math.sin(a) * v,
                                       random.uniform(0.15, 0.35), color, 2))

    def explode(self, x, y, color, count, speed=180):
        for _ in range(count):
            a = random.uniform(0, math.tau)
            v = random.uniform(0.2, 1.0) * speed
            self.particles.append(Particle(x, y, math.cos(a) * v, math.sin(a) * v,
                                           random.uniform(0.3, 0.8), color,
                                           random.choice((2, 2, 3))))
        self.rings.append(Ring(x, y, count * 2 + 10, color, 0.45))

    def float_text(self, text, color):
        self.floats.append(FloatText(self.ship.x, self.ship.y - 30, text, color))

    # --- containers ---------------------------------------------------------

    def take_pickup(self, p):
        cat, key = p.cat, p.key
        alloy_mult = 1
        if cat == "mystery":
            alloy_mult = MYSTERY_ALLOY_MULT
            if random.random() < MYSTERY_BONUS:
                cat, key = "bonus", weighted(BONUSES)
            else:
                cat, key = "malus", weighted(MALUSES)
        ship = self.ship
        self.rings.append(Ring(ship.x, ship.y, 40, C_BONUS if cat == "bonus" else C_MALUS, 0.35))

        if cat == "malus":
            m = MALUSES[key]
            ship.add_effect(key, m["time"], malus=True)
            self.float_text(i18n.pickup_name(key), C_MALUS)
            self.shake = max(self.shake, 5)
            return

        if key == "weapon":
            weapon = p.weapon if p.key == "weapon" else ship.weapon
            if weapon == ship.weapon and ship.level >= WEAPON_MAX_LEVEL:
                self.gain_alloys(WEAPON_MAXED_ALLOY)
                self.float_text(i18n.t("combat.weapon_maxed", alloys=WEAPON_MAXED_ALLOY), C_ALLOY)
                return
            if weapon == ship.weapon:
                ship.level += 1
            ship.weapon = weapon
            self.float_text(i18n.t("combat.weapon_up", name=i18n.weapon_name(weapon), level=ship.level),
                            C_NEON_ORANGE)
            return
        b = BONUSES[key]
        if key == "shield":
            ship.shield = ship.shield_max
        elif key == "repair":
            ship.hull = min(ship.hull_max, ship.hull + b["hull"])
            ship.effects.pop("caustic", None)
        elif key == "missiles":
            ship.missiles = min(MISSILE_MAX, ship.missiles + b["count"])
        elif key == "overcharge":
            ship.add_effect("overcharge", b["time"])
        elif key == "alloy":
            amount = b["amount"] * alloy_mult
            self.gain_alloys(amount)
            self.float_text(i18n.t("combat.alloy_gain", amount=amount), C_ALLOY)
            return
        self.float_text(i18n.pickup_name(key), C_BONUS)

    # --- the Interceptor ----------------------------------------------------

    def on_boss_ready(self):
        pass

    def on_boss_exposed(self):
        self.show_banner(i18n.t("banner.boss_exposed"), "", C_HEART, 1.2)

    def hit_boss(self, damage, x, y):
        result = self.boss.damage(damage)
        self.spark(x, y, C_HEART if self.boss.state == "exposed" else C_THARG)
        if result == "heart":
            b = self.boss
            self.rings.append(Ring(b.x, b.y, 900, (190, 220, 255), 1.1, 5))
            self.explode(b.x, b.y, C_HEART, 40, 260)
            self.shake = 12
            self.ship.add_effect("shutdown", BOSS_SHUTDOWN, malus=True)
            self.gain_alloys(BOSS_ALLOY_PER_HEART)
            self.show_banner(i18n.t("banner.heart_down"), "", C_HEART, 1.6)
            for _ in range(2):
                self.pickups.append(Pickup(b.x - b.radius, b.y, "bonus", weighted(BONUSES)))
        elif result == "dead":
            self.phase, self.phase_t = "boss_dying", 0.0
            self.enemy_shots.clear()
            self.gain_alloys(BOSS_ALLOY + BOSS_ALLOY_PER_HEART)
            self.ship.invuln = BOSS_DEATH_TIME + 1

    def update_boss_death(self, dt):
        b = self.boss
        b.t += dt
        b.hit_flash = 1.0
        if random.random() < dt * 14:
            self.explode(b.x + random.uniform(-b.radius, b.radius),
                         b.y + random.uniform(-b.radius, b.radius),
                         random.choice((C_THARG, C_HEART)), 14, 200)
            self.shake = max(self.shake, 7)
        if self.phase_t >= BOSS_DEATH_TIME:
            self.explode(b.x, b.y, C_HEART, 90, 420)
            self.rings.append(Ring(b.x, b.y, 600, C_THARG, 1.2, 6))
            self.shake = 20
            for e in self.enemies:
                e.hp = 0
            self.collide_kills_only()
            self.boss = None
            self.clear_sector()

    def collide_kills_only(self):
        for e in self.enemies:
            if e.hp <= 0:
                self.kill(e)
        self.enemies = []
