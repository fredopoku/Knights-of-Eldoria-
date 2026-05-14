"""Epic main menu — parallax stars, animated glow title, floating embers."""
from __future__ import annotations
import math
import random
import pygame
from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, VERSION,
    C_BG, C_UI_TEXT, C_UI_TEXT_BRIGHT, C_UI_TEXT_DIM,
    C_UI_BORDER, C_UI_BORDER_HI, C_UI_ACCENT, C_UI_PANEL, C_UI_PANEL_2,
    C_WHITE, C_YELLOW, C_GREEN, C_RED, C_ORANGE,
    C_TREASURE_GOLD, C_HUNTER_NAV, C_KNIGHT, C_HUNTER_HERO,
    MODE_WATCH, MODE_COMMAND, MODE_HERO,
    DIFF_EASY, DIFF_NORMAL, DIFF_HARD, DIFF_LEGENDARY,
    DIFFICULTY_SETTINGS,
)
from src.ui import Button, draw_text, draw_panel, draw_hline


# ---------------------------------------------------------------------------
# Parallax star (3 layers)
# ---------------------------------------------------------------------------
class _Star:
    __slots__ = ("x", "y", "speed", "size", "alpha", "twinkle", "twinkle_s", "layer")

    def __init__(self, layer=0):
        self.layer = layer
        self.reset(random.uniform(0, WINDOW_HEIGHT))

    def reset(self, y=0.0):
        self.x        = random.uniform(0, WINDOW_WIDTH)
        self.y        = float(y)
        self.speed    = (self.layer + 1) * random.uniform(8, 22)
        self.size     = self.layer + 1
        self.alpha    = random.randint(60 + self.layer*40, 150 + self.layer*50)
        self.twinkle  = random.uniform(0, math.tau)
        self.twinkle_s= random.uniform(1.5, 5.0)

    def update(self, dt):
        self.y       += self.speed * dt
        self.twinkle += self.twinkle_s * dt
        if self.y > WINDOW_HEIGHT:
            self.reset()

    def draw(self, surf):
        a = int(self.alpha * (0.6 + 0.4 * math.sin(self.twinkle)))
        c = (a, a, int(a*0.78))
        pygame.draw.circle(surf, c, (int(self.x), int(self.y)), self.size)


# ---------------------------------------------------------------------------
# Floating ember particle
# ---------------------------------------------------------------------------
class _Ember:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color")

    COLORS = [(255,160,40), (255,210,60), (255,120,30), (255,240,100)]

    def __init__(self):
        self.reset()

    def reset(self):
        self.x       = random.uniform(0, WINDOW_WIDTH)
        self.y       = WINDOW_HEIGHT + 8.0
        self.vx      = random.uniform(-18, 18)
        self.vy      = random.uniform(-30, -12)
        self.max_life = random.uniform(3.5, 8.0)
        self.life    = self.max_life
        self.color   = random.choice(self.COLORS)

    def update(self, dt):
        self.x    += self.vx * dt
        self.y    += self.vy * dt
        self.life -= dt
        if self.life <= 0 or self.y < -10:
            self.reset()

    def draw(self, surf):
        t = max(0.0, self.life / self.max_life)
        a = int(200 * t)
        col = tuple(max(0, int(c * t)) for c in self.color)
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), 2)
        # Glow
        glow_c = tuple(max(0, int(c * t * 0.3)) for c in self.color)
        pygame.draw.circle(surf, glow_c, (int(self.x), int(self.y)), 4)


# ---------------------------------------------------------------------------
# Knight silhouette that walks across the bottom
# ---------------------------------------------------------------------------
class _KnightSilhouette:
    def __init__(self):
        self.x    = -80.0
        self.y    = WINDOW_HEIGHT - 90
        self.speed = 28.0

    def update(self, dt):
        self.x += self.speed * dt
        if self.x > WINDOW_WIDTH + 80:
            self.x = -80.0
            self.speed = random.uniform(20, 40)

    def draw(self, surf, t):
        cx, cy = int(self.x), int(self.y)
        bob = int(math.sin(t * 6) * 2)
        cy += bob
        alpha = 80
        c = (80, 20, 20, alpha)
        s = pygame.Surface((60, 80), pygame.SRCALPHA)
        # Body diamond
        pts = [(30,5),(55,30),(30,55),(5,30)]
        pygame.draw.polygon(s, (80,20,20,90), pts)
        pygame.draw.polygon(s, (120,30,30,60), pts, 2)
        surf.blit(s, (cx-30, cy-40))


# ---------------------------------------------------------------------------
# MenuState
# ---------------------------------------------------------------------------
class MenuState:
    def __init__(self, game):
        self.game   = game
        self._time  = 0.0
        self._sub   = "main"
        self._mode  = MODE_WATCH

        # Parallax layers
        self._stars = ([_Star(0) for _ in range(60)] +
                       [_Star(1) for _ in range(40)] +
                       [_Star(2) for _ in range(20)])
        self._embers  = [_Ember()            for _ in range(18)]
        self._knights = [_KnightSilhouette() for _ in range(2)]
        self._knights[1].x = WINDOW_WIDTH * 0.6

        # Title letter reveal
        self._title_t = 0.0

        # Main buttons
        bw, bh = 310, 54
        cx = WINDOW_WIDTH//2 - bw//2
        self._main_btns = [
            Button(pygame.Rect(cx, 322, bw, bh), "PLAY",    callback=self._go_mode, font_size=26),
            Button(pygame.Rect(cx, 388, bw, bh), "TUTORIAL",callback=lambda: self.game.change_state("tutorial")),
            Button(pygame.Rect(cx, 454, bw, bh), "SETTINGS",callback=lambda: self.game.change_state("settings")),
            Button(pygame.Rect(cx, 520, bw, bh), "CREDITS", callback=lambda: self.game.change_state("credits")),
            Button(pygame.Rect(cx, 592, bw, bh), "EXIT",    callback=self._quit, font_size=20),
        ]

        # Mode buttons
        mw, mh = 370, 90
        mx = WINDOW_WIDTH//2 - mw//2
        self._mode_btns = [
            Button(pygame.Rect(mx, 240, mw, mh), "WATCH MODE",
                   callback=lambda: self._pick(MODE_WATCH), font_size=22),
            Button(pygame.Rect(mx, 346, mw, mh), "COMMAND MODE",
                   callback=lambda: self._pick(MODE_COMMAND), font_size=22),
            Button(pygame.Rect(mx, 452, mw, mh), "HERO MODE",
                   callback=lambda: self._pick(MODE_HERO), font_size=22),
            Button(pygame.Rect(mx, 580, 180, 46), "BACK",
                   callback=lambda: self._set("main")),
        ]
        self._mode_descs = [
            "Observe the AI simulation unfold in real-time",
            "Click hunters to issue strategic move orders",
            "Take control — WASD to move, collect treasure!",
        ]

        # Difficulty buttons
        diffs = [DIFF_EASY, DIFF_NORMAL, DIFF_HARD, DIFF_LEGENDARY]
        self._diff_colors = [C_GREEN, C_UI_TEXT_BRIGHT, C_YELLOW, C_RED]
        self._diff_descs  = [
            "Relaxed — few knights, lots of treasure",
            "Balanced — classic experience",
            "Intense — more knights, scarce treasure",
            "Brutal — relentless knights, survive if you dare",
        ]
        dw, dh = 270, 56
        dy0 = 270
        self._diff_btns = []
        for i, d in enumerate(diffs):
            dd = d
            self._diff_btns.append(Button(
                pygame.Rect(WINDOW_WIDTH//2-dw//2, dy0+i*72, dw, dh),
                DIFFICULTY_SETTINGS[d]["label"],
                callback=lambda x=dd: self._launch(x), font_size=22,
            ))
        self._diff_btns.append(Button(
            pygame.Rect(WINDOW_WIDTH//2-135, dy0+4*72, 270, 46), "BACK",
            callback=lambda: self._set("mode"),
        ))

    # ------------------------------------------------------------------
    def _go_mode(self):  self._sub = "mode"
    def _pick(self, m):  self._mode = m; self._sub = "difficulty"
    def _set(self, s):   self._sub = s
    def _launch(self, d):
        self.game.change_state("play", mode=self._mode, difficulty=d)
    def _quit(self):     self.game.running = False

    def enter(self, **kw):
        self._sub   = "main"
        self._title_t = 0.0
        self.game.audio.play_music("music_main.ogg")

    def exit(self): pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self._sub != "main": self._set("main"); return
        btns = self._active_btns()
        for b in btns:
            if b.handle_event(event):
                self.game.audio.play("ui_click"); break

    def update(self, dt):
        self._time    += dt
        self._title_t += dt
        for s in self._stars:   s.update(dt)
        for e in self._embers:  e.update(dt)
        for k in self._knights: k.update(dt)
        for b in self._active_btns(): b.update(dt)

    def _active_btns(self):
        return (self._main_btns if self._sub == "main" else
                self._mode_btns if self._sub == "mode" else
                self._diff_btns)

    # ------------------------------------------------------------------
    def draw(self, surface):
        surface.fill(C_BG)

        for s in self._stars:   s.draw(surface)
        for e in self._embers:  e.draw(surface)
        for k in self._knights: k.draw(surface, self._time)

        if   self._sub == "main":       self._draw_main(surface)
        elif self._sub == "mode":       self._draw_mode(surface)
        else:                           self._draw_diff(surface)

        draw_text(surface, f"v{VERSION}",
                  WINDOW_WIDTH-10, WINDOW_HEIGHT-22,
                  size=13, color=C_UI_TEXT_DIM, align="right")

    # ------------------------------------------------------------------
    def _draw_main(self, surface):
        t = self._time

        # ── Animated glowing title ──
        glow  = 0.5 + 0.5 * math.sin(t * 1.5)
        alpha = int(185 + 70 * glow)
        gold  = (alpha, int(alpha*0.82), int(alpha*0.38))

        # Title glow corona
        for offset, a_mult in [(6, 0.12), (4, 0.2), (2, 0.35)]:
            col = (int(alpha*a_mult), int(alpha*0.6*a_mult), 0)
            draw_text(surface, "KNIGHTS", WINDOW_WIDTH//2, 82+offset,
                      size=100, color=col, bold=True, align="center")

        draw_text(surface, "KNIGHTS", WINDOW_WIDTH//2, 82,
                  size=100, color=gold, bold=True, align="center", shadow=True)

        sub_a = int(200 + 55 * math.sin(t * 1.9))
        draw_text(surface, "OF  ELDORIA", WINDOW_WIDTH//2, 192,
                  size=58, color=(sub_a, int(sub_a*0.92), int(sub_a*0.6)),
                  bold=True, align="center", shadow=True)

        # Subtitle
        ta = int(120 + 40 * math.sin(t * 2.4))
        draw_text(surface, "A Medieval Treasure Hunt",
                  WINDOW_WIDTH//2, 264, size=18,
                  color=(ta, ta, int(ta*0.6)), align="center")

        self._deco(surface, 306)

        for b in self._main_btns:
            b.draw(surface)

    def _draw_mode(self, surface):
        draw_text(surface, "SELECT GAME MODE", WINDOW_WIDTH//2, 172,
                  size=40, color=C_UI_TEXT_BRIGHT, bold=True,
                  align="center", shadow=True)
        self._deco(surface, 224)
        for i, b in enumerate(self._mode_btns):
            b.draw(surface)
            if i < len(self._mode_descs):
                draw_text(surface, self._mode_descs[i],
                          b.rect.centerx, b.rect.bottom-22,
                          size=14, color=C_UI_TEXT_DIM, align="center")

    def _draw_diff(self, surface):
        draw_text(surface, "SELECT DIFFICULTY", WINDOW_WIDTH//2, 172,
                  size=40, color=C_UI_TEXT_BRIGHT, bold=True,
                  align="center", shadow=True)
        mode_lbl = {"watch":"Watch Mode","command":"Command Mode",
                    "hero":"Hero Mode"}.get(self._mode, self._mode.title())
        draw_text(surface, f"Mode: {mode_lbl}",
                  WINDOW_WIDTH//2, 226, size=16, color=C_UI_ACCENT, align="center")
        self._deco(surface, 256)
        for i, b in enumerate(self._diff_btns[:-1]):
            b.draw(surface)
            draw_text(surface, self._diff_descs[i],
                      b.rect.centerx, b.rect.bottom-18,
                      size=13, color=C_UI_TEXT_DIM, align="center")
        self._diff_btns[-1].draw(surface)

    def _deco(self, surface, y):
        lx1 = WINDOW_WIDTH//2 - 270
        lx2 = WINDOW_WIDTH//2 - 46
        rx1 = WINDOW_WIDTH//2 + 46
        rx2 = WINDOW_WIDTH//2 + 270
        pygame.draw.line(surface, C_UI_BORDER, (lx1, y), (lx2, y), 1)
        pygame.draw.line(surface, C_UI_BORDER, (rx1, y), (rx2, y), 1)
        pygame.draw.line(surface, C_UI_BORDER_HI, (lx1+22, y), (lx2-4, y), 1)
        pygame.draw.line(surface, C_UI_BORDER_HI, (rx1+4,  y), (rx2-22, y), 1)
        pulse = 0.7 + 0.3 * math.sin(self._time * 3.2)
        rg = int(8 * pulse)
        pygame.draw.circle(surface, C_TREASURE_GOLD,  (WINDOW_WIDTH//2, y), rg)
        pygame.draw.circle(surface, C_UI_BORDER_HI, (WINDOW_WIDTH//2, y), rg, 1)
        for off in (-28, 28):
            cx = WINDOW_WIDTH//2 + off
            pts = [(cx, y-5),(cx+4, y),(cx, y+5),(cx-4, y)]
            pygame.draw.polygon(surface, C_UI_BORDER, pts)
