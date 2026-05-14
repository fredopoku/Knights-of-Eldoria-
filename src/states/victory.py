"""Celebration victory screen with confetti and glow."""
from __future__ import annotations
import math
import random
import pygame
from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    C_BG, C_UI_TEXT, C_UI_TEXT_BRIGHT, C_UI_TEXT_DIM,
    C_UI_PANEL, C_UI_BORDER, C_UI_BORDER_HI,
    C_GREEN, C_YELLOW, C_TREASURE_GOLD, C_STAR,
)
from src.ui import Button, draw_text, draw_panel, draw_hline
from src.particles import ParticleSystem


class VictoryState:
    def __init__(self, game):
        self.game   = game
        self._stats = {}
        self._mode  = ""
        self._diff  = ""
        self._time  = 0.0
        self._particles = ParticleSystem()

        bw, bh = 230, 52
        cx = WINDOW_WIDTH // 2
        self._again = Button(pygame.Rect(cx-bw-12, 498, bw, bh),
                             "PLAY AGAIN", callback=self._do_again, font_size=22)
        self._menu  = Button(pygame.Rect(cx+12,    498, bw, bh),
                             "MAIN MENU", callback=lambda: self.game.change_state("menu"),
                             font_size=22)

    def _do_again(self):
        self.game.change_state("play", mode=self._mode, difficulty=self._diff)

    def enter(self, stats=None, mode="", difficulty="", **kw):
        self._stats = stats or {}
        self._mode  = mode
        self._diff  = difficulty
        self._time  = 0.0
        self._particles = ParticleSystem()
        # Opening confetti burst
        for _ in range(6):
            self._particles.confetti(
                random.randint(100, WINDOW_WIDTH-100), 80)
        # Save score
        self.game.saves.save(
            slot=0, mode=mode, difficulty=difficulty,
            step=stats.get("step", 0) if stats else 0,
            score=stats.get("score", 0) if stats else 0,
            pct=stats.get("pct", 0) if stats else 0,
        )
        self.game.achievements.unlock("saved_game")
        if difficulty == "hard":       self.game.achievements.unlock("hard_complete")
        if difficulty == "legendary":  self.game.achievements.unlock("legendary_run")
        self.game.audio.play("victory")

    def exit(self): pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.change_state("menu")
        self._again.handle_event(event)
        self._menu.handle_event(event)

    def update(self, dt):
        self._time += dt
        self._again.update(dt)
        self._menu.update(dt)
        self._particles.update(dt)

        # Continuous confetti bursts
        if random.random() < 0.12:
            self._particles.confetti(
                random.choice([80, WINDOW_WIDTH//2, WINDOW_WIDTH-80]),
                random.randint(40, 120))

        # Ambient sparkles
        if random.random() < 0.25:
            self._particles.sparkle(
                random.randint(50, WINDOW_WIDTH-50),
                random.randint(50, WINDOW_HEIGHT-50),
                C_STAR)

    def draw(self, surface: pygame.Surface):
        surface.fill(C_BG)

        t = self._time

        # Gold vignette glow
        va = int(20 + 15 * math.sin(t * 1.4))
        vs = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for r in range(0, 300, 16):
            pygame.draw.rect(vs, (180, 130, 0, max(0, va - r//5)),
                             (r, r, WINDOW_WIDTH-2*r, WINDOW_HEIGHT-2*r), 16)
        surface.blit(vs, (0, 0))

        self._particles.draw(surface)

        cx = WINDOW_WIDTH // 2

        # Animated gold VICTORY title
        glow  = 0.5 + 0.5 * math.sin(t * 2.2)
        alpha = int(195 + 60 * glow)
        gold  = (alpha, int(alpha*0.82), int(alpha*0.12))

        for off, mult in [(5, 0.15), (3, 0.28), (1, 0.45)]:
            corona = (int(alpha*mult*0.9), int(alpha*0.6*mult), 0)
            draw_text(surface, "VICTORY!", cx, 80+off,
                      size=86, color=corona, bold=True, align="center")
        draw_text(surface, "VICTORY!", cx, 80,
                  size=86, color=gold, bold=True, align="center", shadow=True)

        draw_text(surface, "The hunters have triumphed!", cx, 182,
                  size=24, color=C_UI_TEXT_DIM, align="center")

        # Stats panel
        pw, ph = 540, 240
        pr = pygame.Rect(cx-pw//2, 218, pw, ph)
        draw_panel(surface, pr)
        draw_text(surface, "MISSION COMPLETE", cx, pr.top+14,
                  size=20, color=C_UI_TEXT_BRIGHT, bold=True, align="center")
        # Gold gem decoration
        pygame.draw.circle(surface, C_TREASURE_GOLD, (pr.left+30, pr.top+25), 8)
        pygame.draw.circle(surface, C_TREASURE_GOLD, (pr.right-30, pr.top+25), 8)
        draw_hline(surface, pr.left+12, pr.right-12, pr.top+44)

        s = self._stats
        y = pr.top + 56
        for label, val, col in [
            ("Steps Taken",        str(s.get("step", 0)),        C_UI_TEXT_BRIGHT),
            ("Treasure Collected", f"{s.get('pct', 0):.1f}%",    C_GREEN),
            ("Final Score",        f"{s.get('score', 0):,}",     C_TREASURE_GOLD),
            ("Mode",               self._mode.title(),            C_UI_TEXT),
            ("Difficulty",         self._diff.title(),            C_YELLOW),
        ]:
            draw_text(surface, label, pr.left+24, y, size=17, color=C_UI_TEXT_DIM)
            draw_text(surface, val,   pr.right-24, y, size=17, color=col,
                      bold=True, align="right")
            y += 30

        self._again.draw(surface)
        self._menu.draw(surface)

        draw_text(surface, "Press ESC for main menu",
                  cx, 580, size=14, color=C_UI_TEXT_DIM, align="center")
