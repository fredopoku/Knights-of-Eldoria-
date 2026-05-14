import os
import pygame
from src.constants import ASSETS_DIR

class AudioManager:
    """Handles all sound effects and background music."""

    MUSIC_TRACKS = [
        "music_main.ogg",
        "music_battle.ogg",
    ]

    SFX_FILES = {
        "collect":   "collect.wav",
        "challenge": "challenge.wav",
        "footsteps": "footsteps.wav",
        "warning":   "warning.wav",
        "ui_click":  "ui_click.wav",
        "ui_hover":  "ui_hover.wav",
        "victory":   "victory.wav",
        "gameover":  "gameover.wav",
    }

    def __init__(self):
        self._sfx: dict[str, pygame.mixer.Sound] = {}
        self._sfx_vol   = 0.7
        self._music_vol = 0.4
        self._sfx_on    = True
        self._music_on  = True
        self._current_track = None

        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._available = True
        except Exception:
            self._available = False

        if self._available:
            self._load_sfx()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def _load_sfx(self):
        for key, filename in self.SFX_FILES.items():
            path = os.path.join(ASSETS_DIR, filename)
            if os.path.exists(path):
                try:
                    snd = pygame.mixer.Sound(path)
                    snd.set_volume(self._sfx_vol)
                    self._sfx[key] = snd
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # SFX
    # ------------------------------------------------------------------
    def play(self, key: str):
        if not self._available or not self._sfx_on:
            return
        snd = self._sfx.get(key)
        if snd:
            try:
                snd.play()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Music
    # ------------------------------------------------------------------
    def play_music(self, track_name: str | None = None):
        if not self._available or not self._music_on:
            return
        if track_name is None:
            track_name = "music_main.ogg"
        if track_name == self._current_track and pygame.mixer.music.get_busy():
            return
        path = os.path.join(ASSETS_DIR, track_name)
        if not os.path.exists(path):
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self._music_vol)
            pygame.mixer.music.play(-1)
            self._current_track = track_name
        except Exception:
            pass

    def stop_music(self):
        if self._available:
            try:
                pygame.mixer.music.fadeout(800)
            except Exception:
                pass

    def pause_music(self):
        if self._available:
            try:
                pygame.mixer.music.pause()
            except Exception:
                pass

    def resume_music(self):
        if self._available:
            try:
                pygame.mixer.music.unpause()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Volume / toggles
    # ------------------------------------------------------------------
    @property
    def sfx_vol(self):
        return self._sfx_vol

    @sfx_vol.setter
    def sfx_vol(self, v: float):
        self._sfx_vol = max(0.0, min(1.0, v))
        for snd in self._sfx.values():
            snd.set_volume(self._sfx_vol)

    @property
    def music_vol(self):
        return self._music_vol

    @music_vol.setter
    def music_vol(self, v: float):
        self._music_vol = max(0.0, min(1.0, v))
        if self._available:
            try:
                pygame.mixer.music.set_volume(self._music_vol)
            except Exception:
                pass

    @property
    def sfx_on(self):
        return self._sfx_on

    @sfx_on.setter
    def sfx_on(self, v: bool):
        self._sfx_on = v

    @property
    def music_on(self):
        return self._music_on

    @music_on.setter
    def music_on(self, v: bool):
        self._music_on = v
        if not v:
            self.stop_music()
        else:
            self.play_music(self._current_track)
