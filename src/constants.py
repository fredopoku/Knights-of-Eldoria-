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
TILE_SIZE   = 28        # pixels per grid cell in play view

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
# Color Palette  (RGB)
# ---------------------------------------------------------------------------

# -- Map tiles --
C_BG             = (6,  14,  6)
C_TILE_GRASS     = (22, 54, 22)
C_TILE_GRASS_2   = (18, 48, 18)
C_TILE_FOREST    = (14, 38, 14)
C_TILE_DIRT      = (72, 54, 34)
C_TILE_PATH      = (90, 70, 44)
C_GRID           = (28, 58, 28)

# -- Entities --
C_HUNTER_NAV   = (80,  170, 255)   # Navigation  – bright blue
C_HUNTER_END   = (80,  210, 120)   # Endurance   – green
C_HUNTER_STH   = (190, 120, 220)   # Stealth     – purple
C_HUNTER_HERO  = (255, 210,  60)   # Player hero – gold

C_KNIGHT       = (210,  40,  40)
C_KNIGHT_DARK  = (140,  20,  20)
C_KNIGHT_PURSUE= (255,  80,  40)   # Brighter when chasing

C_TREASURE_BRONZE = (180, 100,  40)
C_TREASURE_SILVER = (180, 190, 200)
C_TREASURE_GOLD   = (240, 190,  30)

C_HIDEOUT      = (130,  90,  45)
C_HIDEOUT_DARK = ( 90,  60,  25)
C_GARRISON     = (100,  45,  45)
C_GARRISON_DARK= ( 65,  25,  25)

# -- UI Chrome --
C_UI_BG          = (12,   8,   4)
C_UI_PANEL       = (22,  16,   8)
C_UI_PANEL_2     = (30,  22,  12)
C_UI_BORDER      = (150, 110,  35)
C_UI_BORDER_HI   = (215, 165,  55)
C_UI_TEXT        = (220, 200, 150)
C_UI_TEXT_DIM    = (140, 120,  85)
C_UI_TEXT_BRIGHT = (255, 240, 185)
C_UI_ACCENT      = (200, 150,  40)

C_BTN_NORMAL = ( 38,  26,  12)
C_BTN_HOVER  = ( 58,  40,  18)
C_BTN_ACTIVE = ( 80,  56,  22)
C_BTN_BORDER = (155, 115,  38)
C_BTN_TEXT   = (220, 200, 150)

# -- Status colours --
C_GREEN  = ( 60, 190,  80)
C_RED    = (210,  55,  55)
C_YELLOW = (240, 210,  40)
C_BLUE   = ( 60, 130, 220)
C_WHITE  = (255, 255, 255)
C_BLACK  = (  0,   0,   0)

# -- HUD bars --
C_BAR_STAMINA_HI  = ( 60, 200,  80)
C_BAR_STAMINA_MID = (230, 190,  40)
C_BAR_STAMINA_LOW = (210,  55,  55)
C_BAR_ENERGY      = ( 60, 130, 220)
C_BAR_BG          = ( 35,  25,  12)
C_BAR_BORDER      = (100,  75,  30)

# -- Particles --
C_SPARK_BRONZE = (200, 120,  50)
C_SPARK_SILVER = (200, 210, 220)
C_SPARK_GOLD   = (255, 210,  50)
C_DUST         = (140, 120,  80)
C_CLASH        = (255,  80,  40)
C_STAR         = (255, 240, 100)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
DATA_DIR    = os.path.join(BASE_DIR, "data")
SAVES_DIR   = os.path.join(DATA_DIR, "saves")
FONTS_DIR   = os.path.join(ASSETS_DIR, "fonts")
