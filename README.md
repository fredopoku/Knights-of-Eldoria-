# ⚔️ Knights of Eldoria

A medieval treasure-hunt strategy / action game built in Python + Pygame.

---

## Features

| Feature | Detail |
|---|---|
| **3 Game Modes** | Watch (AI sim), Command (strategic), Hero (direct control) |
| **4 Difficulty Levels** | Easy → Legendary |
| **25 Achievements** | Unlocked automatically as you play |
| **Save System** | 3 save slots with high-score tracking |
| **Full HUD** | Live stats, event log, minimap |
| **Particle FX** | Sparkles, dust, combat bursts |
| **60 FPS** | Hardware-accelerated Pygame rendering |
| **Tutorial** | 7-step interactive guide for new players |

---

## Game Modes

### 👁 Watch Mode
Sit back and observe the AI hunters navigate a dangerous medieval world. Adjust speed 1×–30× and watch emergent strategies unfold.

### 📜 Command Mode
*You're the general.* Click any hunter to select them, then click the map to issue movement orders. Direct your squad to the richest loot while knights patrol.

### 🦸 Hero Mode
*You ARE the hunter.* Use **WASD** or **Arrow Keys** to move, collect treasure, and deposit it at hideouts — all while knights chase you down.

---

## Controls

| Key | Action |
|---|---|
| `Space` | Pause / Resume |
| `+` / `-` | Speed up / down |
| `S` | Single step (Watch / Command) |
| `WASD` / Arrows | Move (Hero Mode) |
| `Escape` | Pause menu |

---

## Running the Game

```bash
pip install -r requirements.txt
python main.py
```

Requires **Python 3.10+**, **Pygame 2.5+**, and **Pillow**.

---

## Entity Guide

| Icon | Entity | Role |
|---|---|---|
| 🔵 Blue circle | Hunter (Navigation) | Sees farther, finds better paths |
| 🟢 Green circle | Hunter (Endurance) | Lower stamina cost, faster regen |
| 🟣 Purple circle | Hunter (Stealth) | 50% dodge chance vs knights |
| 🟡 Gold circle | Your hero (Hero Mode) | Player-controlled |
| 🔴 Red diamond | Knight | Patrols and pursues hunters |
| 🟤 Building | Hideout | Hunter rest & treasure deposit |
| 🏰 Dark building | Garrison | Knight rest & energy recovery |
| 🟡 Glowing dot | Treasure | Bronze / Silver / Gold |

---

## License

© Frederick Opoku Afriyie. All rights reserved.
