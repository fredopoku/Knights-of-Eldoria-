"""
Main Game class — state machine and 60 fps loop.
Errors are always shown on-screen so black screens are impossible.
"""
from __future__ import annotations
import sys
import traceback
import pygame
from src.constants import WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, FPS, C_BG


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen  = pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE
        )
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
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)

            self._apply_transition()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                elif event.type == pygame.VIDEORESIZE:
                    # Recreate surface — states must always accept the
                    # surface passed into draw(), never cache it.
                    self.screen = pygame.display.set_mode(
                        event.size, pygame.RESIZABLE
                    )
                elif not self._error and self._current:
                    try:
                        self._current.handle_event(event)
                    except Exception:
                        pass   # non-fatal; don't blank the screen

            if self._error:
                self._draw_error()
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

                self.screen.fill(C_BG)
                try:
                    self._current.draw(self.screen)
                except Exception:
                    self._error = traceback.format_exc()

            pygame.display.flip()

        pygame.quit()
        sys.exit()

    # ------------------------------------------------------------------
    def _draw_error(self):
        self.screen.fill((20, 0, 0))
        font_h = pygame.font.Font(None, 30)
        font_b = pygame.font.Font(None, 20)
        hdr = font_h.render("GAME ERROR  —  press ESC to return to menu", True, (255, 80, 80))
        self.screen.blit(hdr, (20, 16))
        y = 56
        for line in self._error.splitlines()[:28]:
            s = font_b.render(line[:150], True, (255, 210, 210))
            self.screen.blit(s, (20, y))
            y += 20
