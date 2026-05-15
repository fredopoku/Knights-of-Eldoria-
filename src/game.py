"""
Main Game class — state machine and 60 fps loop.
SDL_RENDER_DRIVER=software is set in main.py so all surfaces are
CPU-accessible software surfaces; no Metal/GPU issues possible.
"""
from __future__ import annotations
import traceback
import pygame
from src.constants import WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, FPS, C_BG


class Game:
    def __init__(self):
        # pygbag's WASM runtime pre-initializes SDL2/pygame; init() may not exist
        if hasattr(pygame, 'init'):
            pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen  = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock   = pygame.time.Clock()
        self.running = True
        self._error: str | None = None

        from src.audio import AudioManager
        from src.saves import SettingsManager, SaveManager, AchievementManager

        self.audio        = AudioManager()
        self.settings     = SettingsManager()
        self.saves        = SaveManager()
        self.achievements = AchievementManager()

        self.audio.sfx_vol   = self.settings["sfx_vol"]
        self.audio.music_vol = self.settings["music_vol"]
        self.audio.sfx_on    = self.settings["sfx_on"]
        self.audio.music_on  = self.settings["music_on"]

        self._states: dict[str, object] = {}
        self._build_states()

        self._current: object | None = None
        self._next:    tuple  | None = None

        # Touch gamepad — active on web/mobile, hidden on desktop until touch used
        from src.touch_ui import TouchGamepad
        self.touch = TouchGamepad()
        # Auto-detect web/Pygbag environment
        import sys as _sys
        self.is_web = _sys.platform in ('emscripten', 'wasi')

        self.change_state("menu")

    # ------------------------------------------------------------------
    def _build_states(self):
        from src.states.menu     import MenuState
        from src.states.play     import PlayState
        from src.states.pause    import PauseState
        from src.states.settings import SettingsState
        from src.states.tutorial import TutorialState
        from src.states.credits  import CreditsState
        from src.states.gameover import GameOverState
        from src.states.victory  import VictoryState

        self._states = {
            "menu":     MenuState(self),
            "play":     PlayState(self),
            "pause":    PauseState(self),
            "settings": SettingsState(self),
            "tutorial": TutorialState(self),
            "credits":  CreditsState(self),
            "gameover": GameOverState(self),
            "victory":  VictoryState(self),
        }

    # ------------------------------------------------------------------
    def change_state(self, name: str, **kwargs):
        self._next = (name, kwargs)

    def _apply_transition(self):
        if self._next is None:
            return
        name, kwargs = self._next
        self._next   = None

        if self._current is not None:
            try:
                self._current.exit()
            except Exception:
                pass

        state = self._states.get(name)
        if state is None:
            self._error = f"Unknown state: {name!r}"
            return

        try:
            state.enter(**kwargs)
        except Exception:
            self._error = traceback.format_exc()
            return

        self._current = state
        self._error   = None

    # ------------------------------------------------------------------
    def run(self):
        """Desktop blocking loop — calls frame() until game ends."""
        while self.running:
            self.frame()

    def frame(self):
        """Single frame: events → update → draw → flip.
        Called by run() on desktop and by the async loop (Pygbag) on web."""
        dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
        surface = pygame.display.get_surface()

        self._apply_transition()

        raw_events = pygame.event.get()
        # Expand touch/mouse events through the virtual gamepad
        all_events = []
        for event in raw_events:
            all_events.append(event)
            synth = self.touch.handle_mouse_event(event)
            all_events.extend(synth)

        for event in all_events:
            if event.type == pygame.QUIT:
                self.running = False
                return
            elif event.type in (pygame.VIDEOEXPOSE, pygame.ACTIVEEVENT):
                pass
            elif not self._error and self._current:
                try:
                    self._current.handle_event(event)
                except Exception:
                    pass

        if self._error:
            try:
                self._draw_error(surface)
            except Exception:
                surface.fill((20, 0, 0))
            keys = pygame.key.get_pressed()
            if keys[pygame.K_ESCAPE]:
                self._error   = None
                self._current = None
                self.change_state("menu")
        elif self._current:
            try:
                self._current.update(dt)
            except Exception:
                self._error = traceback.format_exc()

            surface.fill(C_BG)
            try:
                self._current.draw(surface)
            except Exception:
                self._error = traceback.format_exc()

            # Touch gamepad — always visible on web, only in play on desktop
            if self.is_web or self._is_play_state():
                abilities = self._get_play_abilities()
                self.touch.draw(surface, abilities=abilities)
        else:
            surface.fill(C_BG)

        pygame.event.pump()
        pygame.display.flip()

    def _is_play_state(self) -> bool:
        return (self._current is not None and
                type(self._current).__name__ == "PlayState")

    def _get_play_abilities(self):
        if not self._is_play_state():
            return None
        try:
            return getattr(self._current, '_abilities', None)
        except Exception:
            return None

    # ------------------------------------------------------------------
    def _draw_error(self, surface: pygame.Surface):
        surface.fill((20, 0, 0))
        font_h = pygame.font.Font(None, 30)
        font_b = pygame.font.Font(None, 20)
        hdr = font_h.render("GAME ERROR - press ESC to return to menu", True, (255, 80, 80))
        surface.blit(hdr, (20, 16))
        y = 56
        for line in (self._error or "").splitlines()[:28]:
            s = font_b.render(line[:150], True, (255, 210, 210))
            surface.blit(s, (20, y))
            y += 20
