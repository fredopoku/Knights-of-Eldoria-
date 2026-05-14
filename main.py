#!/usr/bin/env python3
"""
Knights of Eldoria — entry point.
Run:  python main.py
"""
import sys
import os

# Ensure the project root is on sys.path so `src.*` imports resolve.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# macOS SDL2/Metal: keep the Cocoa swap chain alive across click events.
# Must be set BEFORE pygame.init().
os.environ.setdefault('SDL_VIDEO_MAC_FULLSCREEN_SPACES', '0')
os.environ.setdefault('SDL_RENDER_VSYNC',                '0')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT',      '1')

def main():
    from src.game import Game
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
