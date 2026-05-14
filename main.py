#!/usr/bin/env python3
"""
Knights of Eldoria — entry point.
Run:  python main.py
"""
import os
import sys

# CRITICAL: Force SDL2 software rendering BEFORE pygame is imported.
# This fixes the persistent black screen on macOS caused by Metal hardware surfaces.
os.environ['SDL_RENDER_DRIVER'] = 'software'

# Ensure the project root is on sys.path so `src.*` imports resolve.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# macOS / SDL2 housekeeping — must be set BEFORE pygame.init()
os.environ.setdefault('SDL_VIDEO_MAC_FULLSCREEN_SPACES', '0')
os.environ.setdefault('SDL_RENDER_VSYNC',                '0')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT',      '1')


def main():
    from src.game import Game
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
