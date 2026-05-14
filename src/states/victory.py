"""Victory screen — shown when hunters collect ≥ 50% of treasure."""
from __future__ import annotations
import math
import random
import pygame
from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, VERSION,
    C_BG, C_UI_TEXT, C_UI_TEXT_BRIGHT, C_UI_TEXT_DIM,
    C_UI_PANEL, C_UI_BORDER,
    C_GREEN, C_YELLOW, C_TREASURE_GOLD, C_STAR,
)
from src.ui import Button, draw_text, draw_panel, draw_hline
from src.particles import ParticleSystem


class VictoryState:
    def __init__(self, game):
        self.game       = game
        self._stats     = {}
        self._mode      = ""
        self._diff      = ""
        self._time      = 0.0
        self._particles = ParticleSystem()

        bw, bh = 220, 48
        cx = WINDOW_WIDTH // 2
        self._play_again = Button(
            pygame.Rect(cx - bw - 10, 490, bw, bh), "PLAY AGAIN",
            callback=self._again, font_size=22)
        self._menu_btn = Button(
            pygame.Rect(cx + 10, 490, bw, bh), "MAIN MENU",
            callback=lambda: self.game.change_state("menu"), font_size=22)

    def _again(self):
        self.game.change_state("play", mode=self._mode, difficulty=self._diff)

    def enter(self, stats: dict = None, mode: str = "",
              difficulty: str = "", **kwargs):
        self._stats = stats or {}
        self._mode  = mode
        self._diff  = difficulty
        self._time  = 0.0
        self._particles = ParticleSystem()

        # Save score
        self.game.saves.save(
            slot=0,
            mode=mode,
            difficulty=difficulty,
            step=stats.get("step", 0) if stats else 0,
            score=stats.get("score", 0) if stats else 0,
            pct=stats.get("pct", 0) if stats else 0,
        )
        self.game.achievements.unlock("saved_game")

        # Difficulty achievements
        if difficulty == "hard":
            self.game.achievements.unlock("hard_complete")
        elif difficulty == "legendary":
            self.game.achievements.unlock("legendary_run")

        self.game.audio.play("victory")

    def exit(self):
        pass

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.change_state("menu")
        self._play_again.handle_event(event)
        self._menu_btn.handle_event(event)

    def update(self, dt: float):
        self._time += dt
        self._play_again.update(dt)
        self._menu_btn.update(dt)
        self._particles.update(dt)

        # Periodic bursts from top corners
        if random.random() < 0.15:
            x = random.choice([80, WINDOW_WIDTH - 80])
            self._particles.achievement(x, 80)

    def draw(self, surface: pygame.Surface):
        surface.fill(C_BG)
        cx = WINDOW_WIDTH // 2

        # Animated gold title
        glow = 0.5 + 0.5 * math.sin(self._time * 2.5)
        alpha = int(200 + 55 * glow)
        draw_text(surface, "VICTORY!", cx, 80,
                  size=80, color=(alpha, int(alpha*0.85), 30),
                  bold=True, align="center", shadow=True)
        draw_text(surface, "The hunters have triumphed!", cx, 172,
                  size=24, color=C_UI_TEXT_DIM, align="center")

        # Stats panel
        pw, ph = 520, 230
        pr = pygame.Rect(cx - pw//2, 215, pw, ph)
        draw_panel(surface, pr)
        draw_text(surface, "MISSION COMPLETE", cx, pr.top + 14,
                  size=20, color=C_UI_TEXT_BRIGHT, bold=True, align="center")
        draw_hline(surface, pr.left + 12, pr.right - 12, pr.top + 40)

        s = self._stats
        rows = [
            ("Steps Taken",         str(s.get("step", 0))),
            ("Treasure Collected",  f"{s.get('pct', 0):.1f}%"),
            ("Final Score",         f"{s.get('score', 0):,}"),
            ("Mode",                self._mode.title()),
            ("Difficulty",          self._diff.title()),
        ]
        y = pr.top + 52
        for label, val in rows:
            draw_text(surface, label, pr.left + 24, y,
                      size=17, color=C_UI_TEXT_DIM)
            draw_text(surface, val, pr.right - 24, y,
                      size=17, color=C_UI_TEXT_BRIGHT, bold=True, align="right")
            y += 30

        self._play_again.draw(surface)
        self._menu_btn.draw(surface)

        self._particles.draw(surface)

        draw_text(surface, "Press ESC for main menu",
                  cx, 570, size=14, color=C_UI_TEXT_DIM, align="center")
