"""Settings screen: volume sliders, toggles, display options including
weather and day/night cycle controls."""
from __future__ import annotations
import math
import pygame
from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    C_BG, C_UI_TEXT, C_UI_TEXT_BRIGHT, C_UI_TEXT_DIM,
    C_UI_PANEL, C_UI_BORDER, C_UI_BORDER_HI, C_UI_ACCENT,
    C_GREEN, C_RED, C_YELLOW,
    C_TREASURE_GOLD,
)
from src.ui import Button, Slider, draw_text, draw_panel, draw_hline


class SettingsState:
    def __init__(self, game):
        self.game       = game
        self._return_to = "menu"
        self._time      = 0.0

        cx   = WINDOW_WIDTH // 2
        sx   = cx - 110
        sw   = 260

        # ── Audio Sliders ──
        self._sfx_slider = Slider(
            pygame.Rect(sx, 196, sw, 20), label="SFX Volume",
            callback=self._on_sfx
        )
        self._music_slider = Slider(
            pygame.Rect(sx, 262, sw, 20), label="Music Volume",
            callback=self._on_music
        )

        # ── Toggle buttons (two columns) ──
        bw, bh = 200, 42
        col1_x = cx - bw - 10
        col2_x = cx + 10
        row1_y = 314
        row2_y = 368
        row3_y = 422

        self._sfx_btn = Button(
            pygame.Rect(col1_x, row1_y, bw, bh), "SFX: ON",
            callback=self._toggle_sfx, font_size=17)

        self._music_btn = Button(
            pygame.Rect(col2_x, row1_y, bw, bh), "MUSIC: ON",
            callback=self._toggle_music, font_size=17)

        self._particles_btn = Button(
            pygame.Rect(col1_x, row2_y, bw, bh), "PARTICLES: ON",
            callback=self._toggle_particles, font_size=17)

        self._weather_btn = Button(
            pygame.Rect(col2_x, row2_y, bw, bh), "WEATHER: ON",
            callback=self._toggle_weather, font_size=17)

        self._daynight_btn = Button(
            pygame.Rect(col1_x, row3_y, bw, bh), "DAY/NIGHT: ON",
            callback=self._toggle_daynight, font_size=17)

        self._back_btn = Button(
            pygame.Rect(cx - 100, 506, 200, 46), "← BACK",
            callback=self._back, font_size=20)

        self._buttons = [
            self._sfx_btn, self._music_btn,
            self._particles_btn, self._weather_btn,
            self._daynight_btn, self._back_btn,
        ]
        self._sliders = [self._sfx_slider, self._music_slider]

    # ------------------------------------------------------------------
    def _on_sfx(self, val: float):
        self.game.audio.sfx_vol       = val
        self.game.settings["sfx_vol"] = val

    def _on_music(self, val: float):
        self.game.audio.music_vol       = val
        self.game.settings["music_vol"] = val

    def _toggle_sfx(self):
        v = not self.game.settings["sfx_on"]
        self.game.settings["sfx_on"] = v
        self.game.audio.sfx_on       = v
        self._sfx_btn.label          = f"SFX: {'ON' if v else 'OFF'}"

    def _toggle_music(self):
        v = not self.game.settings["music_on"]
        self.game.settings["music_on"] = v
        self.game.audio.music_on       = v
        self._music_btn.label          = f"MUSIC: {'ON' if v else 'OFF'}"

    def _toggle_particles(self):
        v = not self.game.settings["particle_fx"]
        self.game.settings["particle_fx"] = v
        self._particles_btn.label          = f"PARTICLES: {'ON' if v else 'OFF'}"

    def _toggle_weather(self):
        v = not self.game.settings.get("weather_fx", True)
        self.game.settings["weather_fx"] = v
        self._weather_btn.label           = f"WEATHER: {'ON' if v else 'OFF'}"

    def _toggle_daynight(self):
        v = not self.game.settings.get("daynight_fx", True)
        self.game.settings["daynight_fx"] = v
        self._daynight_btn.label           = f"DAY/NIGHT: {'ON' if v else 'OFF'}"

    def _back(self):
        self.game.settings.save()
        if self._return_to == "play":
            self.game.change_state("play", _resume=True)
        else:
            self.game.change_state(self._return_to)

    # ------------------------------------------------------------------
    def enter(self, return_to: str = "menu", **kwargs):
        self._return_to = return_to
        s = self.game.settings
        self._sfx_slider.value   = s["sfx_vol"]
        self._music_slider.value = s["music_vol"]
        self._sfx_btn.label      = f"SFX: {'ON' if s['sfx_on'] else 'OFF'}"
        self._music_btn.label    = f"MUSIC: {'ON' if s['music_on'] else 'OFF'}"
        self._particles_btn.label = f"PARTICLES: {'ON' if s['particle_fx'] else 'OFF'}"
        self._weather_btn.label  = f"WEATHER: {'ON' if s.get('weather_fx', True) else 'OFF'}"
        self._daynight_btn.label = f"DAY/NIGHT: {'ON' if s.get('daynight_fx', True) else 'OFF'}"

    def exit(self):
        self.game.settings.save()

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._back()
            return
        for sl in self._sliders:
            sl.handle_event(event)
        for b in self._buttons:
            if b.handle_event(event):
                self.game.audio.play("ui_click")
                break

    def update(self, dt: float):
        self._time += dt
        for b in self._buttons:
            b.update(dt)

    def draw(self, surface: pygame.Surface):
        surface.fill(C_BG)

        cx = WINDOW_WIDTH // 2
        t  = self._time

        # Animated title
        glow  = 0.5 + 0.5 * math.sin(t * 1.8)
        alpha = int(210 + 45 * glow)
        draw_text(surface, "SETTINGS",
                  cx, 52, size=52,
                  color=(alpha, int(alpha * 0.90), int(alpha * 0.55)),
                  bold=True, align="center", shadow=True)

        # Decorative divider
        pygame.draw.line(surface, C_UI_BORDER,
                         (cx - 220, 122), (cx - 50, 122), 1)
        pygame.draw.line(surface, C_UI_BORDER,
                         (cx + 50, 122), (cx + 220, 122), 1)
        pygame.draw.circle(surface, C_TREASURE_GOLD, (cx, 122), 6)

        # Section headers
        draw_text(surface, "AUDIO", cx - 110, 158, size=13,
                  color=C_UI_TEXT_DIM, bold=True)
        draw_text(surface, "DISPLAY & EFFECTS", cx - 110, 296, size=13,
                  color=C_UI_TEXT_DIM, bold=True)

        # Section panel outlines
        audio_rect = pygame.Rect(cx - 180, 175, 360, 122)
        draw_panel(surface, audio_rect, (16, 12, 32), C_UI_BORDER, border_width=1)

        fx_rect = pygame.Rect(cx - 215, 306, 430, 130)
        draw_panel(surface, fx_rect, (16, 12, 32), C_UI_BORDER, border_width=1)

        for sl in self._sliders:
            sl.draw(surface)
        for b in self._buttons:
            b.draw(surface)

        draw_text(surface, "Press ESC to go back",
                  cx, 570, size=14,
                  color=C_UI_TEXT_DIM, align="center")
