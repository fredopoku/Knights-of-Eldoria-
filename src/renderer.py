"""
All rendering: map tiles, entities, HUD panel, minimap, screen transitions.
"""
from __future__ import annotations
import math
import os
import random
import pygame
from src.constants import (
    TILE_SIZE, GRID_SIZE, HUD_WIDTH, MINIMAP_SIZE, MINIMAP_PAD,
    C_BG, C_TILE_GRASS, C_TILE_GRASS_2, C_TILE_FOREST, C_TILE_PATH,
    C_GRID, C_TILE_DIRT,
    C_HUNTER_NAV, C_HUNTER_END, C_HUNTER_STH, C_HUNTER_HERO,
    C_KNIGHT, C_KNIGHT_DARK, C_KNIGHT_PURSUE,
    C_TREASURE_BRONZE, C_TREASURE_SILVER, C_TREASURE_GOLD,
    C_HIDEOUT, C_HIDEOUT_DARK, C_GARRISON, C_GARRISON_DARK,
    C_UI_PANEL, C_UI_PANEL_2, C_UI_BORDER, C_UI_BORDER_HI,
    C_UI_TEXT, C_UI_TEXT_DIM, C_UI_TEXT_BRIGHT, C_UI_ACCENT,
    C_BAR_BG, C_BAR_BORDER, C_BAR_STAMINA_HI, C_BAR_STAMINA_MID,
    C_BAR_STAMINA_LOW, C_BAR_ENERGY,
    C_GREEN, C_RED, C_YELLOW, C_WHITE, C_BLACK,
    C_SPARK_BRONZE, C_SPARK_SILVER, C_SPARK_GOLD,
    BOB_SPEED, BOB_AMOUNT, PULSE_SPEED,
    ASSETS_DIR,
)
from src.simulation import (
    EntityType, HunterSkill, HunterState, KnightState,
    Hunter, Knight, Treasure, Hideout, Garrison,
    EldoriaSimulation,
)
from src.ui import draw_text, draw_panel, draw_hline, get_font, ProgressBar


# ---------------------------------------------------------------------------
# Tilemap generator  (procedural, seeded so it stays consistent)
# ---------------------------------------------------------------------------
class TileMap:
    GRASS  = 0
    GRASS2 = 1
    FOREST = 2
    DIRT   = 3
    PATH   = 4

    def __init__(self, grid_size: int, seed: int = 42):
        rng = random.Random(seed)
        self._tiles = {}
        for x in range(grid_size):
            for y in range(grid_size):
                r = rng.random()
                if r < 0.05:
                    t = self.FOREST
                elif r < 0.10:
                    t = self.DIRT
                elif r < 0.20:
                    t = self.GRASS2
                else:
                    t = self.GRASS
                self._tiles[(x, y)] = t
        # Scatter a few path tiles
        for _ in range(grid_size // 2):
            px = rng.randint(0, grid_size - 1)
            py = rng.randint(0, grid_size - 1)
            self._tiles[(px, py)] = self.PATH

    def get(self, x: int, y: int) -> int:
        return self._tiles.get((x, y), self.GRASS)

    COLORS = {
        GRASS:  C_TILE_GRASS,
        GRASS2: C_TILE_GRASS_2,
        FOREST: C_TILE_FOREST,
        DIRT:   C_TILE_DIRT,
        PATH:   C_TILE_PATH,
    }


# ---------------------------------------------------------------------------
# Helper: draw a castle/hideout shape with pygame.draw
# ---------------------------------------------------------------------------
def _draw_hideout(surf, cx, cy, size, is_garrison=False):
    c  = C_GARRISON      if is_garrison else C_HIDEOUT
    cd = C_GARRISON_DARK if is_garrison else C_HIDEOUT_DARK
    hw = size // 2
    # Base rectangle
    body = pygame.Rect(cx - hw + 2, cy - hw + 4, size - 4, size - 6)
    pygame.draw.rect(surf, c,  body, border_radius=3)
    pygame.draw.rect(surf, cd, body, width=2, border_radius=3)
    # Battlements
    btw = max(3, size // 6)
    for i in range(3):
        bx = cx - hw + 3 + i * (btw + 2)
        by = cy - hw
        pygame.draw.rect(surf, c, (bx, by, btw, 4))
    # Door
    dw, dh = max(4, size // 5), max(5, size // 4)
    pygame.draw.rect(surf, cd, (cx - dw//2, cy + hw - dh - 2, dw, dh),
                     border_radius=2)


def _draw_tree(surf, cx, cy, size):
    hw = size // 2
    # Trunk
    pygame.draw.rect(surf, C_TILE_DIRT, (cx - 2, cy, 4, hw // 2))
    # Canopy layers
    for layer in range(3):
        r = hw - layer * 3
        yoff = cy - layer * 4 - 2
        pygame.draw.circle(surf, C_TILE_FOREST, (cx, yoff), r)
    pygame.draw.circle(surf, C_HIDEOUT,
                       (cx, cy - hw // 2), hw - 4, width=1)


# ---------------------------------------------------------------------------
# GameRenderer
# ---------------------------------------------------------------------------
class GameRenderer:
    """Renders the simulation world, HUD, and minimap."""

    def __init__(self, screen: pygame.Surface, sim: EldoriaSimulation):
        self.screen = screen
        self.sim    = sim
        self._time  = 0.0

        self._tile_size = TILE_SIZE
        self._tilemap   = TileMap(sim.grid_size)
        self._tile_surf = None    # cached pre-rendered tile layer
        self._tile_dirty = True

        # Load sprite images if available
        self._sprites: dict[str, pygame.Surface] = {}
        self._load_sprites()

        # HUD panel rect
        self.hud_rect  = pygame.Rect(
            screen.get_width() - HUD_WIDTH, 0, HUD_WIDTH, screen.get_height()
        )
        self.map_rect  = pygame.Rect(0, 0,
                                     screen.get_width() - HUD_WIDTH,
                                     screen.get_height())

        # Progress bars (reused each frame)
        self._stam_bar = ProgressBar(pygame.Rect(0, 0, 40, 5))
        self._enrg_bar = ProgressBar(pygame.Rect(0, 0, 40, 5),
                                     color_high=C_BAR_ENERGY,
                                     color_mid=C_BAR_ENERGY,
                                     color_low=C_BAR_ENERGY)

        # Camera offset (pixel) for hero mode pan
        self.cam_x = 0
        self.cam_y = 0
        self._minimap_surf: pygame.Surface | None = None

    # ------------------------------------------------------------------
    # Sprite loading
    # ------------------------------------------------------------------
    def _load_sprites(self):
        mapping = {
            "hunter":  "hunter.png",
            "knight":  "knight.png",
            "hideout": "tree.png",
            "garrison":"garrison.png",
            "bronze":  "bronze.png",
            "silver":  "silver.png",
            "gold":    "gold.png",
        }
        ts = self._tile_size
        for key, fname in mapping.items():
            path = os.path.join(ASSETS_DIR, fname)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    self._sprites[key] = pygame.transform.smoothscale(img, (ts, ts))
                except Exception:
                    pass

    def resize_sprites(self, new_ts: int):
        self._tile_size  = new_ts
        self._tile_dirty = True
        self._load_sprites()

    # ------------------------------------------------------------------
    # Tilemap caching
    # ------------------------------------------------------------------
    def _build_tile_surface(self):
        gs  = self.sim.grid_size
        ts  = self._tile_size
        s   = pygame.Surface((gs * ts, gs * ts))
        for x in range(gs):
            for y in range(gs):
                tt  = self._tilemap.get(x, y)
                col = TileMap.COLORS.get(tt, C_TILE_GRASS)
                pygame.draw.rect(s, col, (x*ts, y*ts, ts, ts))
        # Grid overlay
        for x in range(gs + 1):
            pygame.draw.line(s, C_GRID, (x*ts, 0), (x*ts, gs*ts), 1)
        for y in range(gs + 1):
            pygame.draw.line(s, C_GRID, (0, y*ts), (gs*ts, y*ts), 1)
        self._tile_surf  = s
        self._tile_dirty = False

    # ------------------------------------------------------------------
    # Fit tile size to map area
    # ------------------------------------------------------------------
    def fit_tile_size(self):
        gs  = self.sim.grid_size
        mw  = self.map_rect.width
        mh  = self.map_rect.height
        new_ts = max(8, min(mw // gs, mh // gs))
        if new_ts != self._tile_size:
            self.resize_sprites(new_ts)
        return new_ts

    # ------------------------------------------------------------------
    # Main draw
    # ------------------------------------------------------------------
    def draw(self, dt: float, cam=(0, 0)):
        self._time += dt
        self.cam_x, self.cam_y = cam

        # Compute tile size
        ts = self.fit_tile_size()
        if self._tile_dirty:
            self._build_tile_surface()

        # Draw map background (clipped to map_rect)
        self.screen.fill(C_BG, self.map_rect)
        self.screen.set_clip(self.map_rect)
        map_surf = self._tile_surf
        if map_surf:
            self.screen.blit(map_surf, self.map_rect.topleft,
                             area=pygame.Rect(self.cam_x, self.cam_y,
                                             self.map_rect.width,
                                             self.map_rect.height))
        # Draw entities
        self._draw_entities(ts)
        self.screen.set_clip(None)

        # HUD
        self._draw_hud()

        # Minimap (inside HUD)
        self._draw_minimap()

    def _world_to_screen(self, pos, ts: int):
        wx = pos[0] * ts - self.cam_x + self.map_rect.left
        wy = pos[1] * ts - self.cam_y + self.map_rect.top
        return int(wx), int(wy)

    # ------------------------------------------------------------------
    # Entity drawing
    # ------------------------------------------------------------------
    def _draw_entities(self, ts: int):
        t = self._time
        bob = int(math.sin(t * BOB_SPEED) * BOB_AMOUNT)
        pulse = 0.5 + 0.5 * math.sin(t * PULSE_SPEED)

        # Draw order: treasures → buildings → hunters → knights
        treasures = [e for e in self.sim.entities if isinstance(e, Treasure)]
        buildings = [e for e in self.sim.entities
                     if isinstance(e, (Hideout, Garrison))]
        hunters   = [e for e in self.sim.entities if isinstance(e, Hunter)]
        knights   = [e for e in self.sim.entities if isinstance(e, Knight)]

        for e in treasures:
            self._draw_treasure(e, ts, pulse)
        for e in buildings:
            self._draw_building(e, ts)
        for e in hunters:
            self._draw_hunter(e, ts, bob)
        for e in knights:
            self._draw_knight(e, ts, bob)

    def _draw_treasure(self, e: Treasure, ts: int, pulse: float):
        sx, sy = self._world_to_screen(e.position, ts)
        cx, cy = sx + ts // 2, sy + ts // 2
        mr = self.map_rect
        if not (mr.left <= sx < mr.right and mr.top <= sy < mr.bottom):
            return
        c = {EntityType.TREASURE_BRONZE: C_TREASURE_BRONZE,
             EntityType.TREASURE_SILVER: C_TREASURE_SILVER,
             EntityType.TREASURE_GOLD:   C_TREASURE_GOLD}.get(e.entity_type, C_TREASURE_GOLD)
        key = {EntityType.TREASURE_BRONZE: "bronze",
               EntityType.TREASURE_SILVER: "silver",
               EntityType.TREASURE_GOLD:   "gold"}.get(e.entity_type)

        if key and key in self._sprites:
            self.screen.blit(self._sprites[key], (sx, sy))
        else:
            # Glow
            r_glow = int(ts * 0.35 + ts * 0.1 * pulse)
            glow_s = pygame.Surface((r_glow*2+2, r_glow*2+2), pygame.SRCALPHA)
            pygame.draw.circle(glow_s, (*c, 40), (r_glow+1, r_glow+1), r_glow)
            self.screen.blit(glow_s, (cx - r_glow - 1, cy - r_glow - 1))
            r = max(4, int(ts * 0.28))
            pygame.draw.circle(self.screen, c, (cx, cy), r)
            pygame.draw.circle(self.screen, C_WHITE, (cx, cy), r, 1)

    def _draw_building(self, e, ts: int):
        sx, sy = self._world_to_screen(e.position, ts)
        mr = self.map_rect
        if not (mr.left <= sx < mr.right and mr.top <= sy < mr.bottom):
            return
        cx, cy = sx + ts // 2, sy + ts // 2
        is_garrison = isinstance(e, Garrison)
        key = "garrison" if is_garrison else "hideout"

        if key in self._sprites:
            self.screen.blit(self._sprites[key], (sx, sy))
        else:
            _draw_hideout(self.screen, cx, cy, ts, is_garrison)

    def _draw_hunter(self, e: Hunter, ts: int, bob: int):
        sx, sy = self._world_to_screen(e.position, ts)
        mr = self.map_rect
        if not (mr.left <= sx < mr.right and mr.top <= sy < mr.bottom):
            return
        cx, cy = sx + ts // 2, sy + ts // 2 + bob

        c = (C_HUNTER_HERO if e.is_hero else
             {HunterSkill.NAVIGATION: C_HUNTER_NAV,
              HunterSkill.ENDURANCE:  C_HUNTER_END,
              HunterSkill.STEALTH:    C_HUNTER_STH}.get(e.skill, C_HUNTER_NAV))

        r = max(5, int(ts * 0.35))
        if e.state == HunterState.COLLAPSED:
            # Draw X
            pygame.draw.line(self.screen, C_RED, (cx-r, cy-r), (cx+r, cy+r), 2)
            pygame.draw.line(self.screen, C_RED, (cx+r, cy-r), (cx-r, cy+r), 2)
            return

        if "hunter" in self._sprites and not e.is_hero:
            self.screen.blit(self._sprites["hunter"], (sx, sy + bob))
        else:
            pygame.draw.circle(self.screen, c,    (cx, cy), r)
            pygame.draw.circle(self.screen, C_WHITE, (cx, cy), r, 1)
            # Skill dot
            dot_c = {HunterSkill.NAVIGATION: (100, 200, 255),
                     HunterSkill.ENDURANCE:  (100, 255, 150),
                     HunterSkill.STEALTH:    (220, 150, 255)}.get(e.skill, C_WHITE)
            pygame.draw.circle(self.screen, dot_c, (cx + r//2, cy - r//2), 3)

        # Treasure indicator
        if e.carried_treasure:
            tc = {EntityType.TREASURE_BRONZE: C_TREASURE_BRONZE,
                  EntityType.TREASURE_SILVER: C_TREASURE_SILVER,
                  EntityType.TREASURE_GOLD:   C_TREASURE_GOLD}.get(
                e.carried_treasure.entity_type, C_TREASURE_GOLD)
            pygame.draw.circle(self.screen, tc, (cx, cy - r - 4), 4)
            pygame.draw.circle(self.screen, C_WHITE, (cx, cy - r - 4), 4, 1)

        # Stamina bar
        bw = ts - 4
        bh = 4
        bx, by = sx + 2, sy + ts - 6
        self._stam_bar.rect = pygame.Rect(bx, by, bw, bh)
        self._stam_bar.value = e.stamina
        self._stam_bar.max_value = e.max_stamina
        self._stam_bar.draw(self.screen)

    def _draw_knight(self, e: Knight, ts: int, bob: int):
        sx, sy = self._world_to_screen(e.position, ts)
        mr = self.map_rect
        if not (mr.left <= sx < mr.right and mr.top <= sy < mr.bottom):
            return
        cx, cy = sx + ts // 2, sy + ts // 2 + bob

        c = C_KNIGHT_PURSUE if e.state == KnightState.PURSUING else C_KNIGHT

        if "knight" in self._sprites:
            self.screen.blit(self._sprites["knight"], (sx, sy + bob))
        else:
            r = max(5, int(ts * 0.35))
            # Diamond shape
            pts = [(cx, cy-r), (cx+r, cy), (cx, cy+r), (cx-r, cy)]
            pygame.draw.polygon(self.screen, c, pts)
            pygame.draw.polygon(self.screen, C_KNIGHT_DARK, pts, 2)

        # Alert indicator
        if e.state == KnightState.PURSUING:
            fs = max(10, ts // 2)
            font = get_font(fs, bold=True)
            t = font.render("!", True, C_YELLOW)
            self.screen.blit(t, (cx - t.get_width()//2, cy - ts - 2 + bob))
        elif e.state == KnightState.CHALLENGING:
            fs = max(10, ts // 2)
            font = get_font(fs, bold=True)
            t = font.render("⚔", True, C_RED)
            self.screen.blit(t, (cx - t.get_width()//2, cy - ts - 2 + bob))

        # Energy bar
        bw = ts - 4
        bh = 4
        bx, by = sx + 2, sy + ts - 6
        self._enrg_bar.rect = pygame.Rect(bx, by, bw, bh)
        self._enrg_bar.value = e.energy
        self._enrg_bar.max_value = e.max_energy
        self._enrg_bar.draw(self.screen)

    # ------------------------------------------------------------------
    # HUD
    # ------------------------------------------------------------------
    def _draw_hud(self):
        s   = self.screen
        hr  = self.hud_rect
        stats = self.sim.statistics()

        pygame.draw.rect(s, C_UI_PANEL, hr)
        pygame.draw.line(s, C_UI_BORDER, hr.topleft, hr.bottomleft, 2)

        x  = hr.left + 12
        y  = 12
        w  = hr.width - 24

        # Title
        draw_text(s, "KNIGHTS OF ELDORIA",
                  hr.centerx, y, size=16, color=C_UI_TEXT_BRIGHT,
                  bold=True, align="center", shadow=True)
        y += 26
        draw_hline(s, hr.left + 6, hr.right - 6, y, C_UI_BORDER)
        y += 8

        # Step / mode
        draw_text(s, f"Step  {stats['step']:>5}", x, y, size=15, color=C_UI_TEXT)
        y += 20
        draw_hline(s, hr.left + 6, hr.right - 6, y, C_UI_PANEL_2)
        y += 6

        # Collection progress bar
        draw_text(s, "Treasure Collected", x, y, size=14, color=C_UI_TEXT_DIM)
        y += 18
        pct = stats["pct"] / 100.0
        bar = pygame.Rect(x, y, w, 12)
        pygame.draw.rect(s, C_BAR_BG, bar, border_radius=4)
        pygame.draw.rect(s, C_BAR_BORDER, bar, width=1, border_radius=4)
        if pct > 0:
            fill = pygame.Rect(x, y, max(4, int(w * pct)), 12)
            fc = C_GREEN if pct > 0.7 else C_YELLOW if pct > 0.3 else C_RED
            pygame.draw.rect(s, fc, fill, border_radius=4)
        draw_text(s, f"{stats['pct']:.1f}%", x + w + 6, y - 2,
                  size=13, color=C_UI_TEXT_DIM)
        y += 20
        draw_hline(s, hr.left + 6, hr.right - 6, y, C_UI_BORDER)
        y += 8

        # Entity counts
        rows = [
            ("Hunters",        stats["hunters"],   C_HUNTER_NAV),
            ("Knights",        stats["knights"],   C_KNIGHT),
            ("Hideouts",       stats["hideouts"],  C_HIDEOUT),
            ("Treasures Left", stats["treasures"], C_TREASURE_GOLD),
            ("  Bronze",       stats["bronze"],    C_TREASURE_BRONZE),
            ("  Silver",       stats["silver"],    C_TREASURE_SILVER),
            ("  Gold",         stats["gold"],      C_TREASURE_GOLD),
        ]
        for label, val, col in rows:
            draw_text(s, label, x, y, size=14, color=C_UI_TEXT_DIM)
            draw_text(s, str(val), hr.right - 16, y,
                      size=14, color=col, align="right", bold=True)
            y += 18

        draw_hline(s, hr.left + 6, hr.right - 6, y, C_UI_BORDER)
        y += 6
        draw_text(s, f"Score  {stats['score']:>7,}", x, y,
                  size=16, color=C_UI_TEXT_BRIGHT, bold=True)
        y += 24

        self._hud_bottom_y = y   # used by play state for event log etc.

    # ------------------------------------------------------------------
    # Minimap
    # ------------------------------------------------------------------
    def _draw_minimap(self):
        hr  = self.hud_rect
        ms  = MINIMAP_SIZE
        mp  = MINIMAP_PAD
        mx  = hr.left + (hr.width - ms) // 2
        my  = hr.bottom - ms - mp
        mr  = pygame.Rect(mx, my, ms, ms)

        pygame.draw.rect(self.screen, C_UI_PANEL_2, mr)
        pygame.draw.rect(self.screen, C_UI_BORDER, mr, width=1)

        gs    = self.sim.grid_size
        scale = ms / gs

        # Tile base colors (fast)
        for x in range(gs):
            for y in range(gs):
                tc  = TileMap.COLORS.get(self._tilemap.get(x, y), C_TILE_GRASS)
                px  = int(mx + x * scale)
                py  = int(my + y * scale)
                pw  = max(1, int(scale))
                pygame.draw.rect(self.screen, tc, (px, py, pw, pw))

        # Entities
        for e in self.sim.entities:
            x, y = e.position
            px   = int(mx + x * scale)
            py   = int(my + y * scale)
            r    = max(1, int(scale * 0.8))
            if isinstance(e, Hunter):
                c = C_HUNTER_HERO if e.is_hero else C_HUNTER_NAV
            elif isinstance(e, Knight):
                c = C_KNIGHT
            elif isinstance(e, Treasure):
                c = {EntityType.TREASURE_BRONZE: C_TREASURE_BRONZE,
                     EntityType.TREASURE_SILVER: C_TREASURE_SILVER,
                     EntityType.TREASURE_GOLD:   C_TREASURE_GOLD}.get(e.entity_type, C_WHITE)
            elif isinstance(e, Hideout):
                c = C_HIDEOUT
            elif isinstance(e, Garrison):
                c = C_GARRISON
            else:
                continue
            pygame.draw.circle(self.screen, c, (px, py), r)

        draw_text(self.screen, "MAP", mx + ms // 2, my - 18,
                  size=13, color=C_UI_TEXT_DIM, bold=True, align="center")


# ---------------------------------------------------------------------------
# Fade transition helper
# ---------------------------------------------------------------------------
class FadeTransition:
    def __init__(self, duration: float = 0.4):
        self.duration = duration
        self._t       = 0.0
        self._mode    = "none"   # "in" | "out" | "none"
        self._done    = False

    @property
    def done(self):
        return self._done

    def fade_in(self):
        self._t    = 0.0
        self._mode = "in"
        self._done = False

    def fade_out(self):
        self._t    = 0.0
        self._mode = "out"
        self._done = False

    def update(self, dt: float):
        if self._mode == "none":
            return
        self._t += dt / self.duration
        if self._t >= 1.0:
            self._t    = 1.0
            self._done = True
            self._mode = "none"

    def draw(self, surface: pygame.Surface):
        if self._mode == "none" and not self._done:
            return
        alpha = int(255 * (1.0 - self._t) if self._mode == "in" else 255 * self._t)
        if alpha <= 0:
            return
        s = pygame.Surface(surface.get_size())
        s.fill(C_BLACK)
        s.set_alpha(alpha)
        surface.blit(s, (0, 0))
