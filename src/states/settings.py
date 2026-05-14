"""Settings screen: volume sliders, toggles, display options."""
from __future__ import annotations
import pygame
from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    C_BG, C_UI_TEXT, C_UI_TEXT_BRIGHT, C_UI_TEXT_DIM,
    C_UI_PANEL, C_UI_BORDER, C_UI_BORDER_HI,
    C_GREEN, C_RED,
)
from src.ui import Button, Slider, draw_text, draw_panel, draw_hline


class SettingsState:
    def __init__(self, game):
        self.game       = game
        self._return_to = "menu"

        cx   = WINDOW_WIDTH // 2
        lx   = cx - 250
        sx   = cx - 80
        sw   = 250

        # Sliders
        self._sfx_slider = Slider(
            pygame.Rect(sx, 200, sw, 20), label="SFX Volume",
            callback=self._on_sfx
        )
        self._music_slider = Slider(
            pygame.Rect(sx, 270, sw, 20), label="Music Volume",
            callback=self._on_music
        )

        # Toggle buttons
        bw, bh = 180, 40
        self._sfx_btn = Button(pygame.Rect(cx - bw//2, 320, bw, bh),
                               "SFX: ON", callback=self._toggle_sfx, font_size=18)
        self._music_btn = Button(pygame.Rect(cx - bw//2, 376, bw, bh),
                                 "MUSIC: ON", callback=self._toggle_music, font_size=18)
        self._particles_btn = Button(pygame.Rect(cx - bw//2, 432, bw, bh),
                                     "PARTICLES: ON",
                                     callback=self._toggle_particles, font_size=18)

        self._back_btn = Button(pygame.Rect(cx - 90, 520, 180, 44), "← BACK",
                                callback=self._back, font_size=20)

        self._buttons  = [self._sfx_btn, self._music_btn,
                          self._particles_btn, self._back_btn]
        self._sliders  = [self._sfx_slider, self._music_slider]

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def _on_sfx(self, val: float):
        self.game.audio.sfx_vol = val
        self.game.settings["sfx_vol"] = val

    def _on_music(self, val: float):
        self.game.audio.music_vol = val
        self.game.settings["music_vol"] = val

    def _toggle_sfx(self):
        v = not self.game.settings["sfx_on"]
        self.game.settings["sfx_on"] = v
        self.game.audio.sfx_on = v
        self._sfx_btn.label = f"SFX: {'ON' if v else 'OFF'}"

    def _toggle_music(self):
        v = not self.game.settings["music_on"]
        self.game.settings["music_on"] = v
        self.game.audio.music_on = v
        self._music_btn.label = f"MUSIC: {'ON' if v else 'OFF'}"

    def _toggle_particles(self):
        v = not self.game.settings["particle_fx"]
        self.game.settings["particle_fx"] = v
        self._particles_btn.label = f"PARTICLES: {'ON' if v else 'OFF'}"

    def _back(self):
        self.game.settings.save()
        if self._return_to == "play":
            self.game.change_state("play", _resume=True)
        else:
            self.game.change_state(self._return_to)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def enter(self, return_to: str = "menu", **kwargs):
        self._return_to = return_to
        s = self.game.settings
        self._sfx_slider.value   = s["sfx_vol"]
        self._music_slider.value = s["music_vol"]
        self._sfx_btn.label      = f"SFX: {'ON' if s['sfx_on'] else 'OFF'}"
        self._music_btn.label    = f"MUSIC: {'ON' if s['music_on'] else 'OFF'}"
        self._particles_btn.label = (f"PARTICLES: "
                                     f"{'ON' if s['particle_fx'] else 'OFF'}")

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
        for b in self._buttons:
            b.update(dt)

    def draw(self, surface: pygame.Surface):
        surface.fill(C_BG)

        draw_text(surface, "SETTINGS",
                  WINDOW_WIDTH//2, 80, size=48,
                  color=C_UI_TEXT_BRIGHT, bold=True,
                  align="center", shadow=True)
        draw_hline(surface, WINDOW_WIDTH//2 - 200, WINDOW_WIDTH//2 + 200, 140)

        for sl in self._sliders:
            sl.draw(surface)
        for b in self._buttons:
            b.draw(surface)

        draw_text(surface, "Press ESC to go back",
                  WINDOW_WIDTH//2, 580, size=14,
                  color=C_UI_TEXT_DIM, align="center")
