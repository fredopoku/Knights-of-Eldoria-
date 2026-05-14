"""
Reusable UI widgets for Knights of Eldoria.
All widgets operate in screen-space pixel coordinates.
"""
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
        candidates = ["Palatino Linotype", "Georgia", "Times New Roman",
                      "Serif", "FreeSans"]
        font = None
        for name in candidates:
            try:
                font = pygame.font.SysFont(name, size, bold=bold)
                break
            except Exception:
                pass
        if font is None:
            font = pygame.font.Font(None, size)
        _font_cache[key] = font
    return _font_cache[key]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def draw_text(surface: pygame.Surface, text: str, x: int, y: int,
              size: int = 20, color=C_UI_TEXT, bold: bool = False,
              align: str = "left", shadow: bool = False) -> pygame.Rect:
    font = get_font(size, bold)
    surf = font.render(text, True, color)
    rect = surf.get_rect()
    if align == "center":
        rect.midtop = (x, y)
    elif align == "right":
        rect.topright = (x, y)
    else:
        rect.topleft = (x, y)
    if shadow:
        sh = font.render(text, True, (0, 0, 0))
        surface.blit(sh, rect.move(2, 2))
    surface.blit(surf, rect)
    return rect


def draw_panel(surface: pygame.Surface, rect: pygame.Rect,
               color=C_UI_PANEL, border_color=C_UI_BORDER,
               border_width: int = 2, radius: int = 6):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    pygame.draw.rect(surface, border_color, rect,
                     width=border_width, border_radius=radius)


def draw_hline(surface: pygame.Surface, x1: int, x2: int, y: int,
               color=C_UI_BORDER, width: int = 1):
    pygame.draw.line(surface, color, (x1, y), (x2, y), width)


# ---------------------------------------------------------------------------
# Button
# ---------------------------------------------------------------------------
class Button:
    """Rectangular button with hover / active animation."""

    HEIGHT = 44

    def __init__(self, rect: pygame.Rect, label: str,
                 font_size: int = 22, callback=None,
                 color_normal=C_BTN_NORMAL,
                 color_hover=C_BTN_HOVER,
                 color_active=C_BTN_ACTIVE,
                 border_color=C_BTN_BORDER,
                 text_color=C_BTN_TEXT,
                 enabled: bool = True):
        self.rect         = pygame.Rect(rect)
        self.label        = label
        self.font_size    = font_size
        self.callback     = callback
        self.c_normal     = color_normal
        self.c_hover      = color_hover
        self.c_active     = color_active
        self.c_border     = border_color
        self.c_text       = text_color
        self.enabled      = enabled
        self._hovered     = False
        self._pressed     = False
        self._anim        = 0.0     # 0..1 hover blend

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Returns True if the button was clicked."""
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
        self._anim += (target - self._anim) * min(1.0, dt * 12)

    def draw(self, surface: pygame.Surface):
        t = self._anim
        def lerp_col(a, b, t):
            return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

        bg = lerp_col(self.c_normal,
                      self.c_active if self._pressed else self.c_hover, t)
        bc = lerp_col(self.c_border, (215, 165, 55), t)

        pygame.draw.rect(surface, bg,   self.rect, border_radius=5)
        pygame.draw.rect(surface, bc,   self.rect, width=2, border_radius=5)

        alpha = 200 if not self.enabled else 255
        col = (*self.c_text, alpha) if self.enabled else (*C_UI_TEXT_DIM, 160)
        font = get_font(self.font_size, bold=True)
        ts = font.render(self.label, True, self.c_text if self.enabled
                         else C_UI_TEXT_DIM)
        tr = ts.get_rect(center=self.rect.center)
        if self._pressed:
            tr = tr.move(1, 1)
        surface.blit(ts, tr)


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------
class Panel:
    def __init__(self, rect: pygame.Rect, title: str = "",
                 color=C_UI_PANEL, border_color=C_UI_BORDER):
        self.rect   = pygame.Rect(rect)
        self.title  = title
        self.color  = color
        self.border = border_color

    def draw(self, surface: pygame.Surface):
        draw_panel(surface, self.rect, self.color, self.border)
        if self.title:
            draw_text(surface, self.title,
                      self.rect.centerx, self.rect.top + 8,
                      size=18, color=C_UI_TEXT_BRIGHT, bold=True,
                      align="center", shadow=True)
            draw_hline(surface, self.rect.left + 8,
                       self.rect.right - 8, self.rect.top + 30,
                       color=C_UI_BORDER)


# ---------------------------------------------------------------------------
# ProgressBar
# ---------------------------------------------------------------------------
class ProgressBar:
    def __init__(self, rect: pygame.Rect, value: float = 1.0,
                 max_value: float = 1.0,
                 color_high=C_BAR_STAMINA_HI,
                 color_mid=C_BAR_STAMINA_MID,
                 color_low=C_BAR_STAMINA_LOW,
                 show_text: bool = False):
        self.rect       = pygame.Rect(rect)
        self.value      = value
        self.max_value  = max_value
        self.c_high     = color_high
        self.c_mid      = color_mid
        self.c_low      = color_low
        self.show_text  = show_text

    @property
    def fraction(self) -> float:
        if self.max_value <= 0:
            return 0.0
        return max(0.0, min(1.0, self.value / self.max_value))

    def draw(self, surface: pygame.Surface):
        pygame.draw.rect(surface, C_BAR_BG,    self.rect, border_radius=3)
        pygame.draw.rect(surface, C_BAR_BORDER, self.rect,
                         width=1, border_radius=3)
        f = self.fraction
        if f > 0:
            fill = self.rect.inflate(-2, -2)
            fill.width = max(1, int(fill.width * f))
            c = (self.c_high if f > 0.6 else
                 self.c_mid  if f > 0.3 else self.c_low)
            pygame.draw.rect(surface, c, fill, border_radius=2)
        if self.show_text:
            txt = f"{int(self.value)}/{int(self.max_value)}"
            draw_text(surface, txt,
                      self.rect.centerx, self.rect.top + 1,
                      size=12, color=C_WHITE, align="center")


# ---------------------------------------------------------------------------
# Slider
# ---------------------------------------------------------------------------
class Slider:
    """Horizontal slider 0.0 → 1.0."""

    THUMB_R = 8

    def __init__(self, rect: pygame.Rect, value: float = 0.5,
                 label: str = "", callback=None):
        self.rect      = pygame.Rect(rect)
        self.value     = max(0.0, min(1.0, value))
        self.label     = label
        self.callback  = callback
        self._dragging = False

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._dragging = True
                self._update_from_mouse(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False
        elif event.type == pygame.MOUSEMOTION and self._dragging:
            self._update_from_mouse(event.pos[0])

    def _update_from_mouse(self, mx: int):
        x0, x1 = self.rect.left + self.THUMB_R, self.rect.right - self.THUMB_R
        self.value = max(0.0, min(1.0, (mx - x0) / max(1, x1 - x0)))
        if self.callback:
            self.callback(self.value)

    def draw(self, surface: pygame.Surface):
        # Track
        track = pygame.Rect(self.rect.left, self.rect.centery - 3,
                            self.rect.width, 6)
        pygame.draw.rect(surface, C_BAR_BG,     track, border_radius=3)
        pygame.draw.rect(surface, C_BAR_BORDER, track,
                         width=1, border_radius=3)
        # Fill
        x0 = self.rect.left + self.THUMB_R
        x1 = self.rect.right - self.THUMB_R
        fx = int(x0 + (x1 - x0) * self.value)
        if fx > x0:
            fill = pygame.Rect(x0, track.top, fx - x0, track.height)
            pygame.draw.rect(surface, C_BAR_ENERGY, fill, border_radius=3)
        # Thumb
        pygame.draw.circle(surface, C_UI_BORDER_HI, (fx, self.rect.centery),
                           self.THUMB_R)
        pygame.draw.circle(surface, C_WHITE, (fx, self.rect.centery),
                           self.THUMB_R - 3)
        # Label
        if self.label:
            draw_text(surface, self.label,
                      self.rect.left, self.rect.top - 20,
                      size=16, color=C_UI_TEXT)
        pct = f"{int(self.value * 100)}%"
        draw_text(surface, pct,
                  self.rect.right + 10, self.rect.centery - 8,
                  size=14, color=C_UI_TEXT_DIM)


# ---------------------------------------------------------------------------
# ScrollText  (event log / story text)
# ---------------------------------------------------------------------------
class ScrollText:
    def __init__(self, rect: pygame.Rect, font_size: int = 14,
                 max_lines: int = 200):
        self.rect      = pygame.Rect(rect)
        self.font_size = font_size
        self.max_lines = max_lines
        self._lines: list[tuple[str, tuple]] = []   # (text, color)
        self._scroll   = 0      # lines from bottom visible
        self._line_h   = font_size + 4

    def add(self, text: str, color=C_UI_TEXT):
        self._lines.append((text, color))
        if len(self._lines) > self.max_lines:
            self._lines.pop(0)
        self._scroll = 0

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self._scroll = max(0, min(
                    len(self._lines) - 1,
                    self._scroll - event.y))

    def draw(self, surface: pygame.Surface):
        draw_panel(surface, self.rect, C_UI_PANEL_2, C_UI_BORDER)
        clip = surface.get_clip()
        surface.set_clip(self.rect.inflate(-4, -4))

        visible = self.rect.height // self._line_h
        start   = max(0, len(self._lines) - visible - self._scroll)
        end     = start + visible

        y = self.rect.top + 4
        for text, color in self._lines[start:end]:
            draw_text(surface, text, self.rect.left + 6, y,
                      size=self.font_size, color=color)
            y += self._line_h

        surface.set_clip(clip)


# ---------------------------------------------------------------------------
# Tooltip
# ---------------------------------------------------------------------------
class Tooltip:
    def __init__(self, text: str, font_size: int = 14):
        self.text     = text
        self.font_size = font_size
        self._visible = False
        self._pos     = (0, 0)

    def show(self, pos):
        self._visible = True
        self._pos     = pos

    def hide(self):
        self._visible = False

    def draw(self, surface: pygame.Surface):
        if not self._visible or not self.text:
            return
        font = get_font(self.font_size)
        ts   = font.render(self.text, True, C_UI_TEXT_BRIGHT)
        pad  = 6
        rect = ts.get_rect()
        rect.inflate_ip(pad * 2, pad * 2)
        rect.topleft = (self._pos[0] + 12, self._pos[1] + 12)
        # Keep on screen
        rect.right  = min(rect.right,  surface.get_width()  - 4)
        rect.bottom = min(rect.bottom, surface.get_height() - 4)
        draw_panel(surface, rect, (20, 14, 6), C_UI_BORDER_HI)
        surface.blit(ts, (rect.left + pad, rect.top + pad))


# ---------------------------------------------------------------------------
# MessageBox  (modal dialog)
# ---------------------------------------------------------------------------
class MessageBox:
    def __init__(self, title: str, message: str, buttons: list[str],
                 callback=None, width: int = 400, height: int = 200):
        sw, sh = pygame.display.get_surface().get_size()
        self.rect = pygame.Rect((sw - width) // 2, (sh - height) // 2,
                                width, height)
        self.title    = title
        self.message  = message
        self.callback = callback
        self._buttons: list[Button] = []
        bw = (width - 40 - (len(buttons) - 1) * 12) // len(buttons)
        bx = self.rect.left + 20
        by = self.rect.bottom - 52
        for i, lbl in enumerate(buttons):
            idx = i
            r = pygame.Rect(bx, by, bw, 38)
            def make_cb(n=idx): return lambda: self._on_btn(n)
            self._buttons.append(Button(r, lbl, callback=make_cb()))
            bx += bw + 12

    def _on_btn(self, idx: int):
        if self.callback:
            self.callback(idx)

    def handle_event(self, event: pygame.event.Event):
        for b in self._buttons:
            b.handle_event(event)

    def update(self, dt: float):
        for b in self._buttons:
            b.update(dt)

    def draw(self, surface: pygame.Surface):
        # Dim overlay
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))
        draw_panel(surface, self.rect, C_UI_PANEL, C_UI_BORDER_HI, border_width=2)
        draw_text(surface, self.title,
                  self.rect.centerx, self.rect.top + 12,
                  size=22, color=C_UI_TEXT_BRIGHT, bold=True, align="center")
        draw_hline(surface, self.rect.left + 8, self.rect.right - 8,
                   self.rect.top + 38)
        # Wrap message
        font = get_font(16)
        words = self.message.split()
        line, lines = "", []
        for w in words:
            test = (line + " " + w).strip()
            if font.size(test)[0] > self.rect.width - 30:
                lines.append(line)
                line = w
            else:
                line = test
        if line:
            lines.append(line)
        y = self.rect.top + 50
        for ln in lines:
            draw_text(surface, ln, self.rect.centerx, y,
                      size=16, color=C_UI_TEXT, align="center")
            y += 22
        for b in self._buttons:
            b.draw(surface)
