"""Scrolling credits screen."""
from __future__ import annotations
import pygame
from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, VERSION,
    C_BG, C_UI_TEXT, C_UI_TEXT_BRIGHT, C_UI_TEXT_DIM, C_UI_ACCENT,
    C_TREASURE_GOLD,
)
from src.ui import Button, draw_text


CREDIT_LINES = [
    ("KNIGHTS OF ELDORIA", 40, C_TREASURE_GOLD, True),
    (f"Version {VERSION}", 18, C_UI_TEXT_DIM, False),
    ("", 20, C_UI_TEXT, False),
    ("DEVELOPMENT", 28, C_UI_TEXT_BRIGHT, True),
    ("Frederick Opoku Afriyie", 22, C_UI_TEXT, False),
    ("", 14, C_UI_TEXT, False),
    ("GAME DESIGN", 28, C_UI_TEXT_BRIGHT, True),
    ("Frederick Opoku Afriyie", 22, C_UI_TEXT, False),
    ("", 14, C_UI_TEXT, False),
    ("ART & ASSETS", 28, C_UI_TEXT_BRIGHT, True),
    ("Sprites & Sound effects (original assets)", 20, C_UI_TEXT_DIM, False),
    ("", 14, C_UI_TEXT, False),
    ("AI & PATHFINDING", 28, C_UI_TEXT_BRIGHT, True),
    ("A* Search Algorithm", 20, C_UI_TEXT, False),
    ("State-Machine Hunter & Knight Behaviour", 20, C_UI_TEXT, False),
    ("Q-Learning (Reinforcement Learning module)", 20, C_UI_TEXT, False),
    ("", 14, C_UI_TEXT, False),
    ("BUILT WITH", 28, C_UI_TEXT_BRIGHT, True),
    ("Python 3.12", 20, C_UI_TEXT, False),
    ("Pygame 2.6", 20, C_UI_TEXT, False),
    ("Pillow", 20, C_UI_TEXT, False),
    ("", 14, C_UI_TEXT, False),
    ("SPECIAL THANKS", 28, C_UI_TEXT_BRIGHT, True),
    ("St Mary's University", 20, C_UI_TEXT_DIM, False),
    ("The Pygame Community", 20, C_UI_TEXT_DIM, False),
    ("", 20, C_UI_TEXT, False),
    ("Thank you for playing!", 30, C_UI_ACCENT, True),
    ("", 60, C_UI_TEXT, False),
]


class CreditsState:
    SCROLL_SPEED = 50.0   # pixels / second

    def __init__(self, game):
        self.game   = game
        self._y     = float(WINDOW_HEIGHT)
        self._back  = Button(pygame.Rect(20, 20, 120, 38), "← BACK",
                             callback=lambda: self.game.change_state("menu"),
                             font_size=16)
        self._total_h = sum(size + 6 for _, size, _, _ in CREDIT_LINES)

    def enter(self, **kwargs):
        self._y = float(WINDOW_HEIGHT)

    def exit(self):
        pass

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.change_state("menu")
        self._back.handle_event(event)
        if event.type == pygame.MOUSEWHEEL:
            self._y -= event.y * 30

    def update(self, dt: float):
        self._y -= self.SCROLL_SPEED * dt
        if self._y < -self._total_h:
            self._y = float(WINDOW_HEIGHT)
        self._back.update(dt)

    def draw(self, surface: pygame.Surface):
        surface.fill(C_BG)
        y = int(self._y)
        for text, size, color, bold in CREDIT_LINES:
            if -size < y < WINDOW_HEIGHT + size:
                draw_text(surface, text, WINDOW_WIDTH//2, y,
                          size=size, color=color, bold=bold,
                          align="center", shadow=bold)
            y += size + 6
        self._back.draw(surface)
