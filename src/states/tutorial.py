"""Interactive tutorial with step-by-step guidance."""
from __future__ import annotations
import pygame
from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    C_BG, C_UI_TEXT, C_UI_TEXT_BRIGHT, C_UI_TEXT_DIM,
    C_UI_PANEL, C_UI_BORDER, C_UI_BORDER_HI,
    C_HUNTER_NAV, C_KNIGHT, C_TREASURE_GOLD,
    C_HIDEOUT, C_GARRISON,
)
from src.ui import Button, draw_text, draw_panel, draw_hline


STEPS = [
    {
        "title": "Welcome to Knights of Eldoria",
        "text": (
            "In this medieval world, brave hunters seek treasure scattered\n"
            "across the land — while knights patrol to stop them.\n\n"
            "Your goal: collect as much treasure as possible before the\n"
            "simulation ends or all treasure decays away."
        ),
        "color": C_UI_TEXT_BRIGHT,
    },
    {
        "title": "The Hunters  🏹",
        "text": (
            "Hunters (blue circles) autonomously explore the map,\n"
            "collect treasures, and return them to hideouts.\n\n"
            "Each hunter has a skill:\n"
            "  • Navigation — sees farther, finds better paths\n"
            "  • Endurance  — moves cheaper, recovers faster\n"
            "  • Stealth    — harder for knights to detect\n\n"
            "Watch the stamina bar below each hunter!"
        ),
        "color": C_HUNTER_NAV,
    },
    {
        "title": "The Knights  ⚔️",
        "text": (
            "Knights (red diamonds) patrol circular routes.\n"
            "When they spot a hunter they give chase!\n\n"
            "If caught, the hunter loses stamina and drops their\n"
            "carried treasure. Hunters with Stealth skill have a\n"
            "50% chance to avoid detection.\n\n"
            "Knights rest at garrisons to recover energy."
        ),
        "color": C_KNIGHT,
    },
    {
        "title": "Treasure  💰",
        "text": (
            "Three tiers of treasure are scattered across the map:\n\n"
            "  Bronze  — worth 3 pts  (most common)\n"
            "  Silver  — worth 7 pts\n"
            "  Gold    — worth 13 pts (rarest)\n\n"
            "Treasure slowly decays over time, so act quickly!\n"
            "Hunters prioritise gold first."
        ),
        "color": C_TREASURE_GOLD,
    },
    {
        "title": "Hideouts & Garrisons  🏠",
        "text": (
            "Hideouts (brown buildings) are the hunter's safe haven.\n"
            "Hunters rest here to recover stamina and deposit treasure.\n"
            "When hunters from all 3 skill types are present,\n"
            "a new hunter may be recruited!\n\n"
            "Garrisons (dark-red buildings) serve the same purpose\n"
            "for knights — they rest and recharge energy there."
        ),
        "color": C_HIDEOUT,
    },
    {
        "title": "Game Modes  🎮",
        "text": (
            "You can play three ways:\n\n"
            "  WATCH    — Observe the AI simulation unfold.\n"
            "             Use speed controls to fast-forward.\n\n"
            "  COMMAND  — Click hunters to select them, then click\n"
            "             the map to give movement orders.\n\n"
            "  HERO     — Take direct control! Use WASD / Arrow Keys\n"
            "             to move your golden hunter, collect treasure,\n"
            "             and avoid the knights."
        ),
        "color": C_UI_TEXT_BRIGHT,
    },
    {
        "title": "Controls & Tips  💡",
        "text": (
            "Keyboard shortcuts during play:\n"
            "  Space        — Pause / Resume\n"
            "  +  /  –      — Increase / Decrease speed\n"
            "  S            — Single step\n"
            "  Escape       — Open pause menu\n\n"
            "Tips:\n"
            "  • Use Command mode to direct hunters away from knights\n"
            "  • In Hero mode, visit a hideout to deposit treasure\n"
            "  • Try Legendary difficulty for a real challenge!"
        ),
        "color": C_UI_TEXT_BRIGHT,
    },
]


class TutorialState:
    def __init__(self, game):
        self.game   = game
        self._step  = 0

        bw, bh = 180, 44
        cx = WINDOW_WIDTH // 2
        self._next_btn = Button(
            pygame.Rect(cx + 20, 560, bw, bh), "NEXT →",
            callback=self._next, font_size=20)
        self._prev_btn = Button(
            pygame.Rect(cx - 20 - bw, 560, bw, bh), "← PREV",
            callback=self._prev, font_size=20)
        self._done_btn = Button(
            pygame.Rect(cx - bw//2, 560, bw, bh), "DONE ✓",
            callback=self._done, font_size=20)

    def _next(self):
        if self._step < len(STEPS) - 1:
            self._step += 1
        else:
            self._done()

    def _prev(self):
        if self._step > 0:
            self._step -= 1

    def _done(self):
        self.game.change_state("menu")

    def enter(self, **kwargs):
        self._step = 0

    def exit(self):
        pass

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RIGHT, pygame.K_RETURN):
                self._next()
            elif event.key == pygame.K_LEFT:
                self._prev()
            elif event.key == pygame.K_ESCAPE:
                self._done()
        self._next_btn.handle_event(event)
        self._prev_btn.handle_event(event)
        self._done_btn.handle_event(event)

    def update(self, dt: float):
        self._next_btn.update(dt)
        self._prev_btn.update(dt)
        self._done_btn.update(dt)

    def draw(self, surface: pygame.Surface):
        surface.fill(C_BG)
        step = STEPS[self._step]

        # Panel
        pw, ph = 700, 420
        pr = pygame.Rect((WINDOW_WIDTH - pw)//2, 120, pw, ph)
        draw_panel(surface, pr)

        # Title
        draw_text(surface, step["title"],
                  WINDOW_WIDTH//2, pr.top + 22,
                  size=30, color=step["color"],
                  bold=True, align="center", shadow=True)
        draw_hline(surface, pr.left + 12, pr.right - 12, pr.top + 62)

        # Body (handle \n)
        y = pr.top + 78
        for line in step["text"].split("\n"):
            draw_text(surface, line, pr.left + 24, y,
                      size=17, color=C_UI_TEXT)
            y += 24

        # Progress dots
        dot_y = pr.bottom + 20
        total = len(STEPS)
        for i in range(total):
            c = C_UI_BORDER_HI if i == self._step else C_UI_BORDER
            pygame.draw.circle(surface, c,
                               (WINDOW_WIDTH//2 - (total//2 - i)*20, dot_y), 5)

        # Step counter
        draw_text(surface, f"{self._step + 1} / {len(STEPS)}",
                  WINDOW_WIDTH//2, dot_y + 15,
                  size=14, color=C_UI_TEXT_DIM, align="center")

        # Navigation buttons
        if self._step > 0:
            self._prev_btn.draw(surface)
        if self._step < len(STEPS) - 1:
            self._next_btn.draw(surface)
        else:
            self._done_btn.draw(surface)
