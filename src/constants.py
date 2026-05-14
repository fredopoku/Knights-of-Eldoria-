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
MODE_WATCH    = "watch"     # Watch the AI simulation unfold
MODE_COMMAND  = "command"   # Click-to-command strategic layer
MODE_HERO     = "hero"      # Direct WASD control of a hunter

# ---------------------------------------------------------------------------
# Difficulty Presets
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
GRID_SIZE   = 30
TILE_SIZE   = 28        # pixels per grid cell (approximate; renderer recalculates)

# ---------------------------------------------------------------------------
# Simulation physics
# ---------------------------------------------------------------------------
VISIBILITY_RANGE        = 3
KNIGHT_DETECTION_RANGE  = 3
STAMINA_MOVEMENT_COST   = 2.0
STAMINA_CRITICAL_LEVEL  = 6.0
KNIGHT_CHASE_ENERGY_COST = 20.0
KNIGHT_LOW_ENERGY       = 20.0
TREASURE_DECAY_RATE     = 0.1   # % of initial value lost per step

# ---------------------------------------------------------------------------
# UI Layout
# ---------------------------------------------------------------------------
HUD_WIDTH      = 290
MINIMAP_SIZE   = 180
MINIMAP_PAD    = 8
EVENT_LOG_LINES = 10

# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------
BOB_SPEED    = 2.5          # radians/sec
BOB_AMOUNT   = 2            # pixels
PULSE_SPEED  = 3.0          # radians/sec for treasure glow

# ---------------------------------------------------------------------------
# Color Palette  (RGB)  — commercial-quality medieval
# ---------------------------------------------------------------------------

# -- Map tiles --
C_BG             = (18,  38,  18)   # Rich dark forest background
C_TILE_GRASS     = (55, 118,  45)   # Vibrant meadow green
C_TILE_GRASS_2   = (48, 102,  38)   # Slightly darker variant
C_TILE_FOREST    = (28,  72,  28)   # Deep forest green
C_TILE_DIRT      = (140, 100,  58)  # Rich earth brown
C_TILE_PATH      = (168, 132,  78)  # Warm stone path
C_GRID           = (38,  80,  34)   # Subtle grid lines

# -- Entities --
C_HUNTER_NAV   = ( 80, 170, 255)   # Navigation  – bright blue
C_HUNTER_END   = ( 80, 210, 120)   # Endurance   – green
C_HUNTER_STH   = (190, 120, 220)   # Stealth     – purple
C_HUNTER_HERO  = (255, 215,  60)   # Player hero – gold

C_KNIGHT       = (215,  45,  45)
C_KNIGHT_DARK  = (145,  22,  22)
C_KNIGHT_PURSUE= (255,  85,  40)   # Brighter when chasing

C_TREASURE_BRONZE = (200, 110,  45)
C_TREASURE_SILVER = (185, 198, 210)
C_TREASURE_GOLD   = (248, 200,  35)

C_HIDEOUT      = (148, 105,  52)
C_HIDEOUT_DARK = (100,  68,  30)
C_GARRISON     = (115,  52,  52)
C_GARRISON_DARK= ( 72,  28,  28)

# -- UI Chrome — rich dark medieval gold --
C_UI_BG          = (14,   9,   4)
C_UI_PANEL       = (24,  17,   8)
C_UI_PANEL_2     = (34,  24,  12)
C_UI_BORDER      = (175, 130,  42)
C_UI_BORDER_HI   = (225, 178,  60)
C_UI_TEXT        = (228, 208, 158)
C_UI_TEXT_DIM    = (155, 133,  92)
C_UI_TEXT_BRIGHT = (255, 245, 195)
C_UI_ACCENT      = (210, 158,  45)

C_BTN_NORMAL = ( 42,  29,  13)
C_BTN_HOVER  = ( 65,  47,  20)
C_BTN_ACTIVE = ( 92,  65,  25)
C_BTN_BORDER = (175, 130,  42)
C_BTN_TEXT   = (228, 208, 158)

# -- Status colours --
C_GREEN  = ( 65, 200,  85)
C_RED    = (220,  58,  58)
C_YELLOW = (245, 215,  45)
C_BLUE   = ( 65, 138, 228)
C_WHITE  = (255, 255, 255)
C_BLACK  = (  0,   0,   0)
C_ORANGE = (240, 145,  30)

# -- HUD bars --
C_BAR_STAMINA_HI  = ( 65, 205,  85)
C_BAR_STAMINA_MID = (238, 195,  42)
C_BAR_STAMINA_LOW = (218,  58,  58)
C_BAR_ENERGY      = ( 65, 138, 228)
C_BAR_BG          = ( 32,  22,  10)
C_BAR_BORDER      = (108,  80,  32)

# -- Particles --
C_SPARK_BRONZE = (208, 125,  55)
C_SPARK_SILVER = (205, 215, 228)
C_SPARK_GOLD   = (255, 215,  55)
C_DUST         = (148, 128,  85)
C_CLASH        = (255,  85,  45)
C_STAR         = (255, 245, 105)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
DATA_DIR    = os.path.join(BASE_DIR, "data")
SAVES_DIR   = os.path.join(DATA_DIR, "saves")
FONTS_DIR   = os.path.join(ASSETS_DIR, "fonts")
