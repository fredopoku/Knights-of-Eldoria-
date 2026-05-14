"""
Save/load system, achievement manager, settings manager.
"""
from __future__ import annotations
import json
import os
import time
from src.constants import SAVES_DIR, DATA_DIR, DIFF_NORMAL

# ---------------------------------------------------------------------------
# SettingsManager
# ---------------------------------------------------------------------------
class SettingsManager:
    DEFAULTS = {
        "sfx_vol":      0.7,
        "music_vol":    0.4,
        "sfx_on":       True,
        "music_on":     True,
        "fullscreen":   False,
        "difficulty":   DIFF_NORMAL,
        "grid_size":    30,
        "sim_speed":    5,
        "show_grid":    True,
        "show_paths":   False,
        "particle_fx":  True,
    }

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self._path = os.path.join(DATA_DIR, "settings.json")
        self._data = dict(self.DEFAULTS)
        self._load()

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path) as f:
                    loaded = json.load(f)
                self._data.update(loaded)
            except Exception:
                pass

    def save(self):
        try:
            with open(self._path, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def __getitem__(self, key):
        return self._data.get(key, self.DEFAULTS.get(key))

    def __setitem__(self, key, value):
        self._data[key] = value
        self.save()

    def get(self, key, default=None):
        return self._data.get(key, default)


# ---------------------------------------------------------------------------
# SaveManager
# ---------------------------------------------------------------------------
class SaveData:
    def __init__(self):
        self.slot:       int   = 0
        self.timestamp:  float = 0.0
        self.mode:       str   = ""
        self.difficulty: str   = DIFF_NORMAL
        self.step:       int   = 0
        self.score:      int   = 0
        self.pct:        float = 0.0
        self.label:      str   = ""

    def to_dict(self) -> dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: dict) -> "SaveData":
        s = cls()
        s.__dict__.update(d)
        return s


class SaveManager:
    NUM_SLOTS = 3

    def __init__(self):
        os.makedirs(SAVES_DIR, exist_ok=True)
        self._slots: list[SaveData | None] = [None] * self.NUM_SLOTS
        self._load_all()

    def _slot_path(self, slot: int) -> str:
        return os.path.join(SAVES_DIR, f"save_{slot}.json")

    def _load_all(self):
        for i in range(self.NUM_SLOTS):
            path = self._slot_path(i)
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        self._slots[i] = SaveData.from_dict(json.load(f))
                except Exception:
                    self._slots[i] = None

    def get_slot(self, slot: int) -> SaveData | None:
        return self._slots[slot] if 0 <= slot < self.NUM_SLOTS else None

    def save(self, slot: int, mode: str, difficulty: str,
             step: int, score: int, pct: float):
        sd = SaveData()
        sd.slot       = slot
        sd.timestamp  = time.time()
        sd.mode       = mode
        sd.difficulty = difficulty
        sd.step       = step
        sd.score      = score
        sd.pct        = pct
        sd.label      = f"{mode.title()} – Step {step}"
        self._slots[slot] = sd
        try:
            with open(self._slot_path(slot), "w") as f:
                json.dump(sd.to_dict(), f, indent=2)
        except Exception:
            pass
        return sd

    def delete(self, slot: int):
        self._slots[slot] = None
        path = self._slot_path(slot)
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    def high_scores(self) -> list[SaveData]:
        return sorted(
            [s for s in self._slots if s is not None],
            key=lambda s: s.score, reverse=True
        )


# ---------------------------------------------------------------------------
# Achievement definitions
# ---------------------------------------------------------------------------
ACHIEVEMENTS = [
    {"id": "first_collect",   "name": "First Haul",
     "desc": "Collect your first treasure.",       "icon": "🏅"},
    {"id": "ten_collects",    "name": "Getting Rich",
     "desc": "Collect 10 treasures.",              "icon": "💰"},
    {"id": "fifty_collects",  "name": "Master Looter",
     "desc": "Collect 50 treasures.",              "icon": "👑"},
    {"id": "pct_25",          "name": "Quarter Done",
     "desc": "Reach 25% collection.",              "icon": "📊"},
    {"id": "pct_50",          "name": "Halfway There",
     "desc": "Reach 50% collection.",              "icon": "📈"},
    {"id": "pct_75",          "name": "Almost There",
     "desc": "Reach 75% collection.",              "icon": "🌟"},
    {"id": "pct_100",         "name": "Grand Sweep",
     "desc": "Collect all treasures.",             "icon": "🏆"},
    {"id": "survived_100",    "name": "Century",
     "desc": "Survive 100 simulation steps.",      "icon": "⏱"},
    {"id": "survived_500",    "name": "Long Game",
     "desc": "Survive 500 simulation steps.",      "icon": "🕰"},
    {"id": "first_gold",      "name": "Gold Rush",
     "desc": "Collect your first gold treasure.",  "icon": "🥇"},
    {"id": "hero_collect",    "name": "Hero's Haul",
     "desc": "Collect a treasure in Hero Mode.",   "icon": "⚔️"},
    {"id": "score_1000",      "name": "Score: 1,000",
     "desc": "Reach a score of 1,000.",            "icon": "🎯"},
    {"id": "score_5000",      "name": "Score: 5,000",
     "desc": "Reach a score of 5,000.",            "icon": "🎯"},
    {"id": "score_10000",     "name": "Legend",
     "desc": "Reach a score of 10,000.",           "icon": "🌠"},
    {"id": "hard_complete",   "name": "Tough Knight",
     "desc": "Complete a Hard difficulty run.",    "icon": "🗡"},
    {"id": "legendary_run",   "name": "Legendary",
     "desc": "Complete a Legendary run.",          "icon": "🐉"},
    {"id": "evader",          "name": "Slippery",
     "desc": "Successfully evade 5 knights.",      "icon": "💨"},
    {"id": "recruiter",       "name": "Growing Army",
     "desc": "Recruit a new hunter.",              "icon": "🤝"},
    {"id": "hunter_5",        "name": "Squad Goals",
     "desc": "Have 5 hunters active at once.",     "icon": "👥"},
    {"id": "hunter_10",       "name": "Army of Shadows",
     "desc": "Have 10 hunters active at once.",    "icon": "⚔️"},
    {"id": "watch_mode",      "name": "Spectator",
     "desc": "Play Watch Mode for the first time.","icon": "👁"},
    {"id": "command_mode",    "name": "General",
     "desc": "Issue a command in Command Mode.",   "icon": "📜"},
    {"id": "hero_mode",       "name": "Enter the Hero",
     "desc": "Play Hero Mode for the first time.", "icon": "🦸"},
    {"id": "saved_game",      "name": "Saved",
     "desc": "Save your progress.",               "icon": "💾"},
    {"id": "speedrun_200",    "name": "Speedrunner",
     "desc": "Reach 50% collection in ≤200 steps.","icon": "⚡"},
]


class AchievementManager:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self._path    = os.path.join(DATA_DIR, "achievements.json")
        self._unlocked: set[str] = set()
        self._pending:  list[dict] = []    # queued for display
        self._load()

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path) as f:
                    self._unlocked = set(json.load(f))
            except Exception:
                pass

    def _save(self):
        try:
            with open(self._path, "w") as f:
                json.dump(list(self._unlocked), f)
        except Exception:
            pass

    def unlock(self, achievement_id: str) -> bool:
        """Unlock an achievement. Returns True if newly unlocked."""
        if achievement_id in self._unlocked:
            return False
        self._unlocked.add(achievement_id)
        self._save()
        defn = next((a for a in ACHIEVEMENTS if a["id"] == achievement_id), None)
        if defn:
            self._pending.append(defn)
        return True

    def is_unlocked(self, achievement_id: str) -> bool:
        return achievement_id in self._unlocked

    def pop_pending(self) -> dict | None:
        return self._pending.pop(0) if self._pending else None

    def all_achievements(self) -> list[dict]:
        return ACHIEVEMENTS

    def unlocked_ids(self) -> set[str]:
        return set(self._unlocked)

    def check_stats(self, stats: dict, mode: str, total_collects: int,
                    total_gold: int, hero_collect: bool = False,
                    evasions: int = 0):
        """Check and auto-unlock any achievements based on current game stats."""
        a = self.unlock
        if total_collects >= 1:    a("first_collect")
        if total_collects >= 10:   a("ten_collects")
        if total_collects >= 50:   a("fifty_collects")
        if stats["pct"] >= 25:     a("pct_25")
        if stats["pct"] >= 50:     a("pct_50")
        if stats["pct"] >= 75:     a("pct_75")
        if stats["pct"] >= 99.9:   a("pct_100")
        if stats["step"] >= 100:   a("survived_100")
        if stats["step"] >= 500:   a("survived_500")
        if total_gold >= 1:        a("first_gold")
        if hero_collect:           a("hero_collect")
        if stats["score"] >= 1000: a("score_1000")
        if stats["score"] >= 5000: a("score_5000")
        if stats["score"] >= 10000:a("score_10000")
        if evasions >= 5:          a("evader")
        if stats["hunters"] >= 5:  a("hunter_5")
        if stats["hunters"] >= 10: a("hunter_10")
        if mode == "watch":        a("watch_mode")
        if mode == "command":      a("command_mode")
        if mode == "hero":         a("hero_mode")
        if (stats["pct"] >= 50 and stats["step"] <= 200):
            a("speedrun_200")
