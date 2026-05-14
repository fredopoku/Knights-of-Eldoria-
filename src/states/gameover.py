"""Dramatic game-over screen."""
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


class GameOverState:
    def __init__(self, game):
        self.game   = game
        self._stats = {}
        self._mode  = ""
        self._diff  = ""
        self._time  = 0.0
        self._particles = ParticleSystem()

        bw, bh = 230, 52
        cx = WINDOW_WIDTH // 2
        self._retry = Button(pygame.Rect(cx-bw-12, 490, bw, bh),
                             "TRY AGAIN", callback=self._do_retry, font_size=22)
        self._menu  = Button(pygame.Rect(cx+12,    490, bw, bh),
                             "MAIN MENU", callback=lambda: self.game.change_state("menu"),
                             font_size=22)

    def _do_retry(self):
        self.game.change_state("play", mode=self._mode, difficulty=self._diff)

    def enter(self, stats=None, mode="", difficulty="", **kw):
        self._stats = stats or {}
        self._mode  = mode
        self._diff  = difficulty
        self._time  = 0.0
        self._particles = ParticleSystem()
        # Red burst on enter
        for _ in range(3):
            self._particles.burst_combat(
                random.randint(100, WINDOW_WIDTH-100),
                random.randint(80, 200))

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

    def draw(self, surface: pygame.Surface):
        surface.fill(C_BG)

        # Dark red vignette
        t = self._time
        va = int(30 + 20 * math.sin(t * 1.2))
        vs = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for r in range(0, 320, 16):
            pygame.draw.rect(vs, (140, 0, 0, max(0, va - r//4)),
                             (r, r, WINDOW_WIDTH-2*r, WINDOW_HEIGHT-2*r), 16)
        surface.blit(vs, (0, 0))

        self._particles.draw(surface)

        cx = WINDOW_WIDTH // 2

        # Pulsing GAME OVER
        pulse = 0.5 + 0.5 * math.sin(t * 2.0)
        a = int(200 + 55 * pulse)
        draw_text(surface, "GAME  OVER", cx, 88,
                  size=82, color=(a, int(a*0.22), int(a*0.22)),
                  bold=True, align="center", shadow=True)
        draw_text(surface, "The hunters have fallen…", cx, 188,
                  size=22, color=C_UI_TEXT_DIM, align="center")

        # Stats panel
        pw, ph = 520, 228
        pr = pygame.Rect(cx-pw//2, 228, pw, ph)
        draw_panel(surface, pr)
        draw_text(surface, "FINAL REPORT", cx, pr.top+14,
                  size=20, color=C_UI_TEXT_BRIGHT, bold=True, align="center")
        draw_hline(surface, pr.left+12, pr.right-12, pr.top+42)

        s = self._stats
        y = pr.top + 54
        for label, val in [
            ("Steps Survived",     str(s.get("step", 0))),
            ("Treasure Collected", f"{s.get('pct', 0):.1f}%"),
            ("Final Score",        f"{s.get('score', 0):,}"),
            ("Hunters Remaining",  str(s.get("hunters", 0))),
            ("Difficulty",         self._diff.title()),
        ]:
            draw_text(surface, label, pr.left+24, y, size=17, color=C_UI_TEXT_DIM)
            draw_text(surface, val,   pr.right-24, y, size=17,
                      color=C_UI_TEXT_BRIGHT, bold=True, align="right")
            y += 30

        self._retry.draw(surface)
        self._menu.draw(surface)

        draw_text(surface, "Press ESC for main menu",
                  cx, 566, size=14, color=C_UI_TEXT_DIM, align="center")
