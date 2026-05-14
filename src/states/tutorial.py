"""Interactive tutorial with step-by-step guidance and rich visuals."""
from __future__ import annotations
import math
import pygame
from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    C_BG, C_UI_TEXT, C_UI_TEXT_BRIGHT, C_UI_TEXT_DIM,
    C_UI_PANEL, C_UI_PANEL_2, C_UI_BORDER, C_UI_BORDER_HI,
    C_HUNTER_NAV, C_KNIGHT, C_TREASURE_GOLD,
    C_HIDEOUT, C_GARRISON, C_GREEN, C_YELLOW, C_RED,
)
from src.ui import Button, draw_text, draw_panel, draw_hline


STEPS = [
    {
        "title": "Welcome to Knights of Eldoria",
        "text": (
            "In this medieval world, brave hunters seek treasure scattered\n"
            "across the land — while knights patrol to stop them.\n\n"
            "Your goal: collect as much treasure as possible before the\n"
            "simulation ends or all treasure decays away.\n\n"
            "Use the navigation buttons below to proceed."
        ),
        "color": C_UI_TEXT_BRIGHT,
        "icon_col": C_TREASURE_GOLD,
    },
    {
        "title": "The Hunters",
        "text": (
            "Hunters (circles) autonomously explore the map,\n"
            "collect treasures, and return them to hideouts.\n\n"
            "Each hunter has a unique skill:\n"
            "  Navigation — sees farther, finds better paths\n"
            "  Endurance  — moves cheaper, recovers faster\n"
            "  Stealth    — harder for knights to detect\n\n"
            "Watch the stamina bar below each hunter!"
        ),
        "color": C_HUNTER_NAV,
        "icon_col": C_HUNTER_NAV,
    },
    {
        "title": "The Knights",
        "text": (
            "Knights (red diamonds) patrol circular routes.\n"
            "When they spot a hunter they give chase!\n\n"
            "If caught, the hunter loses stamina and drops their\n"
            "carried treasure. Stealth hunters have a 50% chance\n"
            "to dodge detection.\n\n"
            "Occasionally a BOSS KNIGHT appears — watch out!\n"
            "Boss knights are bigger, faster, and more dangerous."
        ),
        "color": C_KNIGHT,
        "icon_col": C_KNIGHT,
    },
    {
        "title": "Treasure",
        "text": (
            "Three tiers of treasure are scattered across the map:\n\n"
            "  Bronze  — worth 3 pts  (most common)\n"
            "  Silver  — worth 7 pts\n"
            "  Gold    — worth 13 pts (rarest)\n\n"
            "Treasure slowly decays over time, so act quickly!\n"
            "Consecutive collections build a COMBO multiplier!\n"
            "Hunters prioritise gold first."
        ),
        "color": C_TREASURE_GOLD,
        "icon_col": C_TREASURE_GOLD,
    },
    {
        "title": "Hideouts & Garrisons",
        "text": (
            "Hideouts (brown buildings) are the hunters' safe haven.\n"
            "Hunters rest here to recover stamina and deposit treasure.\n"
            "When hunters from all 3 skill types are present,\n"
            "a new hunter may be recruited!\n\n"
            "Garrisons (dark-red buildings) serve the same purpose\n"
            "for knights — they rest and recharge energy there."
        ),
        "color": C_HIDEOUT,
        "icon_col": C_HIDEOUT,
    },
    {
        "title": "Weather & Day/Night",
        "text": (
            "The world has dynamic weather and time-of-day cycles.\n\n"
            "  Clear   — standard conditions\n"
            "  Rain    — atmospheric, adds mood\n"
            "  Storm   — lightning flashes illuminate the map!\n\n"
            "Day/Night shifts cast warm or cool tints over the map.\n"
            "Toggle these effects in Settings if you prefer."
        ),
        "color": C_UI_TEXT_BRIGHT,
        "icon_col": C_YELLOW,
    },
    {
        "title": "Game Modes",
        "text": (
            "You can play three ways:\n\n"
            "  WATCH   — Observe the AI simulation unfold.\n"
            "            Use speed controls to fast-forward.\n\n"
            "  COMMAND — Click hunters to select them, then click\n"
            "            the map to give movement orders.\n\n"
            "  HERO    — Take direct control! Use WASD / Arrow Keys\n"
            "            to move your golden hunter, collect treasure,\n"
            "            and avoid the knights."
        ),
        "color": C_UI_TEXT_BRIGHT,
        "icon_col": C_HUNTER_NAV,
    },
    {
        "title": "Controls & Tips",
        "text": (
            "Keyboard shortcuts during play:\n"
            "  Space        — Pause / Resume\n"
            "  +  /  –      — Increase / Decrease speed\n"
            "  S            — Single step\n"
            "  Escape       — Open pause menu\n\n"
            "Tips:\n"
            "  Use Command mode to direct hunters away from knights\n"
            "  In Hero mode, visit a hideout to deposit treasure\n"
            "  Try Legendary difficulty for a real challenge!\n"
            "  Chain collects for big combo bonuses!"
        ),
        "color": C_UI_TEXT_BRIGHT,
        "icon_col": C_GREEN,
    },
]


class TutorialState:
    def __init__(self, game):
        self.game   = game
        self._step  = 0
        self._time  = 0.0

        bw, bh = 184, 46
        cx = WINDOW_WIDTH // 2
        self._next_btn = Button(
            pygame.Rect(cx + 20, 562, bw, bh), "NEXT →",
            callback=self._next, font_size=20)
        self._prev_btn = Button(
            pygame.Rect(cx - 20 - bw, 562, bw, bh), "← PREV",
            callback=self._prev, font_size=20)
        self._done_btn = Button(
            pygame.Rect(cx - bw // 2, 562, bw, bh), "DONE",
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
        self._time = 0.0

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
        self._time += dt
        self._next_btn.update(dt)
        self._prev_btn.update(dt)
        self._done_btn.update(dt)

    def draw(self, surface: pygame.Surface):
        surface.fill(C_BG)
        t    = self._time
        step = STEPS[self._step]
        cx   = WINDOW_WIDTH // 2

        # Animated title glow
        glow  = 0.5 + 0.5 * math.sin(t * 1.6)
        alpha = int(185 + 60 * glow)
        gold  = (int(alpha * 0.85), int(alpha * 0.72), int(alpha * 0.30))
        draw_text(surface, "TUTORIAL", cx, 36,
                  size=46, color=gold, bold=True, align="center", shadow=True)

        # Decorative divider
        pygame.draw.line(surface, C_UI_BORDER, (cx - 220, 94), (cx - 50, 94), 1)
        pygame.draw.line(surface, C_UI_BORDER, (cx + 50, 94),  (cx + 220, 94), 1)
        pulse = 0.7 + 0.3 * math.sin(t * 3.0)
        pygame.draw.circle(surface, step["icon_col"], (cx, 94), int(7 * pulse))
        pygame.draw.circle(surface, C_UI_BORDER_HI, (cx, 94), int(7 * pulse), 1)

        # Content panel
        pw, ph = 720, 420
        pr = pygame.Rect((WINDOW_WIDTH - pw) // 2, 114, pw, ph)
        draw_panel(surface, pr)

        # Step title
        draw_text(surface, step["title"],
                  cx, pr.top + 20,
                  size=30, color=step["color"],
                  bold=True, align="center", shadow=True)
        draw_hline(surface, pr.left + 14, pr.right - 14, pr.top + 62)

        # Body text
        y = pr.top + 76
        for line in step["text"].split("\n"):
            draw_text(surface, line, pr.left + 28, y,
                      size=17, color=C_UI_TEXT)
            y += 26

        # Progress dots
        dot_y = pr.bottom + 18
        total = len(STEPS)
        dot_spacing = 22
        dot_start   = cx - (total * dot_spacing) // 2
        for i in range(total):
            c  = step["icon_col"] if i == self._step else C_UI_BORDER
            r  = 6 if i == self._step else 4
            px = dot_start + i * dot_spacing
            pygame.draw.circle(surface, c, (px, dot_y), r)
            if i == self._step:
                pygame.draw.circle(surface, C_UI_BORDER_HI, (px, dot_y), r, 1)

        # Step counter
        draw_text(surface, f"{self._step + 1} / {len(STEPS)}",
                  cx, dot_y + 16, size=14, color=C_UI_TEXT_DIM, align="center")

        # Navigation buttons
        if self._step > 0:
            self._prev_btn.draw(surface)
        if self._step < len(STEPS) - 1:
            self._next_btn.draw(surface)
        else:
            self._done_btn.draw(surface)
