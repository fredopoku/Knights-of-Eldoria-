#!/usr/bin/env python3
"""
Knights of Eldoria — entry point.
  Desktop:  python main.py
  Web/PWA:  python -m pygbag main.py   (builds WebAssembly bundle)
"""
import os
import sys
import asyncio

# Force SDL software rendering on desktop macOS (ignored by Pygbag on web).
os.environ['SDL_RENDER_DRIVER'] = 'software'
os.environ.setdefault('SDL_VIDEO_MAC_FULLSCREEN_SPACES', '0')
os.environ.setdefault('SDL_RENDER_VSYNC',                '0')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT',      '1')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def main():
    from src.game import Game
    game = Game()
    # Pygbag-compatible loop: yield to browser every frame with asyncio.sleep(0)
    while game.running:
        game.frame()
        await asyncio.sleep(0)
    # Do NOT call pygame.quit() / sys.exit() here — Pygbag owns the process.


if __name__ == "__main__":
    asyncio.run(main())
