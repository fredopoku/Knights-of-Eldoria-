import math
import random
import pygame
from src.constants import (
    C_SPARK_BRONZE, C_SPARK_SILVER, C_SPARK_GOLD,
    C_DUST, C_CLASH, C_STAR, C_TREASURE_GOLD,
    C_HUNTER_NAV, C_WHITE, C_RED, C_YELLOW, C_ORANGE,
)


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life",
                 "color", "radius", "gravity", "fade", "glow")

    def __init__(self, x, y, vx, vy, life, color,
                 radius=3, gravity=0.0, fade=True, glow=False):
        self.x, self.y     = float(x), float(y)
        self.vx, self.vy   = float(vx), float(vy)
        self.life = self.max_life = float(life)
        self.color   = color
        self.radius  = radius
        self.gravity = gravity
        self.fade    = fade
        self.glow    = glow

    def update(self, dt: float) -> bool:
        self.x   += self.vx * dt
        self.y   += self.vy * dt
        self.vy  += self.gravity * dt
        self.vx  *= 0.985          # slight air resistance
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, offset=(0, 0)):
        if self.life <= 0:
            return
        t  = max(0.0, self.life / self.max_life)
        r  = max(1, int(self.radius * t))
        cx = int(self.x - offset[0])
        cy = int(self.y - offset[1])
        w, h = surface.get_size()
        if not (-r < cx < w + r and -r < cy < h + r):
            return
        col = tuple(max(0, int(c * t)) for c in self.color[:3]) if self.fade else self.color[:3]
        try:
            # Glow particles: draw a soft outer ring before the core
            if self.glow and r >= 2:
                outer_r = r * 2
                glow_col = tuple(max(0, int(c * t * 0.4)) for c in self.color[:3])
                pygame.draw.circle(surface, glow_col, (cx, cy), outer_r)
            pygame.draw.circle(surface, col, (cx, cy), r)
        except Exception:
            pass


class ParticleSystem:
    MAX_PARTICLES = 800

    def __init__(self):
        self._particles: list[Particle] = []
        # Floating score popups
        self._popups: list[dict] = []

    def update(self, dt: float):
        self._particles = [p for p in self._particles if p.update(dt)]
        alive = []
        for p in self._popups:
            p["y"]    -= 55 * dt
            p["life"] -= dt
            if p["life"] > 0:
                alive.append(p)
        self._popups = alive

    def draw(self, surface: pygame.Surface, offset=(0, 0)):
        for p in self._particles:
            p.draw(surface, offset)
        # Score popups
        font = pygame.font.Font(None, 28)
        for p in self._popups:
            t = max(0.0, p["life"] / p["max_life"])
            a = int(255 * t)
            col = tuple(max(0, int(c * t)) for c in p["color"][:3])
            s = font.render(p["text"], True, col)
            sx = int(p["x"] - offset[0]) - s.get_width() // 2
            sy = int(p["y"] - offset[1])
            surface.blit(s, (sx, sy))

    # ------------------------------------------------------------------
    def _emit(self, pts: list[Particle]):
        remaining = self.MAX_PARTICLES - len(self._particles)
        if remaining > 0:
            self._particles.extend(pts[:remaining])

    def add_popup(self, x: int, y: int, text: str, color=C_TREASURE_GOLD):
        self._popups.append({
            "x": x, "y": y, "text": text, "color": color,
            "life": 1.6, "max_life": 1.6,
        })

    # ------------------------------------------------------------------
    # Emitters
    # ------------------------------------------------------------------
    def burst_collect(self, sx: int, sy: int, treasure_type: str):
        colors = {"bronze": C_SPARK_BRONZE, "silver": C_SPARK_SILVER, "gold": C_SPARK_GOLD}
        c = colors.get(treasure_type, C_SPARK_GOLD)
        pts = []
        for _ in range(28):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(45, 140)
            life  = random.uniform(0.5, 1.3)
            pts.append(Particle(sx, sy,
                                math.cos(angle) * speed,
                                math.sin(angle) * speed,
                                life, c,
                                radius=random.randint(3, 7),
                                gravity=50, fade=True, glow=True))
        self._emit(pts)
        # Extra ring of gold sparks
        for _ in range(12):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(20, 55)
            self._emit([Particle(sx, sy,
                                 math.cos(angle) * speed,
                                 math.sin(angle) * speed - 30,
                                 random.uniform(0.4, 0.8),
                                 C_STAR, radius=2, fade=True)])

    def burst_combat(self, sx: int, sy: int):
        pts = []
        for _ in range(30):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(60, 160)
            life  = random.uniform(0.3, 1.0)
            pts.append(Particle(sx, sy,
                                math.cos(angle) * speed,
                                math.sin(angle) * speed,
                                life, C_CLASH,
                                radius=random.randint(3, 7),
                                gravity=80, fade=True, glow=True))
        self._emit(pts)

    def dust(self, sx: int, sy: int, color=None):
        c = color or C_DUST
        pts = []
        for _ in range(6):
            angle = random.uniform(math.pi * 0.7, math.pi * 1.3)
            speed = random.uniform(20, 55)
            life  = random.uniform(0.25, 0.55)
            pts.append(Particle(sx, sy,
                                math.cos(angle) * speed,
                                math.sin(angle) * speed,
                                life, c,
                                radius=random.randint(2, 4), fade=True))
        self._emit(pts)

    def sparkle(self, sx: int, sy: int, color=None):
        c = color or C_STAR
        for _ in range(3):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(8, 28)
            life  = random.uniform(0.5, 1.1)
            self._emit([Particle(
                sx + random.randint(-8, 8),
                sy + random.randint(-8, 8),
                math.cos(angle) * speed,
                math.sin(angle) * speed - 25,
                life, c, radius=random.randint(2, 4), fade=True, glow=True
            )])

    def achievement(self, sx: int, sy: int):
        pts = []
        for _ in range(40):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(50, 200)
            life  = random.uniform(0.8, 2.0)
            pts.append(Particle(sx, sy,
                                math.cos(angle) * speed,
                                math.sin(angle) * speed,
                                life, C_STAR,
                                radius=random.randint(3, 7),
                                gravity=40, fade=True, glow=True))
        self._emit(pts)

    def danger_pulse(self, sx: int, sy: int):
        """Burst of red sparks — knight is close."""
        pts = []
        for _ in range(8):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(15, 40)
            life  = random.uniform(0.3, 0.6)
            pts.append(Particle(sx, sy,
                                math.cos(angle) * speed,
                                math.sin(angle) * speed,
                                life, C_RED,
                                radius=random.randint(2, 4), fade=True))
        self._emit(pts)

    def confetti(self, sx: int, sy: int):
        """Multi-colour burst for victory/achievement."""
        colors = [C_TREASURE_GOLD, C_SPARK_SILVER, C_HUNTER_NAV,
                  C_SPARK_BRONZE, C_STAR, (180, 100, 255)]
        pts = []
        for _ in range(50):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(80, 240)
            life  = random.uniform(1.0, 2.5)
            c = random.choice(colors)
            pts.append(Particle(sx, sy,
                                math.cos(angle) * speed,
                                math.sin(angle) * speed - 60,
                                life, c,
                                radius=random.randint(3, 6),
                                gravity=120, fade=True, glow=False))
        self._emit(pts)
