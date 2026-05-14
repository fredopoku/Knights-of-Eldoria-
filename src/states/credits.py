"""Scrolling credits screen with atmospheric star background."""
from __future__ import annotations
import math
import random
import pygame
from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, VERSION,
    C_BG, C_UI_TEXT, C_UI_TEXT_BRIGHT, C_UI_TEXT_DIM, C_UI_ACCENT,
    C_UI_BORDER, C_UI_BORDER_HI,
    C_TREASURE_GOLD, C_GREEN, C_YELLOW,
)
from src.ui import Button, draw_text


CREDIT_LINES = [
    ("KNIGHTS OF ELDORIA", 44, C_TREASURE_GOLD, True),
    (f"Version {VERSION}", 18, C_UI_TEXT_DIM, False),
    ("", 20, C_UI_TEXT, False),
    ("DEVELOPMENT", 30, C_UI_TEXT_BRIGHT, True),
    ("Frederick Opoku Afriyie", 24, C_UI_TEXT, False),
    ("", 14, C_UI_TEXT, False),
    ("GAME DESIGN", 30, C_UI_TEXT_BRIGHT, True),
    ("Frederick Opoku Afriyie", 24, C_UI_TEXT, False),
    ("", 14, C_UI_TEXT, False),
    ("ART & ASSETS", 30, C_UI_TEXT_BRIGHT, True),
    ("Original sprites and visual effects", 20, C_UI_TEXT_DIM, False),
    ("", 14, C_UI_TEXT, False),
    ("AI & PATHFINDING", 30, C_UI_TEXT_BRIGHT, True),
    ("A* Search Algorithm", 20, C_UI_TEXT, False),
    ("State-Machine Hunter & Knight Behaviour", 20, C_UI_TEXT, False),
    ("Q-Learning Reinforcement Learning module", 20, C_UI_TEXT, False),
    ("", 14, C_UI_TEXT, False),
    ("NEW IN VERSION 2.0", 30, C_YELLOW, True),
    ("Dynamic weather system (Rain, Storm)", 20, C_UI_TEXT_DIM, False),
    ("Day/Night cycle with ambient tints", 20, C_UI_TEXT_DIM, False),
    ("Boss Knight with crown decoration", 20, C_UI_TEXT_DIM, False),
    ("Combo multiplier system", 20, C_UI_TEXT_DIM, False),
    ("Objectives panel & speed indicator", 20, C_UI_TEXT_DIM, False),
    ("macOS Metal rendering fix (software SDL2)", 20, C_UI_TEXT_DIM, False),
    ("", 14, C_UI_TEXT, False),
    ("BUILT WITH", 30, C_UI_TEXT_BRIGHT, True),
    ("Python 3.12", 20, C_UI_TEXT, False),
    ("Pygame 2.6", 20, C_UI_TEXT, False),
    ("", 14, C_UI_TEXT, False),
    ("SPECIAL THANKS", 30, C_UI_TEXT_BRIGHT, True),
    ("St Mary's University", 20, C_UI_TEXT_DIM, False),
    ("The Pygame Community", 20, C_UI_TEXT_DIM, False),
    ("", 24, C_UI_TEXT, False),
    ("Thank you for playing!", 34, C_UI_ACCENT, True),
    ("", 80, C_UI_TEXT, False),
]

# ---------------------------------------------------------------------------
# Tiny background star for credits screen
# ---------------------------------------------------------------------------
class _CStar:
    def __init__(self):
        self.x = random.uniform(0, WINDOW_WIDTH)
        self.y = random.uniform(0, WINDOW_HEIGHT)
        self.r = random.randint(1, 2)
        self.a = random.randint(40, 130)
        self.tw = random.uniform(0, math.tau)
        self.ts = random.uniform(1.0, 3.5)

    def update(self, dt):
        self.tw += self.ts * dt

    def draw(self, surf):
        a = int(self.a * (0.5 + 0.5 * math.sin(self.tw)))
        c = (a, a, int(a * 0.7))
        pygame.draw.circle(surf, c, (int(self.x), int(self.y)), self.r)


class CreditsState:
    SCROLL_SPEED = 48.0   # pixels / second

    def __init__(self, game):
        self.game     = game
        self._y       = float(WINDOW_HEIGHT)
        self._time    = 0.0
        self._stars   = [_CStar() for _ in range(90)]
        self._back    = Button(pygame.Rect(20, 20, 128, 40), "← BACK",
                               callback=lambda: self.game.change_state("menu"),
                               font_size=16)
        self._total_h = sum(size + 6 for _, size, _, _ in CREDIT_LINES)

    def enter(self, **kwargs):
        self._y    = float(WINDOW_HEIGHT)
        self._time = 0.0

    def exit(self):
        pass

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.change_state("menu")
        self._back.handle_event(event)
        if event.type == pygame.MOUSEWHEEL:
            self._y -= event.y * 30

    def update(self, dt: float):
        self._time += dt
        self._y    -= self.SCROLL_SPEED * dt
        if self._y < -self._total_h:
            self._y = float(WINDOW_HEIGHT)
        for s in self._stars:
            s.update(dt)
        self._back.update(dt)

    def draw(self, surface: pygame.Surface):
        surface.fill(C_BG)

        for s in self._stars:
            s.draw(surface)

        # Soft vignette edges
        t = self._time
        for i in range(3):
            a = int(30 + 15 * math.sin(t * 0.8 + i))
            vs = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            for r in range(0, 180 + i * 40, 20):
                pygame.draw.rect(vs, (0, 0, 0, max(0, a - r // 5)),
                                 (r, r, WINDOW_WIDTH - 2 * r, WINDOW_HEIGHT - 2 * r), 20)
            surface.blit(vs, (0, 0))

        y = int(self._y)
        for text, size, color, bold in CREDIT_LINES:
            if -size < y < WINDOW_HEIGHT + size:
                draw_text(surface, text, WINDOW_WIDTH // 2, y,
                          size=size, color=color, bold=bold,
                          align="center", shadow=bold)
            y += size + 6

        self._back.draw(surface)
