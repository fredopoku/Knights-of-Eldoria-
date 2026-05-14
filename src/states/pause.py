"""Pause menu — rendered as a translucent overlay over the play state."""
from __future__ import annotations
import pygame
from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    C_UI_TEXT_BRIGHT, C_UI_BORDER_HI, C_UI_PANEL, C_UI_BORDER,
    C_BLACK,
)
from src.ui import Button, draw_text, draw_panel


class PauseState:
    def __init__(self, game):
        self.game    = game
        bw, bh = 240, 48
        cx = WINDOW_WIDTH // 2 - bw // 2
        self._buttons = [
            Button(pygame.Rect(cx, 280, bw, bh), "RESUME",
                   callback=self._resume, font_size=22),
            Button(pygame.Rect(cx, 340, bw, bh), "SETTINGS",
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
        # Capture current screen as frozen background
        s = self.game.screen
        self._bg = s.copy()

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
        for b in self._buttons:
            b.update(dt)

    def draw(self, surface: pygame.Surface):
        if self._bg:
            surface.blit(self._bg, (0, 0))
        # Dark overlay
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        # Panel
        pw, ph = 300, 260
        pr = pygame.Rect((WINDOW_WIDTH - pw)//2, (WINDOW_HEIGHT - ph)//2 - 30,
                         pw, ph)
        draw_panel(surface, pr)

        draw_text(surface, "PAUSED",
                  WINDOW_WIDTH//2, pr.top + 18,
                  size=36, color=C_UI_TEXT_BRIGHT, bold=True,
                  align="center", shadow=True)

        for b in self._buttons:
            b.draw(surface)
