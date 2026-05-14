#!/usr/bin/env python3
"""
Knights of Eldoria — entry point.
Run:  python main.py
"""
import sys
import os

# Ensure the project root is on sys.path so `src.*` imports resolve.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    from src.game import Game
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
