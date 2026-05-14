"""
Main menu: animated star field, title, mode select, settings entry.
Commercial-quality overhaul with animated title, particle effects, rich panels.
"""
from __future__ import annotations
import math
import random
import pygame
from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, VERSION,
    C_BG, C_UI_TEXT, C_UI_TEXT_BRIGHT, C_UI_TEXT_DIM,
    C_UI_BORDER, C_UI_BORDER_HI, C_UI_ACCENT, C_UI_PANEL, C_UI_PANEL_2,
    C_WHITE, C_BLACK, C_YELLOW, C_GREEN, C_RED,
    C_HUNTER_NAV, C_KNIGHT, C_TREASURE_GOLD, C_HUNTER_HERO,
    MODE_WATCH, MODE_COMMAND, MODE_HERO,
    DIFF_EASY, DIFF_NORMAL, DIFF_HARD, DIFF_LEGENDARY,
    DIFFICULTY_SETTINGS,
)
from src.ui import Button, draw_text, draw_panel, draw_hline


# ---------------------------------------------------------------------------
# Animated star field
# ---------------------------------------------------------------------------
class _Star:
    __slots__ = ("x", "y", "speed", "size", "alpha", "twinkle", "twinkle_speed")

    def __init__(self):
        self.reset(random.uniform(0, WINDOW_HEIGHT))

    def reset(self, y=0.0):
        self.x            = random.uniform(0, WINDOW_WIDTH)
        self.y            = float(y)
        self.speed        = random.uniform(10, 40)
        self.size         = random.randint(1, 3)
        self.alpha        = random.randint(80, 230)
        self.twinkle      = random.uniform(0, math.pi * 2)
        self.twinkle_speed = random.uniform(1.0, 4.0)

    def update(self, dt: float):
        self.y       += self.speed * dt
        self.twinkle += self.twinkle_speed * dt
        if self.y > WINDOW_HEIGHT:
            self.reset()

    def draw(self, surf: pygame.Surface):
        a = int(self.alpha * (0.7 + 0.3 * math.sin(self.twinkle)))
        c = (a, a, int(a * 0.82))
        pygame.draw.circle(surf, c, (int(self.x), int(self.y)), self.size)


# ---------------------------------------------------------------------------
# Floating particle (for menu atmosphere)
# ---------------------------------------------------------------------------
class _MenuParticle:
    __slots__ = ("x", "y", "vy", "life", "max_life", "color", "r")

    def __init__(self):
        self.reset()

    def reset(self):
        self.x       = random.uniform(0, WINDOW_WIDTH)
        self.y       = WINDOW_HEIGHT + 10
        self.vy      = random.uniform(-25, -10)
        self.max_life = random.uniform(4, 9)
        self.life    = self.max_life
        tier = random.randint(0, 2)
        self.color   = [C_TREASURE_GOLD, C_UI_BORDER_HI, (255, 255, 200)][tier]
        self.r       = random.randint(1, 2)

    def update(self, dt):
        self.y    += self.vy * dt
        self.life -= dt
        if self.life <= 0 or self.y < -10:
            self.reset()

    def draw(self, surf):
        t = self.life / self.max_life
        a = int(180 * t)
        if a > 0:
            col = tuple(max(0, int(c * t)) for c in self.color[:3])
            pygame.draw.circle(surf, col, (int(self.x), int(self.y)), self.r)


# ---------------------------------------------------------------------------
# MenuState
# ---------------------------------------------------------------------------
class MenuState:
    def __init__(self, game):
        self.game = game
        self._stars       = [_Star() for _ in range(140)]
        self._particles   = [_MenuParticle() for _ in range(30)]
        self._time        = 0.0
        self._sub         = "main"    # "main" | "mode" | "difficulty"
        self._chosen_mode = MODE_WATCH

        # Main menu buttons
        bw, bh = 300, 50
        cx = WINDOW_WIDTH // 2 - bw // 2

        self._main_btns = [
            Button(pygame.Rect(cx, 318, bw, bh), "PLAY",
                   callback=self._go_mode, font_size=24),
            Button(pygame.Rect(cx, 380, bw, bh), "TUTORIAL",
                   callback=lambda: self.game.change_state("tutorial")),
            Button(pygame.Rect(cx, 442, bw, bh), "SETTINGS",
                   callback=lambda: self.game.change_state("settings")),
            Button(pygame.Rect(cx, 504, bw, bh), "CREDITS",
                   callback=lambda: self.game.change_state("credits")),
            Button(pygame.Rect(cx, 572, bw, bh), "EXIT",
                   callback=self._quit, font_size=20),
        ]

        # Mode select buttons — descriptions drawn separately
        mw, mh = 360, 88
        mx = WINDOW_WIDTH // 2 - mw // 2
        self._mode_btns = [
            Button(pygame.Rect(mx, 248, mw, mh), "WATCH MODE",
                   callback=lambda: self._pick_mode(MODE_WATCH), font_size=22),
            Button(pygame.Rect(mx, 352, mw, mh), "COMMAND MODE",
                   callback=lambda: self._pick_mode(MODE_COMMAND), font_size=22),
            Button(pygame.Rect(mx, 456, mw, mh), "HERO MODE",
                   callback=lambda: self._pick_mode(MODE_HERO), font_size=22),
            Button(pygame.Rect(mx, 578, 170, 44), "BACK",
                   callback=lambda: self._set_sub("main")),
        ]
        self._mode_descs = [
            "Observe the AI simulation unfold",
            "Click hunters to issue move commands",
            "Control a hunter with WASD keys",
        ]
        self._mode_icons = ["★", "⚑", "♞"]

        # Difficulty buttons
        diffs = [DIFF_EASY, DIFF_NORMAL, DIFF_HARD, DIFF_LEGENDARY]
        diff_colors = [C_GREEN, C_UI_TEXT_BRIGHT, C_YELLOW, C_RED]
        dw, dh = 260, 54
        dy0 = 275
        self._diff_btns  = []
        self._diff_colors = diff_colors
        for i, d in enumerate(diffs):
            dd = d
            self._diff_btns.append(Button(
                pygame.Rect(WINDOW_WIDTH//2 - dw//2, dy0 + i*70, dw, dh),
                DIFFICULTY_SETTINGS[d]["label"],
                callback=lambda x=dd: self._launch(x),
                font_size=22,
            ))
        self._diff_btns.append(Button(
            pygame.Rect(WINDOW_WIDTH//2 - 130, dy0 + 4*70, 260, 44), "BACK",
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
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self._sub != "main":
                self._sub = "main"
                return
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
        for p in self._particles:
            p.update(dt)
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
        # Floating gold particles
        for p in self._particles:
            p.draw(surface)

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
        # Animated pulsing title
        glow  = 0.5 + 0.5 * math.sin(self._time * 1.6)
        alpha = int(190 + 65 * glow)
        gold  = (alpha, int(alpha * 0.84), int(alpha * 0.45))

        # Title shadow + text
        draw_text(surface, "KNIGHTS", WINDOW_WIDTH//2, 90,
                  size=98, color=gold, bold=True, align="center", shadow=True)
        draw_text(surface, "OF  ELDORIA", WINDOW_WIDTH//2, 192,
                  size=56, color=C_UI_TEXT_BRIGHT, bold=True,
                  align="center", shadow=True)

        # Sub-title
        sub_alpha = int(160 + 40 * math.sin(self._time * 2.2 + 1))
        draw_text(surface, "A Medieval Treasure Hunt",
                  WINDOW_WIDTH//2, 264, size=18,
                  color=(sub_alpha, sub_alpha, int(sub_alpha * 0.7)),
                  align="center")

        self._draw_deco(surface, 302)

        for b in self._main_btns:
            b.draw(surface)

    def _draw_mode(self, surface: pygame.Surface):
        draw_text(surface, "SELECT GAME MODE", WINDOW_WIDTH//2, 175,
                  size=38, color=C_UI_TEXT_BRIGHT, bold=True,
                  align="center", shadow=True)
        self._draw_deco(surface, 220)

        for i, b in enumerate(self._mode_btns):
            b.draw(surface)
            if i < len(self._mode_descs):
                draw_text(surface, self._mode_descs[i],
                          b.rect.centerx, b.rect.bottom - 22,
                          size=14, color=C_UI_TEXT_DIM, align="center")

    def _draw_difficulty(self, surface: pygame.Surface):
        draw_text(surface, "SELECT DIFFICULTY", WINDOW_WIDTH//2, 175,
                  size=38, color=C_UI_TEXT_BRIGHT, bold=True,
                  align="center", shadow=True)
        mode_label = {"watch": "Watch Mode", "command": "Command Mode",
                      "hero": "Hero Mode"}.get(self._chosen_mode, self._chosen_mode.title())
        draw_text(surface, f"Mode: {mode_label}",
                  WINDOW_WIDTH//2, 228, size=16, color=C_UI_ACCENT, align="center")
        self._draw_deco(surface, 258)

        diff_descs = {
            DIFF_EASY:      "Few knights, plentiful treasure — ideal for learning",
            DIFF_NORMAL:    "Balanced challenge for experienced hunters",
            DIFF_HARD:      "More knights, scarce treasure — for veterans only",
            DIFF_LEGENDARY: "Relentless knights — only the boldest survive",
        }
        diffs = [DIFF_EASY, DIFF_NORMAL, DIFF_HARD, DIFF_LEGENDARY]
        for i, (b, d) in enumerate(zip(self._diff_btns[:-1], diffs)):
            b.draw(surface)
            col = self._diff_colors[i]
            draw_text(surface, diff_descs[d],
                      b.rect.centerx, b.rect.bottom - 18,
                      size=13, color=C_UI_TEXT_DIM, align="center")
        self._diff_btns[-1].draw(surface)  # BACK button

    def _draw_deco(self, surface: pygame.Surface, y: int):
        """Decorative gold divider with gem centre."""
        lx1, lx2 = WINDOW_WIDTH//2 - 260, WINDOW_WIDTH//2 - 44
        rx1, rx2 = WINDOW_WIDTH//2 + 44,  WINDOW_WIDTH//2 + 260

        # Gradient lines (two shades)
        pygame.draw.line(surface, C_UI_BORDER, (lx1, y), (lx2, y), 1)
        pygame.draw.line(surface, C_UI_BORDER, (rx1, y), (rx2, y), 1)
        pygame.draw.line(surface, C_UI_BORDER_HI, (lx1+20, y), (lx2-4, y), 1)
        pygame.draw.line(surface, C_UI_BORDER_HI, (rx1+4,  y), (rx2-20, y), 1)

        # Centre gem with pulse
        pulse = 0.7 + 0.3 * math.sin(self._time * 3.0)
        r_gem = int(7 * pulse)
        pygame.draw.circle(surface, C_TREASURE_GOLD,  (WINDOW_WIDTH//2, y), r_gem)
        pygame.draw.circle(surface, C_UI_BORDER_HI, (WINDOW_WIDTH//2, y), r_gem, 1)
        # Tiny flanking diamonds
        for offset in (-24, 24):
            cx = WINDOW_WIDTH//2 + offset
            pts = [(cx, y-4), (cx+3, y), (cx, y+4), (cx-3, y)]
            pygame.draw.polygon(surface, C_UI_BORDER, pts)
