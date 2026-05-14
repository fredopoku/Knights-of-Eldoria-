"""Reusable UI widgets — polished, animated, commercial quality."""
from __future__ import annotations
import math
import pygame
from src.constants import (
    C_UI_TEXT, C_UI_TEXT_BRIGHT, C_UI_TEXT_DIM,
    C_UI_PANEL, C_UI_PANEL_2, C_UI_BORDER, C_UI_BORDER_HI,
    C_BTN_NORMAL, C_BTN_HOVER, C_BTN_ACTIVE, C_BTN_BORDER, C_BTN_TEXT,
    C_BAR_BG, C_BAR_BORDER, C_BAR_STAMINA_HI, C_BAR_STAMINA_MID,
    C_BAR_STAMINA_LOW, C_BAR_ENERGY,
    C_GREEN, C_RED, C_YELLOW, C_WHITE, C_BLACK,
)

# ---------------------------------------------------------------------------
# Font cache
# ---------------------------------------------------------------------------
_font_cache: dict[tuple, pygame.font.Font] = {}

def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key not in _font_cache:
        for name in ["Georgia", "Palatino Linotype", "Times New Roman", "Serif"]:
            try:
                f = pygame.font.SysFont(name, size, bold=bold)
                _font_cache[key] = f
                break
            except Exception:
                pass
        if key not in _font_cache:
            _font_cache[key] = pygame.font.Font(None, max(8, size))
    return _font_cache[key]


# ---------------------------------------------------------------------------
# draw_text
# ---------------------------------------------------------------------------
def draw_text(surface, text, x, y, size=20, color=C_UI_TEXT,
              bold=False, align="left", shadow=False, alpha=255):
    font = get_font(size, bold)
    col  = color[:3]
    surf = font.render(text, True, col)
    if alpha < 255:
        surf.set_alpha(alpha)
    rect = surf.get_rect()
    if align == "center":
        rect.midtop = (x, y)
    elif align == "right":
        rect.topright = (x, y)
    else:
        rect.topleft = (x, y)
    if shadow:
        sh = font.render(text, True, (0, 0, 0))
        if alpha < 255:
            sh.set_alpha(alpha // 2)
        surface.blit(sh, rect.move(2, 2))
    surface.blit(surf, rect)
    return rect


def draw_panel(surface, rect, color=C_UI_PANEL, border_color=C_UI_BORDER,
               border_width=2, radius=6):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    pygame.draw.rect(surface, border_color, rect,
                     width=border_width, border_radius=radius)


def draw_hline(surface, x1, x2, y, color=C_UI_BORDER, width=1):
    pygame.draw.line(surface, color, (x1, y), (x2, y), width)


# ---------------------------------------------------------------------------
# Button — animated hover glow
# ---------------------------------------------------------------------------
class Button:
    HEIGHT = 46

    def __init__(self, rect, label, font_size=22, callback=None,
                 color_normal=C_BTN_NORMAL, color_hover=C_BTN_HOVER,
                 color_active=C_BTN_ACTIVE, border_color=C_BTN_BORDER,
                 text_color=C_BTN_TEXT, enabled=True):
        self.rect      = pygame.Rect(rect)
        self.label     = label
        self.font_size = font_size
        self.callback  = callback
        self.c_normal  = color_normal
        self.c_hover   = color_hover
        self.c_active  = color_active
        self.c_border  = border_color
        self.c_text    = text_color
        self.enabled   = enabled
        self._hovered  = False
        self._pressed  = False
        self._anim     = 0.0

    def handle_event(self, event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self._hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._pressed and self.rect.collidepoint(event.pos):
                self._pressed = False
                if self.callback:
                    self.callback()
                return True
            self._pressed = False
        return False

    def update(self, dt: float):
        target = 1.0 if (self._hovered or self._pressed) else 0.0
        self._anim += (target - self._anim) * min(1.0, dt * 14)

    def draw(self, surface):
        t  = self._anim
        def lerp(a, b, t): return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))

        bg = lerp(self.c_normal, self.c_active if self._pressed else self.c_hover, t)
        bc = lerp(self.c_border, C_UI_BORDER_HI, t)

        pygame.draw.rect(surface, bg, self.rect, border_radius=6)

        # Inner highlight strip (top edge)
        hi_strip = pygame.Rect(self.rect.x+3, self.rect.y+2,
                               self.rect.width-6, 2)
        hi_col = lerp((40, 32, 68), (100, 80, 160), t)
        pygame.draw.rect(surface, hi_col, hi_strip, border_radius=2)

        pygame.draw.rect(surface, bc, self.rect, width=2, border_radius=6)

        # Glow behind border on hover
        if t > 0.05:
            glow_r = self.rect.inflate(4, 4)
            glow_s = pygame.Surface((glow_r.width, glow_r.height), pygame.SRCALPHA)
            ga = int(50 * t)
            pygame.draw.rect(glow_s, (*C_UI_BORDER_HI, ga),
                             glow_s.get_rect(), border_radius=8)
            surface.blit(glow_s, glow_r.topleft)

        tc = self.c_text if self.enabled else C_UI_TEXT_DIM
        font = get_font(self.font_size, bold=True)
        ts   = font.render(self.label, True, tc)
        tr   = ts.get_rect(center=self.rect.center)
        if self._pressed:
            tr = tr.move(1, 1)
        surface.blit(ts, tr)


# ---------------------------------------------------------------------------
# ProgressBar
# ---------------------------------------------------------------------------
class ProgressBar:
    def __init__(self, rect, value=1.0, max_value=1.0,
                 color_high=C_BAR_STAMINA_HI,
                 color_mid=C_BAR_STAMINA_MID,
                 color_low=C_BAR_STAMINA_LOW,
                 show_text=False):
        self.rect      = pygame.Rect(rect)
        self.value     = value
        self.max_value = max_value
        self.c_high    = color_high
        self.c_mid     = color_mid
        self.c_low     = color_low
        self.show_text = show_text

    @property
    def fraction(self):
        if self.max_value <= 0:
            return 0.0
        return max(0.0, min(1.0, self.value / self.max_value))

    def draw(self, surface):
        pygame.draw.rect(surface, C_BAR_BG,     self.rect, border_radius=3)
        pygame.draw.rect(surface, C_BAR_BORDER, self.rect, width=1, border_radius=3)
        f = self.fraction
        if f > 0:
            fill = self.rect.inflate(-2, -2)
            fill.width = max(1, int(fill.width * f))
            c = self.c_high if f > 0.6 else self.c_mid if f > 0.3 else self.c_low
            pygame.draw.rect(surface, c, fill, border_radius=2)
            # Shine
            shine = pygame.Rect(fill.x+1, fill.y+1, max(1, fill.width-2), 2)
            shine_c = tuple(min(255, int(v*1.4)) for v in c)
            pygame.draw.rect(surface, shine_c, shine, border_radius=1)
        if self.show_text:
            draw_text(surface, f"{int(self.value)}/{int(self.max_value)}",
                      self.rect.centerx, self.rect.top+1,
                      size=12, color=C_WHITE, align="center")


# ---------------------------------------------------------------------------
# Slider
# ---------------------------------------------------------------------------
class Slider:
    THUMB_R = 9

    def __init__(self, rect, value=0.5, label="", callback=None):
        self.rect      = pygame.Rect(rect)
        self.value     = max(0.0, min(1.0, value))
        self.label     = label
        self.callback  = callback
        self._dragging = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._dragging = True
                self._update(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False
        elif event.type == pygame.MOUSEMOTION and self._dragging:
            self._update(event.pos[0])

    def _update(self, mx):
        x0 = self.rect.left + self.THUMB_R
        x1 = self.rect.right - self.THUMB_R
        self.value = max(0.0, min(1.0, (mx - x0) / max(1, x1-x0)))
        if self.callback:
            self.callback(self.value)

    def draw(self, surface):
        track = pygame.Rect(self.rect.left, self.rect.centery-3, self.rect.width, 6)
        pygame.draw.rect(surface, C_BAR_BG,     track, border_radius=3)
        pygame.draw.rect(surface, C_BAR_BORDER, track, width=1, border_radius=3)
        x0 = self.rect.left + self.THUMB_R
        x1 = self.rect.right - self.THUMB_R
        fx = int(x0 + (x1-x0) * self.value)
        if fx > x0:
            fill = pygame.Rect(x0, track.top, fx-x0, track.height)
            pygame.draw.rect(surface, C_BAR_ENERGY, fill, border_radius=3)
        pygame.draw.circle(surface, C_UI_BORDER_HI, (fx, self.rect.centery), self.THUMB_R)
        pygame.draw.circle(surface, C_WHITE,        (fx, self.rect.centery), self.THUMB_R-4)
        if self.label:
            draw_text(surface, self.label, self.rect.left, self.rect.top-22,
                      size=16, color=C_UI_TEXT)
        draw_text(surface, f"{int(self.value*100)}%",
                  self.rect.right+12, self.rect.centery-9, size=14, color=C_UI_TEXT_DIM)


# ---------------------------------------------------------------------------
# ScrollText  (event log)
# ---------------------------------------------------------------------------
class ScrollText:
    def __init__(self, rect, font_size=14, max_lines=200):
        self.rect      = pygame.Rect(rect)
        self.font_size = font_size
        self.max_lines = max_lines
        self._lines: list[tuple[str, tuple]] = []
        self._scroll   = 0
        self._line_h   = font_size + 4

    def add(self, text: str, color=C_UI_TEXT):
        self._lines.append((text, color))
        if len(self._lines) > self.max_lines:
            self._lines.pop(0)
        self._scroll = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self._scroll = max(0, min(len(self._lines)-1,
                                         self._scroll - event.y))

    def draw(self, surface):
        draw_panel(surface, self.rect, C_UI_PANEL_2, C_UI_BORDER)
        clip = surface.get_clip()
        surface.set_clip(self.rect.inflate(-4, -4))
        visible = self.rect.height // self._line_h
        start   = max(0, len(self._lines) - visible - self._scroll)
        end     = start + visible
        y = self.rect.top + 4
        for text, color in self._lines[start:end]:
            draw_text(surface, text, self.rect.left+6, y,
                      size=self.font_size, color=color)
            y += self._line_h
        surface.set_clip(clip)


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------
class Panel:
    def __init__(self, rect, title="", color=C_UI_PANEL, border_color=C_UI_BORDER):
        self.rect   = pygame.Rect(rect)
        self.title  = title
        self.color  = color
        self.border = border_color

    def draw(self, surface):
        draw_panel(surface, self.rect, self.color, self.border)
        if self.title:
            draw_text(surface, self.title,
                      self.rect.centerx, self.rect.top+8,
                      size=18, color=C_UI_TEXT_BRIGHT, bold=True,
                      align="center", shadow=True)
            draw_hline(surface, self.rect.left+8, self.rect.right-8,
                       self.rect.top+30, C_UI_BORDER)


# ---------------------------------------------------------------------------
# Tooltip
# ---------------------------------------------------------------------------
class Tooltip:
    def __init__(self, text, font_size=14):
        self.text      = text
        self.font_size = font_size
        self._visible  = False
        self._pos      = (0, 0)

    def show(self, pos): self._visible = True;  self._pos = pos
    def hide(self):      self._visible = False

    def draw(self, surface):
        if not self._visible or not self.text:
            return
        font = get_font(self.font_size)
        ts   = font.render(self.text, True, C_UI_TEXT_BRIGHT)
        pad  = 6
        rect = ts.get_rect()
        rect.inflate_ip(pad*2, pad*2)
        rect.topleft = (self._pos[0]+14, self._pos[1]+14)
        rect.right   = min(rect.right,  surface.get_width()-4)
        rect.bottom  = min(rect.bottom, surface.get_height()-4)
        draw_panel(surface, rect, (20, 14, 8), C_UI_BORDER_HI)
        surface.blit(ts, (rect.left+pad, rect.top+pad))


# ---------------------------------------------------------------------------
# MessageBox
# ---------------------------------------------------------------------------
class MessageBox:
    def __init__(self, title, message, buttons, callback=None,
                 width=420, height=210):
        sw, sh = pygame.display.get_surface().get_size()
        self.rect     = pygame.Rect((sw-width)//2, (sh-height)//2, width, height)
        self.title    = title
        self.message  = message
        self.callback = callback
        self._buttons = []
        bw = (width - 40 - (len(buttons)-1)*12) // len(buttons)
        bx = self.rect.left + 20
        by = self.rect.bottom - 54
        for i, lbl in enumerate(buttons):
            r = pygame.Rect(bx, by, bw, 40)
            def make(n=i): return lambda: self._on(n)
            self._buttons.append(Button(r, lbl, callback=make()))
            bx += bw + 12

    def _on(self, idx):
        if self.callback:
            self.callback(idx)

    def handle_event(self, event):
        for b in self._buttons:
            b.handle_event(event)

    def update(self, dt):
        for b in self._buttons:
            b.update(dt)

    def draw(self, surface):
        ov = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 150))
        surface.blit(ov, (0, 0))
        draw_panel(surface, self.rect, C_UI_PANEL, C_UI_BORDER_HI, border_width=2)
        draw_text(surface, self.title, self.rect.centerx, self.rect.top+12,
                  size=22, color=C_UI_TEXT_BRIGHT, bold=True, align="center")
        draw_hline(surface, self.rect.left+8, self.rect.right-8, self.rect.top+40)
        font = get_font(16)
        words = self.message.split()
        line, lines = "", []
        for w in words:
            test = (line+" "+w).strip()
            if font.size(test)[0] > self.rect.width-30:
                lines.append(line); line = w
            else:
                line = test
        if line:
            lines.append(line)
        y = self.rect.top + 52
        for ln in lines:
            draw_text(surface, ln, self.rect.centerx, y,
                      size=16, color=C_UI_TEXT, align="center")
            y += 22
        for b in self._buttons:
            b.draw(surface)
