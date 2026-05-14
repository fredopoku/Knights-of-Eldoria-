import os

# ---------------------------------------------------------------------------
# Window / Display
# ---------------------------------------------------------------------------
WINDOW_WIDTH  = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE  = "Knights of Eldoria"
FPS           = 60
VERSION       = "2.0.0"

# ---------------------------------------------------------------------------
# Game Modes
# ---------------------------------------------------------------------------
MODE_WATCH   = "watch"
MODE_COMMAND = "command"
MODE_HERO    = "hero"

# ---------------------------------------------------------------------------
# Difficulty
# ---------------------------------------------------------------------------
DIFF_EASY      = "easy"
DIFF_NORMAL    = "normal"
DIFF_HARD      = "hard"
DIFF_LEGENDARY = "legendary"

DIFFICULTY_SETTINGS = {
    DIFF_EASY:      {"knight_scale": 0.5,  "treasure_scale": 1.5, "stamina_cost": 0.6, "label": "Easy"},
    DIFF_NORMAL:    {"knight_scale": 1.0,  "treasure_scale": 1.0, "stamina_cost": 1.0, "label": "Normal"},
    DIFF_HARD:      {"knight_scale": 1.5,  "treasure_scale": 0.8, "stamina_cost": 1.3, "label": "Hard"},
    DIFF_LEGENDARY: {"knight_scale": 2.0,  "treasure_scale": 0.6, "stamina_cost": 1.6, "label": "Legendary"},
}

# ---------------------------------------------------------------------------
# Map / Grid
# ---------------------------------------------------------------------------
GRID_SIZE = 28
TILE_SIZE = 28

# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------
VISIBILITY_RANGE         = 4
KNIGHT_DETECTION_RANGE   = 3
STAMINA_MOVEMENT_COST    = 2.0
STAMINA_CRITICAL_LEVEL   = 6.0
KNIGHT_CHASE_ENERGY_COST = 20.0
KNIGHT_LOW_ENERGY        = 20.0
TREASURE_DECAY_RATE      = 0.1

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
HUD_WIDTH      = 300
MINIMAP_SIZE   = 190
MINIMAP_PAD    = 10

# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------
BOB_SPEED   = 2.5
BOB_AMOUNT  = 2
PULSE_SPEED = 3.0

# ---------------------------------------------------------------------------
# Weather constants
# ---------------------------------------------------------------------------
WEATHER_NONE  = "none"
WEATHER_RAIN  = "rain"
WEATHER_STORM = "storm"

# ---------------------------------------------------------------------------
# COLOR PALETTE — Dark Fantasy "Glowing World" (Vivid Remaster)
# ---------------------------------------------------------------------------

# Void background — deep space black
C_BG = (6, 8, 18)

# Map tiles — dark atmospheric with richer hues
C_TILE_GRASS   = (28,  72,  22)
C_TILE_GRASS_2 = (22,  58,  16)
C_TILE_FOREST  = (14,  46,  14)
C_TILE_DIRT    = (92,  68,  42)
C_TILE_PATH    = (112, 88,  56)
C_GRID         = (34,  76,  28)

# Entities — vivid, glowing
C_HUNTER_NAV  = ( 50, 175, 255)   # Electric blue
C_HUNTER_END  = ( 60, 240, 110)   # Vivid green
C_HUNTER_STH  = (210, 100, 255)   # Bright purple
C_HUNTER_HERO = (255, 225,  50)   # Hero gold

C_KNIGHT        = (235,  48,  48)
C_KNIGHT_DARK   = (145,  22,  22)
C_KNIGHT_PURSUE = (255, 105,  30)

# Boss knight — bigger, redder, more threatening
C_BOSS_KNIGHT      = (220,  50,  50)
C_BOSS_KNIGHT_DARK = (140,  20,  20)

C_TREASURE_BRONZE = (230, 125,  52)
C_TREASURE_SILVER = (210, 222, 242)
C_TREASURE_GOLD   = (255, 215,  32)

C_HIDEOUT       = (165, 118,  60)
C_HIDEOUT_DARK  = (105,  72,  34)
C_GARRISON      = (135,  55,  55)
C_GARRISON_DARK = ( 80,  32,  32)

# UI — dark purple glass with gold trim (redesigned)
C_UI_BG          = (6,   8,  18)
C_UI_PANEL       = (18,  14,  36)
C_UI_PANEL_2     = (26,  22,  48)
C_UI_BORDER      = (60,  45, 100)
C_UI_BORDER_HI   = (120, 90, 200)
C_UI_TEXT        = (255, 248, 210)   # warm cream
C_UI_TEXT_DIM    = (160, 145, 130)   # muted warm
C_UI_TEXT_BRIGHT = (255, 248, 210)   # warm cream bright
C_UI_ACCENT      = (190, 140, 255)   # violet

C_BTN_NORMAL = ( 22,  16,  44)
C_BTN_HOVER  = ( 48,  36,  90)
C_BTN_ACTIVE = ( 72,  56, 128)
C_BTN_BORDER = (60,   45, 100)
C_BTN_TEXT   = (255, 248, 210)

# Status
C_GREEN  = ( 80, 220, 120)
C_RED    = (240,  60,  60)
C_YELLOW = (255, 215,  50)
C_BLUE   = ( 60, 150, 245)
C_ORANGE = (255, 140,  30)
C_WHITE  = (255, 255, 255)
C_BLACK  = (  0,   0,   0)

# Bars
C_BAR_STAMINA_HI  = ( 80, 220, 120)
C_BAR_STAMINA_MID = (255, 210,  48)
C_BAR_STAMINA_LOW = (240,  60,  60)
C_BAR_ENERGY      = ( 60, 150, 245)
C_BAR_BG          = ( 22,  18,  48)
C_BAR_BORDER      = ( 60,  45, 100)

# Particles
C_SPARK_BRONZE = (225, 135,  58)
C_SPARK_SILVER = (215, 225, 245)
C_SPARK_GOLD   = (255, 220,  58)
C_DUST         = (145, 130,  90)
C_CLASH        = (255,  90,  44)
C_STAR         = (255, 252, 115)

# Weather / Environment
C_WEATHER_RAIN = (120, 160, 220)   # rain drop colour
C_DAY_TINT     = (255, 240, 200)   # warm daytime overlay
C_NIGHT_TINT   = ( 40,  60, 120)   # cool night overlay

# Combo
C_COMBO = (255, 200,   0)          # combo multiplier text

# Ability colours
C_ABILITY_DASH  = ( 80, 210, 255)  # electric cyan
C_ABILITY_CLOAK = (180,  80, 255)  # deep violet
C_ABILITY_RALLY = (255, 200,  40)  # hero gold

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR   = os.path.join(BASE_DIR, "data")
SAVES_DIR  = os.path.join(DATA_DIR, "saves")
FONTS_DIR  = os.path.join(ASSETS_DIR, "fonts")
