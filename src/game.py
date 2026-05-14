"""
Main Game class: window, state machine, and the 60fps game loop.
"""
from __future__ import annotations
import sys
import pygame
from src.constants import WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, FPS, C_BG


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen = pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE
        )
        self.clock   = pygame.time.Clock()
        self.running = True

        # Shared sub-systems (imported here to avoid circular imports)
        from src.audio import AudioManager
        from src.saves import SettingsManager, SaveManager, AchievementManager

        self.audio        = AudioManager()
        self.settings     = SettingsManager()
        self.saves        = SaveManager()
        self.achievements = AchievementManager()

        # Apply saved audio settings
        self.audio.sfx_vol   = self.settings["sfx_vol"]
        self.audio.music_vol = self.settings["music_vol"]
        self.audio.sfx_on    = self.settings["sfx_on"]
        self.audio.music_on  = self.settings["music_on"]

        # Build state registry
        self._states: dict[str, object] = {}
        self._build_states()

        self._current:   object | None = None
        self._next:      tuple  | None = None   # (name, kwargs)

        # Start at menu
        self.change_state("menu")

    # ------------------------------------------------------------------
    # State registry
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
    # State transitions
    # ------------------------------------------------------------------
    def change_state(self, name: str, **kwargs):
        """Request a state change; applied at start of next frame."""
        self._next = (name, kwargs)

    def _apply_transition(self):
        if self._next is None:
            return
        name, kwargs = self._next
        self._next   = None

        if self._current is not None:
            try:
                self._current.exit()
            except Exception as e:
                print(f"[WARN] exit() error in {self._current}: {e}")

        state = self._states.get(name)
        if state is None:
            print(f"[ERROR] Unknown state: {name!r}")
            return

        try:
            state.enter(**kwargs)
        except Exception as e:
            print(f"[WARN] enter() error in {name}: {e}")

        self._current = state

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)  # cap at 50ms

            # Pending transition
            self._apply_transition()
            if self._current is None:
                continue

            # Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                elif event.type == pygame.VIDEORESIZE:
                    # Re-create surface on resize (RESIZABLE flag)
                    self.screen = pygame.display.set_mode(
                        event.size, pygame.RESIZABLE
                    )
                else:
                    try:
                        self._current.handle_event(event)
                    except Exception as e:
                        print(f"[WARN] handle_event error: {e}")

            # Update
            try:
                self._current.update(dt)
            except Exception as e:
                print(f"[WARN] update error: {e}")

            # Draw
            self.screen.fill(C_BG)
            try:
                self._current.draw(self.screen)
            except Exception as e:
                print(f"[WARN] draw error: {e}")

            pygame.display.flip()

        pygame.quit()
        sys.exit()
