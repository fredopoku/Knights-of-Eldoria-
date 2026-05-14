"""Celebration victory screen with confetti, gold glow and particle effects."""
from __future__ import annotations
import math
import random
import pygame
from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    C_BG, C_UI_TEXT, C_UI_TEXT_BRIGHT, C_UI_TEXT_DIM,
    C_UI_PANEL, C_UI_BORDER, C_UI_BORDER_HI,
    C_GREEN, C_YELLOW, C_TREASURE_GOLD, C_STAR, C_UI_ACCENT,
)
from src.ui import Button, draw_text, draw_panel, draw_hline
from src.particles import ParticleSystem


# ---------------------------------------------------------------------------
# Golden star burst particle for the victory screen
# ---------------------------------------------------------------------------
class _GoldStar:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x        = random.uniform(0, WINDOW_WIDTH)
        self.y        = random.uniform(0, WINDOW_HEIGHT * 0.5)
        self.vx       = random.uniform(-20, 20)
        self.vy       = random.uniform(-5, 15)
        self.max_life = random.uniform(2.5, 6.0)
        self.life     = self.max_life
        self.r        = random.uniform(1.5, 3.5)
        cols          = [(255, 215, 50), (255, 240, 100), (255, 200, 30),
                         (255, 180, 200), (180, 230, 255)]
        self.color    = random.choice(cols)

    def update(self, dt):
        self.x    += self.vx * dt
        self.y    += self.vy * dt
        self.life -= dt
        if self.life <= 0 or self.y > WINDOW_HEIGHT + 20:
            self.reset()

    def draw(self, surf):
        t   = max(0.0, self.life / self.max_life)
        col = tuple(max(0, int(c * t)) for c in self.color)
        r   = max(1, int(self.r * t))
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), r)


class VictoryState:
    def __init__(self, game):
        self.game       = game
        self._stats     = {}
        self._mode      = ""
        self._diff      = ""
        self._time      = 0.0
        self._particles = ParticleSystem()
        self._gold_stars= [_GoldStar() for _ in range(50)]

        bw, bh = 234, 54
        cx = WINDOW_WIDTH // 2
        self._again = Button(pygame.Rect(cx - bw - 14, 502, bw, bh),
                             "PLAY AGAIN", callback=self._do_again, font_size=22)
        self._menu  = Button(pygame.Rect(cx + 14,     502, bw, bh),
                             "MAIN MENU",
                             callback=lambda: self.game.change_state("menu"),
                             font_size=22)

    def _do_again(self):
        self.game.change_state("play", mode=self._mode, difficulty=self._diff)

    def enter(self, stats=None, mode="", difficulty="", **kw):
        self._stats     = stats or {}
        self._mode      = mode
        self._diff      = difficulty
        self._time      = 0.0
        self._particles = ParticleSystem()
        self._gold_stars = [_GoldStar() for _ in range(50)]
        # Opening confetti bursts
        for _ in range(8):
            self._particles.confetti(
                random.randint(80, WINDOW_WIDTH - 80), 80)
        # Save score
        self.game.saves.save(
            slot=0, mode=mode, difficulty=difficulty,
            step=stats.get("step", 0) if stats else 0,
            score=stats.get("score", 0) if stats else 0,
            pct=stats.get("pct", 0) if stats else 0,
        )
        self.game.achievements.unlock("saved_game")
        if difficulty == "hard":
            self.game.achievements.unlock("hard_complete")
        if difficulty == "legendary":
            self.game.achievements.unlock("legendary_run")
        self.game.audio.play("victory")

    def exit(self): pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.change_state("menu")
        self._again.handle_event(event)
        self._menu.handle_event(event)

    def update(self, dt):
        self._time += dt
        self._again.update(dt)
        self._menu.update(dt)
        self._particles.update(dt)
        for gs in self._gold_stars:
            gs.update(dt)

        # Continuous confetti bursts
        if random.random() < 0.12:
            self._particles.confetti(
                random.choice([80, WINDOW_WIDTH // 2, WINDOW_WIDTH - 80]),
                random.randint(40, 130))

        # Ambient sparkles
        if random.random() < 0.25:
            self._particles.sparkle(
                random.randint(50, WINDOW_WIDTH - 50),
                random.randint(50, WINDOW_HEIGHT - 50),
                C_STAR)

    def draw(self, surface: pygame.Surface):
        surface.fill(C_BG)

        t = self._time

        # Gold vignette glow
        va = int(22 + 16 * math.sin(t * 1.4))
        vs = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for r in range(0, 320, 18):
            pygame.draw.rect(vs, (190, 140, 0, max(0, va - r // 6)),
                             (r, r, WINDOW_WIDTH - 2 * r, WINDOW_HEIGHT - 2 * r), 18)
        surface.blit(vs, (0, 0))

        for gs in self._gold_stars:
            gs.draw(surface)

        self._particles.draw(surface)

        cx = WINDOW_WIDTH // 2

        # Animated gold VICTORY title
        glow  = 0.5 + 0.5 * math.sin(t * 2.2)
        alpha = int(198 + 57 * glow)
        gold  = (alpha, int(alpha * 0.82), int(alpha * 0.12))

        for off, mult in [(6, 0.12), (4, 0.25), (2, 0.42)]:
            corona = (int(alpha * mult * 0.9), int(alpha * 0.55 * mult), 0)
            draw_text(surface, "VICTORY!", cx, 76 + off,
                      size=88, color=corona, bold=True, align="center")
        draw_text(surface, "VICTORY!", cx, 76,
                  size=88, color=gold, bold=True, align="center", shadow=True)

        draw_text(surface, "The hunters have triumphed!",
                  cx, 182, size=24, color=C_UI_TEXT_DIM, align="center")

        # Decorative divider
        pygame.draw.line(surface, C_UI_BORDER, (cx - 220, 218), (cx - 50, 218), 1)
        pygame.draw.line(surface, C_UI_BORDER, (cx + 50, 218), (cx + 220, 218), 1)
        pygame.draw.circle(surface, C_TREASURE_GOLD, (cx, 218), 7)
        pygame.draw.circle(surface, C_UI_BORDER_HI,  (cx, 218), 7, 1)

        # Stats panel
        pw, ph = 556, 248
        pr = pygame.Rect(cx - pw // 2, 228, pw, ph)
        draw_panel(surface, pr)
        draw_text(surface, "MISSION COMPLETE", cx, pr.top + 14,
                  size=20, color=C_UI_TEXT_BRIGHT, bold=True, align="center")
        # Gold gem decorations
        pygame.draw.circle(surface, C_TREASURE_GOLD, (pr.left + 32, pr.top + 26), 9)
        pygame.draw.circle(surface, C_TREASURE_GOLD, (pr.right - 32, pr.top + 26), 9)
        draw_hline(surface, pr.left + 14, pr.right - 14, pr.top + 46)

        s = self._stats
        y = pr.top + 60
        for label, val, col in [
            ("Steps Taken",        str(s.get("step", 0)),         C_UI_TEXT_BRIGHT),
            ("Treasure Collected", f"{s.get('pct', 0):.1f}%",     C_GREEN),
            ("Final Score",        f"{s.get('score', 0):,}",      C_TREASURE_GOLD),
            ("Mode",               self._mode.title(),             C_UI_ACCENT),
            ("Difficulty",         self._diff.title(),             C_YELLOW),
        ]:
            draw_text(surface, label, pr.left + 26, y, size=17, color=C_UI_TEXT_DIM)
            draw_text(surface, val,   pr.right - 26, y, size=17,
                      color=col, bold=True, align="right")
            y += 32

        self._again.draw(surface)
        self._menu.draw(surface)

        draw_text(surface, "Press ESC for main menu",
                  cx, 582, size=14, color=C_UI_TEXT_DIM, align="center")
