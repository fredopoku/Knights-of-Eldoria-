"""
Main menu: animated star field, title, mode select, settings entry.
"""
from __future__ import annotations
import math
import random
import pygame
from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, VERSION,
    C_BG, C_UI_TEXT, C_UI_TEXT_BRIGHT, C_UI_TEXT_DIM,
    C_UI_BORDER, C_UI_BORDER_HI, C_UI_ACCENT,
    C_WHITE, C_BLACK, C_YELLOW,
    C_HUNTER_NAV, C_KNIGHT, C_TREASURE_GOLD,
    MODE_WATCH, MODE_COMMAND, MODE_HERO,
    DIFF_EASY, DIFF_NORMAL, DIFF_HARD, DIFF_LEGENDARY,
    DIFFICULTY_SETTINGS,
)
from src.ui import Button, draw_text, draw_panel, draw_hline


# ---------------------------------------------------------------------------
# Animated star field
# ---------------------------------------------------------------------------
class _Star:
    __slots__ = ("x", "y", "speed", "size", "alpha")

    def __init__(self):
        self.reset(random.uniform(0, WINDOW_HEIGHT))

    def reset(self, y=0.0):
        self.x     = random.uniform(0, WINDOW_WIDTH)
        self.y     = float(y)
        self.speed = random.uniform(12, 45)
        self.size  = random.randint(1, 3)
        self.alpha = random.randint(100, 255)

    def update(self, dt: float):
        self.y += self.speed * dt
        if self.y > WINDOW_HEIGHT:
            self.reset()

    def draw(self, surf: pygame.Surface):
        c = (self.alpha, self.alpha, int(self.alpha * 0.8))
        pygame.draw.circle(surf, c, (int(self.x), int(self.y)), self.size)


# ---------------------------------------------------------------------------
# MenuState
# ---------------------------------------------------------------------------
class MenuState:
    def __init__(self, game):
        self.game = game
        self._stars   = [_Star() for _ in range(120)]
        self._time    = 0.0
        self._sub     = "main"    # "main" | "mode" | "difficulty"
        self._chosen_mode = MODE_WATCH

        # Main menu buttons
        bw, bh = 280, 48
        cx = WINDOW_WIDTH // 2 - bw // 2

        self._main_btns = [
            Button(pygame.Rect(cx, 310, bw, bh), "PLAY",
                   callback=self._go_mode, font_size=24),
            Button(pygame.Rect(cx, 370, bw, bh), "TUTORIAL",
                   callback=lambda: self.game.change_state("tutorial")),
            Button(pygame.Rect(cx, 430, bw, bh), "SETTINGS",
                   callback=lambda: self.game.change_state("settings")),
            Button(pygame.Rect(cx, 490, bw, bh), "CREDITS",
                   callback=lambda: self.game.change_state("credits")),
            Button(pygame.Rect(cx, 560, bw, bh), "EXIT",
                   callback=self._quit, font_size=20),
        ]

        # Mode select buttons  (no \n — descriptions drawn separately)
        mw, mh = 340, 90
        mx = WINDOW_WIDTH // 2 - mw // 2
        self._mode_btns = [
            Button(pygame.Rect(mx, 250, mw, mh), "WATCH MODE",
                   callback=lambda: self._pick_mode(MODE_WATCH), font_size=22),
            Button(pygame.Rect(mx, 355, mw, mh), "COMMAND MODE",
                   callback=lambda: self._pick_mode(MODE_COMMAND), font_size=22),
            Button(pygame.Rect(mx, 460, mw, mh), "HERO MODE",
                   callback=lambda: self._pick_mode(MODE_HERO), font_size=22),
            Button(pygame.Rect(mx, 580, 160, 44), "BACK",
                   callback=lambda: self._set_sub("main")),
        ]
        self._mode_descs = [
            "Observe the AI simulation unfold",
            "Click hunters to issue move commands",
            "Control a hunter with WASD keys",
        ]

        # Difficulty buttons
        diffs = [DIFF_EASY, DIFF_NORMAL, DIFF_HARD, DIFF_LEGENDARY]
        dw, dh = 240, 52
        dy0 = 280
        self._diff_btns = []
        for i, d in enumerate(diffs):
            dd = d
            self._diff_btns.append(Button(
                pygame.Rect(WINDOW_WIDTH//2 - dw//2, dy0 + i*68, dw, dh),
                DIFFICULTY_SETTINGS[d]["label"],
                callback=lambda x=dd: self._launch(x),
                font_size=22,
            ))
        self._diff_btns.append(Button(
            pygame.Rect(WINDOW_WIDTH//2 - 120, dy0 + 4*68, 240, 44), "← BACK",
            callback=lambda: self._set_sub("mode")
        ))

        # Achievement toast
        self._toast_surf: pygame.Surface | None = None
        self._toast_timer = 0.0

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------
    def _go_mode(self):
        self._sub = "mode"

    def _pick_mode(self, mode: str):
        self._chosen_mode = mode
        self._sub = "difficulty"

    def _set_sub(self, sub: str):
        self._sub = sub

    def _launch(self, difficulty: str):
        self.game.change_state("play",
                               mode=self._chosen_mode,
                               difficulty=difficulty)

    def _quit(self):
        self.game.running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def enter(self, **kwargs):
        self._sub = "main"
        self.game.audio.play_music("music_main.ogg")

    def exit(self):
        pass

    # ------------------------------------------------------------------
    # Handle events
    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event):
        btns = (self._main_btns if self._sub == "main" else
                self._mode_btns if self._sub == "mode" else
                self._diff_btns)
        for b in btns:
            if b.handle_event(event):
                self.game.audio.play("ui_click")
                break

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, dt: float):
        self._time += dt
        for s in self._stars:
            s.update(dt)
        btns = (self._main_btns if self._sub == "main" else
                self._mode_btns if self._sub == "mode" else
                self._diff_btns)
        for b in btns:
            b.update(dt)
        if self._toast_timer > 0:
            self._toast_timer -= dt

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        surface.fill(C_BG)

        # Stars
        for s in self._stars:
            s.draw(surface)

        if self._sub == "main":
            self._draw_main(surface)
        elif self._sub == "mode":
            self._draw_mode(surface)
        else:
            self._draw_difficulty(surface)

        # Toast
        if self._toast_timer > 0 and self._toast_surf:
            surface.blit(self._toast_surf, (20, WINDOW_HEIGHT - 80))

        # Version
        draw_text(surface, f"v{VERSION}", WINDOW_WIDTH - 10, WINDOW_HEIGHT - 22,
                  size=13, color=C_UI_TEXT_DIM, align="right")

    def _draw_main(self, surface: pygame.Surface):
        # Decorative line
        self._draw_deco(surface, 290)

        # Title
        glow = 0.5 + 0.5 * math.sin(self._time * 1.8)
        alpha = int(180 + 75 * glow)
        draw_text(surface, "KNIGHTS", WINDOW_WIDTH//2, 120,
                  size=90, color=(alpha, int(alpha*0.85), int(alpha*0.5)),
                  bold=True, align="center", shadow=True)
        draw_text(surface, "OF  ELDORIA", WINDOW_WIDTH//2, 200,
                  size=52, color=C_UI_TEXT_BRIGHT,
                  bold=True, align="center", shadow=True)
        draw_text(surface, "A Medieval Treasure Hunt", WINDOW_WIDTH//2, 268,
                  size=18, color=C_UI_TEXT_DIM, align="center")

        for b in self._main_btns:
            b.draw(surface)

    def _draw_mode(self, surface: pygame.Surface):
        draw_text(surface, "SELECT GAME MODE", WINDOW_WIDTH//2, 170,
                  size=36, color=C_UI_TEXT_BRIGHT, bold=True,
                  align="center", shadow=True)
        for i, b in enumerate(self._mode_btns):
            b.draw(surface)
            if i < len(self._mode_descs):
                draw_text(surface, self._mode_descs[i],
                          b.rect.centerx, b.rect.bottom - 22,
                          size=14, color=C_UI_TEXT_DIM, align="center")

    def _draw_difficulty(self, surface: pygame.Surface):
        draw_text(surface, "SELECT DIFFICULTY", WINDOW_WIDTH//2, 170,
                  size=36, color=C_UI_TEXT_BRIGHT, bold=True,
                  align="center", shadow=True)
        draw_text(surface, f"Mode: {self._chosen_mode.upper()}",
                  WINDOW_WIDTH//2, 220,
                  size=18, color=C_UI_TEXT_DIM, align="center")
        for b in self._diff_btns:
            b.draw(surface)

    def _draw_deco(self, surface: pygame.Surface, y: int):
        """Draw a decorative horizontal divider with gem icons."""
        pygame.draw.line(surface, C_UI_BORDER,
                         (WINDOW_WIDTH//2 - 250, y),
                         (WINDOW_WIDTH//2 - 40,  y), 1)
        pygame.draw.line(surface, C_UI_BORDER,
                         (WINDOW_WIDTH//2 + 40,  y),
                         (WINDOW_WIDTH//2 + 250, y), 1)
        pygame.draw.circle(surface, C_TREASURE_GOLD, (WINDOW_WIDTH//2, y), 6)
        pygame.draw.circle(surface, C_UI_BORDER_HI, (WINDOW_WIDTH//2, y), 6, 1)
