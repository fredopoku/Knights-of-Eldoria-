"""Pause menu — beautiful translucent overlay over the frozen play screen."""
from __future__ import annotations
import math
import pygame
from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    C_BG, C_UI_TEXT_BRIGHT, C_UI_TEXT_DIM,
    C_UI_BORDER_HI, C_UI_PANEL, C_UI_BORDER,
    C_TREASURE_GOLD, C_BLACK,
)
from src.ui import Button, draw_text, draw_panel, draw_hline


class PauseState:
    def __init__(self, game):
        self.game    = game
        self._time   = 0.0
        bw, bh = 248, 50
        cx = WINDOW_WIDTH // 2 - bw // 2
        self._buttons = [
            Button(pygame.Rect(cx, 276, bw, bh), "RESUME",
                   callback=self._resume, font_size=22),
            Button(pygame.Rect(cx, 338, bw, bh), "SETTINGS",
                   callback=lambda: self.game.change_state("settings",
                                                           return_to="pause"),
                   font_size=22),
            Button(pygame.Rect(cx, 400, bw, bh), "MAIN MENU",
                   callback=lambda: self.game.change_state("menu"), font_size=22),
        ]
        self._bg: pygame.Surface | None = None

    def _resume(self):
        self.game.change_state("play")

    def enter(self, **kwargs):
        self._time = 0.0
        # Capture current screen as frozen background
        try:
            s = pygame.display.get_surface()
            self._bg = s.copy() if s else None
        except Exception:
            self._bg = None

    def exit(self):
        pass

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._resume()
            return
        for b in self._buttons:
            if b.handle_event(event):
                self.game.audio.play("ui_click")
                break

    def update(self, dt: float):
        self._time += dt
        for b in self._buttons:
            b.update(dt)

    def draw(self, surface: pygame.Surface):
        if self._bg:
            surface.blit(self._bg, (0, 0))

        # Dark overlay
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 168))
        surface.blit(overlay, (0, 0))

        # Animated panel glow
        t    = self._time
        glow = 0.5 + 0.5 * math.sin(t * 2.0)

        # Panel
        pw, ph = 310, 278
        pr = pygame.Rect((WINDOW_WIDTH - pw) // 2, (WINDOW_HEIGHT - ph) // 2 - 30,
                         pw, ph)
        draw_panel(surface, pr)

        # Decorative top gem
        gem_y = pr.top + 26
        pygame.draw.circle(surface, C_TREASURE_GOLD, (WINDOW_WIDTH // 2, gem_y), 8)
        pygame.draw.circle(surface, C_UI_BORDER_HI,  (WINDOW_WIDTH // 2, gem_y), 8, 1)

        draw_text(surface, "PAUSED",
                  WINDOW_WIDTH // 2, pr.top + 14,
                  size=36, color=C_UI_TEXT_BRIGHT, bold=True,
                  align="center", shadow=True)

        draw_hline(surface, pr.left + 12, pr.right - 12, pr.top + 50)

        for b in self._buttons:
            b.draw(surface)

        draw_text(surface, "Press ESC to resume",
                  WINDOW_WIDTH // 2, pr.bottom - 20,
                  size=13, color=C_UI_TEXT_DIM, align="center")
