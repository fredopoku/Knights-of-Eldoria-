"""
Knights of Eldoria — Main Menu.
Animated star field, rune circle, floating treasure particles, animated title.
"""
from __future__ import annotations
import math
import random
import pygame
from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, VERSION,
    C_BG, C_UI_TEXT, C_UI_TEXT_BRIGHT, C_UI_TEXT_DIM,
    C_UI_BORDER, C_UI_BORDER_HI, C_UI_ACCENT, C_UI_PANEL, C_UI_PANEL_2,
    C_WHITE, C_YELLOW, C_GREEN, C_RED, C_ORANGE,
    C_TREASURE_GOLD, C_TREASURE_BRONZE, C_TREASURE_SILVER,
    C_HUNTER_NAV, C_KNIGHT, C_HUNTER_HERO,
    MODE_WATCH, MODE_COMMAND, MODE_HERO,
    DIFF_EASY, DIFF_NORMAL, DIFF_HARD, DIFF_LEGENDARY,
    DIFFICULTY_SETTINGS,
)
from src.ui import Button, draw_text, draw_panel, draw_hline


# ---------------------------------------------------------------------------
# Star — 3-layer parallax with twinkle
# ---------------------------------------------------------------------------
class _Star:
    __slots__ = ("x", "y", "speed", "size", "alpha", "twinkle", "twinkle_s",
                 "layer", "drift_x")

    def __init__(self, layer=0):
        self.layer = layer
        self.reset(random.uniform(0, WINDOW_HEIGHT))

    def reset(self, y=0.0):
        self.x        = random.uniform(0, WINDOW_WIDTH)
        self.y        = float(y)
        self.speed    = (self.layer + 1) * random.uniform(6, 18)
        self.drift_x  = random.uniform(-2, 2)
        self.size     = self.layer + 1
        self.alpha    = random.randint(55 + self.layer * 40, 145 + self.layer * 50)
        self.twinkle  = random.uniform(0, math.tau)
        self.twinkle_s = random.uniform(1.2, 4.5)

    def update(self, dt):
        self.y       += self.speed * dt
        self.x       += self.drift_x * dt
        self.twinkle += self.twinkle_s * dt
        if self.y > WINDOW_HEIGHT:
            self.reset()
        if self.x < 0 or self.x > WINDOW_WIDTH:
            self.reset()

    def draw(self, surf):
        a = int(self.alpha * (0.55 + 0.45 * math.sin(self.twinkle)))
        c = (a, a, int(a * 0.75))
        if self.size > 1:
            pygame.draw.circle(surf, c, (int(self.x), int(self.y)), self.size)
        else:
            surf.set_at((int(self.x), int(self.y)), c)


# ---------------------------------------------------------------------------
# Floating treasure particle
# ---------------------------------------------------------------------------
class _TreasureParticle:
    COLORS = [C_TREASURE_GOLD, C_TREASURE_BRONZE, C_TREASURE_SILVER,
              (255, 220, 80), (255, 200, 50)]
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size")

    def __init__(self):
        self.reset()

    def reset(self):
        self.x        = random.uniform(80, WINDOW_WIDTH - 80)
        self.y        = WINDOW_HEIGHT + 10.0
        self.vx       = random.uniform(-14, 14)
        self.vy       = random.uniform(-28, -12)
        self.max_life = random.uniform(4.0, 9.0)
        self.life     = self.max_life
        self.color    = random.choice(self.COLORS)
        self.size     = random.randint(2, 4)

    def update(self, dt):
        self.x    += self.vx * dt
        self.y    += self.vy * dt
        self.vy   -= 4.0 * dt   # slight acceleration upward
        self.life -= dt
        if self.life <= 0 or self.y < -20:
            self.reset()

    def draw(self, surf):
        t   = max(0.0, self.life / self.max_life)
        a   = int(220 * t)
        col = tuple(max(0, min(255, int(c * t))) for c in self.color)
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), self.size)
        # Tiny glow
        glow_c = tuple(max(0, int(c * t * 0.25)) for c in self.color)
        pygame.draw.circle(surf, glow_c, (int(self.x), int(self.y)), self.size + 2)


# ---------------------------------------------------------------------------
# Ember — fire sparks rising from bottom
# ---------------------------------------------------------------------------
class _Ember:
    COLORS = [(255, 160, 40), (255, 210, 60), (255, 120, 30), (255, 240, 100)]
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color")

    def __init__(self):
        self.reset()

    def reset(self):
        self.x        = random.uniform(0, WINDOW_WIDTH)
        self.y        = WINDOW_HEIGHT + 8.0
        self.vx       = random.uniform(-15, 15)
        self.vy       = random.uniform(-26, -10)
        self.max_life = random.uniform(3.0, 7.0)
        self.life     = self.max_life
        self.color    = random.choice(self.COLORS)

    def update(self, dt):
        self.x    += self.vx * dt
        self.y    += self.vy * dt
        self.life -= dt
        if self.life <= 0 or self.y < -10:
            self.reset()

    def draw(self, surf):
        t = max(0.0, self.life / self.max_life)
        col = tuple(max(0, int(c * t)) for c in self.color)
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), 2)


# ---------------------------------------------------------------------------
# MenuState
# ---------------------------------------------------------------------------
class MenuState:
    def __init__(self, game):
        self.game  = game
        self._time = 0.0
        self._sub  = "main"   # "main" | "mode" | "difficulty"
        self._mode = MODE_WATCH

        # Animated background
        self._stars    = ([_Star(0) for _ in range(80)] +
                          [_Star(1) for _ in range(45)] +
                          [_Star(2) for _ in range(25)])
        self._embers   = [_Ember()           for _ in range(20)]
        self._t_parts  = [_TreasureParticle() for _ in range(22)]

        # Title animation
        self._title_t = 0.0
        self._rune_angle = 0.0

        # ── Main buttons ──
        bw, bh = 320, 54
        cx = WINDOW_WIDTH // 2 - bw // 2
        self._main_btns = [
            Button(pygame.Rect(cx, 318, bw, bh), "PLAY GAME",
                   callback=self._go_mode, font_size=24),
            Button(pygame.Rect(cx, 384, bw, bh), "TUTORIAL",
                   callback=lambda: self.game.change_state("tutorial"), font_size=22),
            Button(pygame.Rect(cx, 450, bw, bh), "ACHIEVEMENTS",
                   callback=self._show_achievements, font_size=22),
            Button(pygame.Rect(cx, 516, bw, bh), "SETTINGS",
                   callback=lambda: self.game.change_state("settings"), font_size=22),
            Button(pygame.Rect(cx, 582, bw, bh), "CREDITS",
                   callback=lambda: self.game.change_state("credits"), font_size=22),
            Button(pygame.Rect(cx, 648, bw, bh), "QUIT",
                   callback=self._quit, font_size=20),
        ]

        # ── Mode buttons ──
        mw, mh = 380, 88
        mx = WINDOW_WIDTH // 2 - mw // 2
        self._mode_btns = [
            Button(pygame.Rect(mx, 228, mw, mh), "WATCH MODE",
                   callback=lambda: self._pick(MODE_WATCH), font_size=22),
            Button(pygame.Rect(mx, 332, mw, mh), "COMMAND MODE",
                   callback=lambda: self._pick(MODE_COMMAND), font_size=22),
            Button(pygame.Rect(mx, 436, mw, mh), "HERO MODE",
                   callback=lambda: self._pick(MODE_HERO), font_size=22),
            Button(pygame.Rect(mx, 572, 190, 46), "BACK",
                   callback=lambda: self._set("main")),
        ]
        self._mode_descs = [
            "Observe the simulation unfold in real-time",
            "Click hunters to issue strategic move orders",
            "Take control — WASD to move, collect treasure!",
        ]

        # ── Difficulty buttons ──
        diffs = [DIFF_EASY, DIFF_NORMAL, DIFF_HARD, DIFF_LEGENDARY]
        self._diff_colors = [C_GREEN, C_UI_TEXT_BRIGHT, C_YELLOW, C_RED]
        self._diff_descs  = [
            "Relaxed — few knights, plentiful treasure",
            "Balanced — the classic experience",
            "Intense — more knights, scarce treasure",
            "Brutal — relentless knights. Survive if you dare!",
        ]
        dw, dh = 280, 56
        dy0 = 258
        self._diff_btns = []
        for i, d in enumerate(diffs):
            dd = d
            self._diff_btns.append(Button(
                pygame.Rect(WINDOW_WIDTH // 2 - dw // 2, dy0 + i * 72, dw, dh),
                DIFFICULTY_SETTINGS[d]["label"],
                callback=lambda x=dd: self._launch(x), font_size=22,
            ))
        self._diff_btns.append(Button(
            pygame.Rect(WINDOW_WIDTH // 2 - 140, dy0 + 4 * 72, 280, 46), "BACK",
            callback=lambda: self._set("mode"),
        ))

    # ------------------------------------------------------------------
    def _go_mode(self):  self._sub = "mode"
    def _pick(self, m):  self._mode = m; self._sub = "difficulty"
    def _set(self, s):   self._sub = s
    def _launch(self, d): self.game.change_state("play", mode=self._mode, difficulty=d)
    def _quit(self):      self.game.running = False

    def _show_achievements(self):
        # Show achievement count toast then stay on menu
        pass   # placeholder — achievements screen can be a future state

    def enter(self, **kw):
        self._sub   = "main"
        self._title_t = 0.0
        self.game.audio.play_music("music_main.ogg")

    def exit(self): pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self._sub != "main":
                self._set("main")
                return
        btns = self._active_btns()
        for b in btns:
            if b.handle_event(event):
                self.game.audio.play("ui_click")
                break

    def update(self, dt):
        self._time      += dt
        self._title_t   += dt
        self._rune_angle = (self._rune_angle + dt * 12.0) % 360
        for s in self._stars:   s.update(dt)
        for e in self._embers:  e.update(dt)
        for p in self._t_parts: p.update(dt)
        for b in self._active_btns():
            b.update(dt)

    def _active_btns(self):
        return (self._main_btns   if self._sub == "main"       else
                self._mode_btns   if self._sub == "mode"       else
                self._diff_btns)

    # ------------------------------------------------------------------
    def draw(self, surface):
        surface.fill(C_BG)

        # Background layers
        for s in self._stars:   s.draw(surface)
        for p in self._t_parts: p.draw(surface)
        for e in self._embers:  e.draw(surface)

        # Sub-menu
        if   self._sub == "main":       self._draw_main(surface)
        elif self._sub == "mode":       self._draw_mode(surface)
        else:                           self._draw_diff(surface)

        # Version tag
        draw_text(surface, f"v{VERSION}",
                  WINDOW_WIDTH - 10, WINDOW_HEIGHT - 22,
                  size=13, color=C_UI_TEXT_DIM, align="right")

    # ------------------------------------------------------------------
    def _draw_rune_circle(self, surface, cx, cy, radius):
        """Slowly rotating decorative rune circle."""
        t   = self._time
        col = (*C_UI_BORDER, 140)
        # Outer ring
        rs = pygame.Surface((radius * 2 + 10, radius * 2 + 10), pygame.SRCALPHA)
        rc = radius + 5
        pygame.draw.circle(rs, (60, 45, 100, 60), (rc, rc), radius, 1)
        # Rune marks
        n_marks = 12
        for i in range(n_marks):
            angle = math.radians(self._rune_angle + i * (360 / n_marks))
            ox = int(rc + radius * math.cos(angle))
            oy = int(rc + radius * math.sin(angle))
            pygame.draw.circle(rs, (80, 60, 140, 80), (ox, oy), 2)
        # Inner dotted ring
        for i in range(24):
            angle = math.radians(-self._rune_angle * 0.5 + i * 15)
            ox = int(rc + (radius * 0.7) * math.cos(angle))
            oy = int(rc + (radius * 0.7) * math.sin(angle))
            a_val = int(50 + 40 * math.sin(i * 1.3 + t))
            pygame.draw.circle(rs, (100, 75, 170, a_val), (ox, oy), 1)
        surface.blit(rs, (cx - rc, cy - rc))

    # ------------------------------------------------------------------
    def _draw_main(self, surface):
        t  = self._time
        cx = WINDOW_WIDTH // 2
        cy = 165

        # Rotating rune circle behind title
        self._draw_rune_circle(surface, cx, cy, 150)

        # ── Title glow corona ──
        glow  = 0.5 + 0.5 * math.sin(t * 1.5)
        alpha = int(190 + 65 * glow)
        gold  = (alpha, int(alpha * 0.82), int(alpha * 0.32))

        for offset, a_mult in [(8, 0.10), (5, 0.18), (2, 0.32)]:
            col = (int(alpha * a_mult), int(alpha * 0.55 * a_mult), 0)
            draw_text(surface, "KNIGHTS", cx, 78 + offset,
                      size=96, color=col, bold=True, align="center")

        draw_text(surface, "KNIGHTS", cx, 78,
                  size=96, color=gold, bold=True, align="center", shadow=True)

        sub_a = int(205 + 50 * math.sin(t * 1.9))
        draw_text(surface, "OF  ELDORIA", cx, 186,
                  size=56, color=(sub_a, int(sub_a * 0.90), int(sub_a * 0.55)),
                  bold=True, align="center", shadow=True)

        # Subtitle
        ta = int(115 + 40 * math.sin(t * 2.4))
        draw_text(surface, "A Dark Fantasy Simulation",
                  cx, 256, size=18,
                  color=(ta, ta, int(ta * 0.55)), align="center")

        self._deco(surface, 302)

        for b in self._main_btns:
            b.draw(surface)

    # ------------------------------------------------------------------
    def _draw_mode(self, surface):
        cx = WINDOW_WIDTH // 2
        draw_text(surface, "SELECT GAME MODE", cx, 162,
                  size=40, color=C_UI_TEXT_BRIGHT, bold=True,
                  align="center", shadow=True)
        self._deco(surface, 214)

        mode_icons = ["  Watch", "  Command", "  Hero"]
        for i, b in enumerate(self._mode_btns[:-1]):
            b.draw(surface)
            if i < len(self._mode_descs):
                draw_text(surface, self._mode_descs[i],
                          b.rect.centerx, b.rect.bottom - 22,
                          size=14, color=C_UI_TEXT_DIM, align="center")

        self._mode_btns[-1].draw(surface)

    # ------------------------------------------------------------------
    def _draw_diff(self, surface):
        cx = WINDOW_WIDTH // 2
        draw_text(surface, "SELECT DIFFICULTY", cx, 162,
                  size=40, color=C_UI_TEXT_BRIGHT, bold=True,
                  align="center", shadow=True)
        mode_lbl = {"watch": "Watch Mode", "command": "Command Mode",
                    "hero": "Hero Mode"}.get(self._mode, self._mode.title())
        draw_text(surface, f"Mode: {mode_lbl}",
                  cx, 214, size=16, color=C_UI_ACCENT, align="center")
        self._deco(surface, 244)

        for i, b in enumerate(self._diff_btns[:-1]):
            b.draw(surface)
            draw_text(surface, self._diff_descs[i],
                      b.rect.centerx, b.rect.bottom - 18,
                      size=13, color=self._diff_colors[i], align="center")

        self._diff_btns[-1].draw(surface)

    # ------------------------------------------------------------------
    def _deco(self, surface, y):
        """Decorative horizontal divider with pulsing gem."""
        cx = WINDOW_WIDTH // 2
        lx1, lx2 = cx - 280, cx - 50
        rx1, rx2 = cx + 50, cx + 280
        pygame.draw.line(surface, C_UI_BORDER,    (lx1, y), (lx2, y), 1)
        pygame.draw.line(surface, C_UI_BORDER,    (rx1, y), (rx2, y), 1)
        pygame.draw.line(surface, C_UI_BORDER_HI, (lx1 + 24, y), (lx2 - 4, y), 1)
        pygame.draw.line(surface, C_UI_BORDER_HI, (rx1 + 4,  y), (rx2 - 24, y), 1)
        pulse = 0.7 + 0.3 * math.sin(self._time * 3.2)
        rg    = int(9 * pulse)
        pygame.draw.circle(surface, C_TREASURE_GOLD, (cx, y), rg)
        pygame.draw.circle(surface, C_UI_BORDER_HI,  (cx, y), rg, 1)
        for off in (-32, 32):
            ocx = cx + off
            pts = [(ocx, y - 5), (ocx + 4, y), (ocx, y + 5), (ocx - 4, y)]
            pygame.draw.polygon(surface, C_UI_BORDER, pts)
