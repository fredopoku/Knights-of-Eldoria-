import os

# ---------------------------------------------------------------------------
# Window / Display
# ---------------------------------------------------------------------------
WINDOW_WIDTH  = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE  = "Knights of Eldoria"
FPS           = 60
VERSION       = "1.0.0"

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
# COLOR PALETTE — Dark Fantasy "Glowing World"
# ---------------------------------------------------------------------------

# Void background
C_BG = (8, 10, 22)

# Map tiles — dark, atmospheric
C_TILE_GRASS   = (32,  65,  26)
C_TILE_GRASS_2 = (26,  54,  20)
C_TILE_FOREST  = (18,  42,  18)
C_TILE_DIRT    = (88,  64,  40)
C_TILE_PATH    = (108, 85,  54)
C_GRID         = (38,  72,  32)

# Entities — vivid, glowing
C_HUNTER_NAV  = ( 55, 165, 255)   # Electric blue
C_HUNTER_END  = ( 65, 235, 115)   # Vivid green
C_HUNTER_STH  = (205, 105, 255)   # Bright purple
C_HUNTER_HERO = (255, 220,  55)   # Hero gold

C_KNIGHT        = (235,  48,  48)
C_KNIGHT_DARK   = (145,  22,  22)
C_KNIGHT_PURSUE = (255, 105,  30)

C_TREASURE_BRONZE = (225, 122,  52)
C_TREASURE_SILVER = (205, 218, 238)
C_TREASURE_GOLD   = (255, 212,  32)

C_HIDEOUT       = (162, 115,  58)
C_HIDEOUT_DARK  = (102,  70,  32)
C_GARRISON      = (132,  54,  54)
C_GARRISON_DARK = ( 78,  30,  30)

# UI — dark purple glass with gold trim
C_UI_BG          = (12,  10,  24)
C_UI_PANEL       = (18,  15,  32)
C_UI_PANEL_2     = (26,  22,  44)
C_UI_BORDER      = (182, 140,  50)
C_UI_BORDER_HI   = (235, 190,  72)
C_UI_TEXT        = (235, 215, 168)
C_UI_TEXT_DIM    = (155, 135, 102)
C_UI_TEXT_BRIGHT = (255, 248, 205)
C_UI_ACCENT      = (218, 165,  52)

C_BTN_NORMAL = ( 28,  22,  50)
C_BTN_HOVER  = ( 52,  42,  88)
C_BTN_ACTIVE = ( 78,  62, 118)
C_BTN_BORDER = (182, 140,  50)
C_BTN_TEXT   = (235, 215, 168)

# Status
C_GREEN  = ( 72, 220,  92)
C_RED    = (228,  58,  58)
C_YELLOW = (252, 222,  48)
C_BLUE   = ( 62, 148, 238)
C_ORANGE = (248, 152,  34)
C_WHITE  = (255, 255, 255)
C_BLACK  = (  0,   0,   0)

# Bars
C_BAR_STAMINA_HI  = ( 72, 220,  92)
C_BAR_STAMINA_MID = (248, 208,  46)
C_BAR_STAMINA_LOW = (228,  58,  58)
C_BAR_ENERGY      = ( 62, 148, 238)
C_BAR_BG          = ( 24,  20,  44)
C_BAR_BORDER      = (102,  80,  34)

# Particles
C_SPARK_BRONZE = (222, 132,  56)
C_SPARK_SILVER = (212, 222, 242)
C_SPARK_GOLD   = (255, 218,  56)
C_DUST         = (142, 128,  88)
C_CLASH        = (255,  92,  46)
C_STAR         = (255, 252, 112)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR   = os.path.join(BASE_DIR, "data")
SAVES_DIR  = os.path.join(DATA_DIR, "saves")
FONTS_DIR  = os.path.join(ASSETS_DIR, "fonts")
