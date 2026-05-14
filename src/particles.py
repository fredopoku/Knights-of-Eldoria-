import math
import random
import pygame
from src.constants import (
    C_SPARK_BRONZE, C_SPARK_SILVER, C_SPARK_GOLD,
    C_DUST, C_CLASH, C_STAR,
)


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life",
                 "color", "radius", "gravity", "fade")

    def __init__(self, x, y, vx, vy, life, color, radius=3,
                 gravity=0.0, fade=True):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.life = self.max_life = float(life)
        self.color  = color
        self.radius = radius
        self.gravity = gravity
        self.fade   = fade

    def update(self, dt: float) -> bool:
        self.x  += self.vx * dt
        self.y  += self.vy * dt
        self.vy += self.gravity * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, offset=(0, 0)):
        if self.life <= 0:
            return
        alpha = int(255 * (self.life / self.max_life)) if self.fade else 255
        r = max(1, int(self.radius * (self.life / self.max_life)))
        cx = int(self.x - offset[0])
        cy = int(self.y - offset[1])
        if -r < cx < surface.get_width() + r and -r < cy < surface.get_height() + r:
            col = (*self.color[:3], alpha)
            try:
                pygame.draw.circle(surface, col, (cx, cy), r)
            except Exception:
                pass


class ParticleSystem:
    """Manages all active particles in the game."""

    MAX_PARTICLES = 600

    def __init__(self):
        self._particles: list[Particle] = []

    # ------------------------------------------------------------------
    # Update / Draw
    # ------------------------------------------------------------------
    def update(self, dt: float):
        self._particles = [p for p in self._particles if p.update(dt)]

    def draw(self, surface: pygame.Surface, offset=(0, 0)):
        # Blit to a per-frame alpha surface for proper blending
        for p in self._particles:
            p.draw(surface, offset)

    # ------------------------------------------------------------------
    # Emitters
    # ------------------------------------------------------------------
    def _emit(self, particles: list[Particle]):
        remaining = self.MAX_PARTICLES - len(self._particles)
        self._particles.extend(particles[:remaining])

    def burst_collect(self, sx: int, sy: int, treasure_type: str):
        """Sparkles when a hunter picks up treasure."""
        color_map = {
            "bronze": C_SPARK_BRONZE,
            "silver": C_SPARK_SILVER,
            "gold":   C_SPARK_GOLD,
        }
        c = color_map.get(treasure_type, C_SPARK_GOLD)
        pts = []
        for _ in range(18):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(30, 100)
            life  = random.uniform(0.5, 1.2)
            pts.append(Particle(sx, sy,
                                math.cos(angle) * speed,
                                math.sin(angle) * speed,
                                life, c, radius=random.randint(2, 5),
                                gravity=40, fade=True))
        self._emit(pts)

    def burst_combat(self, sx: int, sy: int):
        """Sword-clash effect when knight catches hunter."""
        pts = []
        for _ in range(20):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(50, 130)
            life  = random.uniform(0.3, 0.9)
            pts.append(Particle(sx, sy,
                                math.cos(angle) * speed,
                                math.sin(angle) * speed,
                                life, C_CLASH,
                                radius=random.randint(2, 5),
                                gravity=60, fade=True))
        self._emit(pts)

    def dust(self, sx: int, sy: int):
        """Light dust puff when an entity moves."""
        pts = []
        for _ in range(4):
            angle = random.uniform(math.pi * 0.8, math.pi * 1.2)
            speed = random.uniform(15, 40)
            life  = random.uniform(0.2, 0.5)
            pts.append(Particle(sx, sy,
                                math.cos(angle) * speed,
                                math.sin(angle) * speed,
                                life, C_DUST,
                                radius=random.randint(1, 3),
                                fade=True))
        self._emit(pts)

    def sparkle(self, sx: int, sy: int, color=None):
        """Ambient sparkle (e.g. for treasure on the ground)."""
        c = color or C_STAR
        for _ in range(2):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(5, 20)
            life  = random.uniform(0.4, 0.9)
            self._emit([Particle(
                sx + random.randint(-6, 6),
                sy + random.randint(-6, 6),
                math.cos(angle) * speed,
                math.sin(angle) * speed - 20,
                life, c, radius=random.randint(1, 3), fade=True
            )])

    def achievement(self, sx: int, sy: int):
        """Star burst for achievement unlock."""
        pts = []
        for _ in range(30):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(40, 160)
            life  = random.uniform(0.6, 1.5)
            pts.append(Particle(sx, sy,
                                math.cos(angle) * speed,
                                math.sin(angle) * speed,
                                life, C_STAR,
                                radius=random.randint(2, 6),
                                gravity=30, fade=True))
        self._emit(pts)

    def screen_stars(self, surface: pygame.Surface, dt: float):
        """Ambient drifting stars for menu background — drawn directly."""
        pass  # Handled by MenuState for performance
