"""Dramatic game-over screen with deep red atmosphere."""
from __future__ import annotations
import math
import random
import pygame
from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    C_BG, C_UI_TEXT, C_UI_TEXT_BRIGHT, C_UI_TEXT_DIM,
    C_UI_PANEL, C_UI_BORDER, C_UI_BORDER_HI,
    C_RED, C_YELLOW, C_TREASURE_GOLD,
)
from src.ui import Button, draw_text, draw_panel, draw_hline
from src.particles import ParticleSystem


# ---------------------------------------------------------------------------
# Falling blood-red ember for game-over ambience
# ---------------------------------------------------------------------------
class _RedEmber:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x        = random.uniform(0, WINDOW_WIDTH)
        self.y        = random.uniform(-20, WINDOW_HEIGHT * 0.6)
        self.vx       = random.uniform(-8, 8)
        self.vy       = random.uniform(18, 45)
        self.max_life = random.uniform(3.0, 7.0)
        self.life     = self.max_life
        self.r        = random.randint(1, 3)

    def update(self, dt):
        self.x    += self.vx * dt
        self.y    += self.vy * dt
        self.life -= dt
        if self.life <= 0 or self.y > WINDOW_HEIGHT + 20:
            self.reset()

    def draw(self, surf):
        t   = max(0.0, self.life / self.max_life)
        a   = int(180 * t)
        col = (int(220 * t), int(30 * t), int(30 * t))
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), self.r)


class GameOverState:
    def __init__(self, game):
        self.game       = game
        self._stats     = {}
        self._mode      = ""
        self._diff      = ""
        self._time      = 0.0
        self._particles = ParticleSystem()
        self._embers    = [_RedEmber() for _ in range(30)]

        bw, bh = 234, 54
        cx = WINDOW_WIDTH // 2
        self._retry = Button(pygame.Rect(cx - bw - 14, 494, bw, bh),
                             "TRY AGAIN", callback=self._do_retry, font_size=22)
        self._menu  = Button(pygame.Rect(cx + 14,     494, bw, bh),
                             "MAIN MENU",
                             callback=lambda: self.game.change_state("menu"),
                             font_size=22)

    def _do_retry(self):
        self.game.change_state("play", mode=self._mode, difficulty=self._diff)

    def enter(self, stats=None, mode="", difficulty="", **kw):
        self._stats     = stats or {}
        self._mode      = mode
        self._diff      = difficulty
        self._time      = 0.0
        self._particles = ParticleSystem()
        self._embers    = [_RedEmber() for _ in range(30)]
        # Combat burst on enter
        for _ in range(4):
            self._particles.burst_combat(
                random.randint(100, WINDOW_WIDTH - 100),
                random.randint(80, 220))

    def exit(self): pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.change_state("menu")
        self._retry.handle_event(event)
        self._menu.handle_event(event)

    def update(self, dt):
        self._time += dt
        self._retry.update(dt)
        self._menu.update(dt)
        self._particles.update(dt)
        for e in self._embers:
            e.update(dt)

    def draw(self, surface: pygame.Surface):
        surface.fill(C_BG)

        # Deep red pulsing vignette
        t  = self._time
        va = int(34 + 22 * math.sin(t * 1.2))
        vs = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for r in range(0, 340, 18):
            pygame.draw.rect(vs, (150, 0, 0, max(0, va - r // 5)),
                             (r, r, WINDOW_WIDTH - 2 * r, WINDOW_HEIGHT - 2 * r), 18)
        surface.blit(vs, (0, 0))

        for e in self._embers:
            e.draw(surface)

        self._particles.draw(surface)

        cx = WINDOW_WIDTH // 2

        # Pulsing GAME OVER title
        pulse = 0.5 + 0.5 * math.sin(t * 2.0)
        a     = int(200 + 55 * pulse)

        for off, mult in [(6, 0.12), (4, 0.22), (2, 0.40)]:
            col = (int(a * mult), 0, 0)
            draw_text(surface, "GAME  OVER", cx, 82 + off,
                      size=84, color=col, bold=True, align="center")
        draw_text(surface, "GAME  OVER", cx, 82,
                  size=84, color=(a, int(a * 0.22), int(a * 0.22)),
                  bold=True, align="center", shadow=True)

        draw_text(surface, "The hunters have fallen…",
                  cx, 186, size=22, color=C_UI_TEXT_DIM, align="center")

        # Decorative divider
        pygame.draw.line(surface, C_UI_BORDER, (cx - 220, 220), (cx - 50, 220), 1)
        pygame.draw.line(surface, C_UI_BORDER, (cx + 50, 220), (cx + 220, 220), 1)
        pygame.draw.circle(surface, C_RED, (cx, 220), 6)

        # Stats panel
        pw, ph = 540, 234
        pr = pygame.Rect(cx - pw // 2, 232, pw, ph)
        draw_panel(surface, pr)
        draw_text(surface, "FINAL REPORT", cx, pr.top + 14,
                  size=20, color=C_UI_TEXT_BRIGHT, bold=True, align="center")
        draw_hline(surface, pr.left + 14, pr.right - 14, pr.top + 44)

        s = self._stats
        y = pr.top + 58
        for label, val, col in [
            ("Steps Survived",     str(s.get("step", 0)),         C_UI_TEXT_BRIGHT),
            ("Treasure Collected", f"{s.get('pct', 0):.1f}%",     C_YELLOW),
            ("Final Score",        f"{s.get('score', 0):,}",      C_TREASURE_GOLD),
            ("Hunters Remaining",  str(s.get("hunters", 0)),      C_UI_TEXT_BRIGHT),
            ("Difficulty",         self._diff.title(),             C_RED),
        ]:
            draw_text(surface, label,  pr.left + 26, y, size=17, color=C_UI_TEXT_DIM)
            draw_text(surface, val,    pr.right - 26, y, size=17,
                      color=col, bold=True, align="right")
            y += 32

        self._retry.draw(surface)
        self._menu.draw(surface)

        draw_text(surface, "Press ESC for main menu",
                  cx, 568, size=14, color=C_UI_TEXT_DIM, align="center")
