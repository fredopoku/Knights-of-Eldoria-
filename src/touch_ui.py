"""
Virtual gamepad overlay — drawn over the game on web/mobile.
D-pad (bottom-left) + ability buttons (bottom-right of map area).
Touch/finger events are already converted to mouse events by Pygbag,
so we only need to respond to MOUSEBUTTONDOWN/UP.
"""
from __future__ import annotations
import math
import pygame
from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, HUD_WIDTH,
    C_UI_BORDER, C_UI_BORDER_HI, C_UI_PANEL,
    C_ABILITY_DASH, C_ABILITY_CLOAK, C_ABILITY_RALLY,
    C_GREEN, C_RED, C_YELLOW, C_WHITE, C_UI_TEXT_DIM,
)


# ---------------------------------------------------------------------------
class _DpadButton:
    """One directional button of the D-pad."""
    __slots__ = ("rect", "key", "label", "_pressed")

    def __init__(self, rect: pygame.Rect, key: int, label: str):
        self.rect     = rect
        self.key      = key
        self.label    = label
        self._pressed = False

    @property
    def pressed(self): return self._pressed

    def hit(self, pos) -> bool:
        return self.rect.collidepoint(pos)

    def draw(self, surface: pygame.Surface):
        bg  = (55, 45, 95) if self._pressed else (22, 18, 46)
        bdr = (130, 110, 200) if self._pressed else (60, 50, 110)
        pygame.draw.rect(surface, bg,  self.rect, border_radius=8)
        pygame.draw.rect(surface, bdr, self.rect, width=2, border_radius=8)
        cx, cy = self.rect.centerx, self.rect.centery
        font = pygame.font.Font(None, 26)
        ts   = font.render(self.label, True, (200, 190, 230) if not self._pressed else (255, 255, 255))
        surface.blit(ts, ts.get_rect(center=(cx, cy)))


# ---------------------------------------------------------------------------
class _AbilityButton:
    """One ability button (Q / E / R)."""
    __slots__ = ("rect", "key", "name", "key_label", "color", "_pressed")

    def __init__(self, rect: pygame.Rect, key: int,
                 name: str, key_label: str, color: tuple):
        self.rect      = rect
        self.key       = key
        self.name      = name
        self.key_label = key_label
        self.color     = color
        self._pressed  = False

    @property
    def pressed(self): return self._pressed

    def hit(self, pos) -> bool:
        return self.rect.collidepoint(pos)

    def draw(self, surface: pygame.Surface, cooldown_pct: float = 0.0):
        ready = cooldown_pct <= 0
        col   = self.color
        dim   = tuple(c // 3 for c in col)
        bg    = (28, 22, 56) if ready else (12, 9, 26)

        pygame.draw.rect(surface, bg,  self.rect, border_radius=10)
        pygame.draw.rect(surface, col if ready else dim,
                         self.rect, width=2, border_radius=10)

        if not ready:
            ov = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            ov.fill((0, 0, 0, int(160 * cooldown_pct)))
            surface.blit(ov, self.rect.topleft)

        font_big = pygame.font.Font(None, 32)
        font_sm  = pygame.font.Font(None, 19)

        if ready:
            ts = font_big.render(self.key_label, True, col)
        else:
            ts = font_big.render(self.key_label, True, dim)
        surface.blit(ts, ts.get_rect(center=(self.rect.centerx, self.rect.centery - 8)))

        name_surf = font_sm.render(self.name, True, col if ready else dim)
        surface.blit(name_surf,
                     name_surf.get_rect(center=(self.rect.centerx,
                                                self.rect.bottom - 12)))


# ---------------------------------------------------------------------------
class TouchGamepad:
    """
    Full virtual gamepad. Call `handle_mouse_event()` on every pygame event,
    then inject the returned synthetic events back into the event queue, and
    call `draw()` at the end of each frame.
    """
    _BTN_W   = 52
    _BTN_H   = 48
    _AB_W    = 74
    _AB_H    = 62

    def __init__(self):
        map_w = WINDOW_WIDTH - HUD_WIDTH
        bw, bh = self._BTN_W, self._BTN_H
        pad = 10

        # ── D-pad layout ──────────────────────────────────────────────
        # Centre anchor of the cross
        cx = pad + bw + bw // 2
        cy = WINDOW_HEIGHT - bh - pad

        self._dpad: list[_DpadButton] = [
            _DpadButton(pygame.Rect(cx - bw // 2, cy - bh - 4, bw, bh),
                        pygame.K_UP,    "▲"),
            _DpadButton(pygame.Rect(cx - bw // 2, cy + 4, bw, bh),
                        pygame.K_DOWN,  "▼"),
            _DpadButton(pygame.Rect(cx - bw - 4,  cy - bh // 2, bw, bh),
                        pygame.K_LEFT,  "◀"),
            _DpadButton(pygame.Rect(cx + 4,        cy - bh // 2, bw, bh),
                        pygame.K_RIGHT, "▶"),
        ]

        # ── Ability buttons ───────────────────────────────────────────
        aw, ah = self._AB_W, self._AB_H
        ay = WINDOW_HEIGHT - ah - pad
        # Sit to the right of the D-pad, centred in the remaining space
        ab_start = cx + bw + 4 + 20
        ab_gap   = 6
        ab_colors = [C_ABILITY_DASH, C_ABILITY_CLOAK, C_ABILITY_RALLY]
        ab_keys   = [pygame.K_q,     pygame.K_e,      pygame.K_r]
        ab_names  = ["DASH",         "CLOAK",          "RALLY"]
        ab_labels = ["Q",            "E",              "R"]

        self._ability_btns: list[_AbilityButton] = [
            _AbilityButton(
                pygame.Rect(ab_start + i * (aw + ab_gap), ay, aw, ah),
                ab_keys[i], ab_names[i], ab_labels[i], ab_colors[i],
            )
            for i in range(3)
        ]

        # ── Pause button (top-right of map) ───────────────────────────
        self._pause_rect = pygame.Rect(map_w - 52, 8, 44, 30)

        # Track which buttons are currently held
        self._held: set[int] = set()   # pygame key codes currently pressed

    # ------------------------------------------------------------------
    def handle_mouse_event(self, event: pygame.event.Event
                           ) -> list[pygame.event.Event]:
        """Returns synthetic KEYDOWN / KEYUP events generated by touch."""
        out: list[pygame.event.Event] = []
        if event.type not in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            return out

        pos     = event.pos
        pressed = (event.type == pygame.MOUSEBUTTONDOWN)

        all_btns: list[_DpadButton | _AbilityButton] = [
            *self._dpad, *self._ability_btns
        ]

        for btn in all_btns:
            if not btn.hit(pos):
                continue
            k = btn.key
            if pressed and k not in self._held:
                self._held.add(k)
                btn._pressed = True
                out.append(pygame.event.Event(
                    pygame.KEYDOWN,
                    {'key': k, 'mod': 0, 'unicode': '', 'scancode': 0}
                ))
            elif not pressed and k in self._held:
                self._held.discard(k)
                btn._pressed = False
                out.append(pygame.event.Event(
                    pygame.KEYUP,
                    {'key': k, 'mod': 0, 'unicode': ''}
                ))

        # Pause button
        if self._pause_rect.collidepoint(pos) and pressed:
            out.append(pygame.event.Event(
                pygame.KEYDOWN,
                {'key': pygame.K_ESCAPE, 'mod': 0, 'unicode': '', 'scancode': 0}
            ))

        return out

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface,
             abilities: list[dict] | None = None):
        """
        Draw the full virtual gamepad.
        abilities: list of ability dicts with 'timer' and 'cooldown' keys.
        """
        map_w = WINDOW_WIDTH - HUD_WIDTH

        # Translucent strip at the bottom of the map area
        strip_h = self._BTN_H + self._AB_H + 28
        strip   = pygame.Surface((map_w, strip_h), pygame.SRCALPHA)
        strip.fill((6, 4, 16, 185))
        pygame.draw.line(strip, (50, 40, 90, 200), (0, 0), (map_w, 0), 1)
        surface.blit(strip, (0, WINDOW_HEIGHT - strip_h))

        # D-pad
        for btn in self._dpad:
            btn.draw(surface)

        # Ability buttons
        for i, btn in enumerate(self._ability_btns):
            pct = 0.0
            if abilities and i < len(abilities):
                ab  = abilities[i]
                pct = ab['timer'] / max(1e-3, ab['cooldown']) if ab['timer'] > 0 else 0.0
            btn.draw(surface, cooldown_pct=pct)

        # Pause button
        pygame.draw.rect(surface, (22, 18, 44), self._pause_rect, border_radius=6)
        pygame.draw.rect(surface, C_UI_BORDER,  self._pause_rect, width=1, border_radius=6)
        font = pygame.font.Font(None, 18)
        ts   = font.render("II  MENU", True, (160, 150, 200))
        surface.blit(ts, ts.get_rect(center=self._pause_rect.center))
