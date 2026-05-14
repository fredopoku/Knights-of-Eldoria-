"""Game-over screen — shown when hunters fail or time runs out."""
from __future__ import annotations
import pygame
from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    C_BG, C_UI_TEXT, C_UI_TEXT_BRIGHT, C_UI_TEXT_DIM,
    C_UI_PANEL, C_UI_BORDER,
    C_RED, C_YELLOW,
)
from src.ui import Button, draw_text, draw_panel, draw_hline


class GameOverState:
    def __init__(self, game):
        self.game   = game
        self._stats = {}
        self._mode  = ""
        self._diff  = ""

        bw, bh = 220, 48
        cx = WINDOW_WIDTH // 2
        self._retry_btn = Button(
            pygame.Rect(cx - bw - 10, 480, bw, bh), "TRY AGAIN",
            callback=self._retry, font_size=22)
        self._menu_btn = Button(
            pygame.Rect(cx + 10, 480, bw, bh), "MAIN MENU",
            callback=lambda: self.game.change_state("menu"), font_size=22)

    def _retry(self):
        self.game.change_state("play", mode=self._mode, difficulty=self._diff)

    def enter(self, stats: dict = None, mode: str = "",
              difficulty: str = "", **kwargs):
        self._stats = stats or {}
        self._mode  = mode
        self._diff  = difficulty

    def exit(self):
        pass

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.change_state("menu")
        self._retry_btn.handle_event(event)
        self._menu_btn.handle_event(event)

    def update(self, dt: float):
        self._retry_btn.update(dt)
        self._menu_btn.update(dt)

    def draw(self, surface: pygame.Surface):
        surface.fill(C_BG)
        cx = WINDOW_WIDTH // 2

        draw_text(surface, "GAME OVER", cx, 100,
                  size=72, color=C_RED, bold=True,
                  align="center", shadow=True)
        draw_text(surface, "The hunters have fallen…", cx, 188,
                  size=22, color=C_UI_TEXT_DIM, align="center")

        # Stats panel
        pw, ph = 500, 220
        pr = pygame.Rect(cx - pw//2, 230, pw, ph)
        draw_panel(surface, pr)
        draw_text(surface, "FINAL STATS", cx, pr.top + 14,
                  size=20, color=C_UI_TEXT_BRIGHT, bold=True, align="center")
        draw_hline(surface, pr.left + 12, pr.right - 12, pr.top + 40)

        s = self._stats
        rows = [
            ("Steps Survived",   str(s.get("step",  0))),
            ("Treasure Collected", f"{s.get('pct', 0):.1f}%"),
            ("Final Score",      f"{s.get('score', 0):,}"),
            ("Hunters Active",   str(s.get("hunters", 0))),
            ("Difficulty",       self._diff.title()),
        ]
        y = pr.top + 52
        for label, val in rows:
            draw_text(surface, label, pr.left + 24, y, size=17, color=C_UI_TEXT_DIM)
            draw_text(surface, val,   pr.right - 24, y, size=17,
                      color=C_UI_TEXT_BRIGHT, bold=True, align="right")
            y += 28

        self._retry_btn.draw(surface)
        self._menu_btn.draw(surface)

        draw_text(surface, "Press ESC for main menu",
                  cx, 560, size=14, color=C_UI_TEXT_DIM, align="center")
