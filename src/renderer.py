"""
All rendering: map tiles, entities, HUD panel, minimap, screen transitions.
Commercial-quality visual overhaul — tiles fill the full map area.
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
        self._detail = {}   # sub-tile detail points for texture
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
                # Random detail dots for texture variety
                if rng.random() < 0.35:
                    self._detail[(x, y)] = (
                        rng.uniform(0.2, 0.8),
                        rng.uniform(0.2, 0.8),
                        rng.randint(1, 2),
                    )
        # Scatter path tiles in cross patterns for roads
        for _ in range(grid_size // 2):
            px = rng.randint(1, grid_size - 2)
            py = rng.randint(1, grid_size - 2)
            self._tiles[(px, py)] = self.PATH
            # Extend path naturally
            for _ in range(rng.randint(2, 5)):
                step = rng.choice([(1,0),(-1,0),(0,1),(0,-1)])
                px = max(0, min(grid_size-1, px + step[0]))
                py = max(0, min(grid_size-1, py + step[1]))
                self._tiles[(px, py)] = self.PATH

    def get(self, x: int, y: int) -> int:
        return self._tiles.get((x, y), self.GRASS)

    def get_detail(self, x: int, y: int):
        return self._detail.get((x, y))

    COLORS = {
        GRASS:  C_TILE_GRASS,
        GRASS2: C_TILE_GRASS_2,
        FOREST: C_TILE_FOREST,
        DIRT:   C_TILE_DIRT,
        PATH:   C_TILE_PATH,
    }

    # Slightly lighter shade for detail dots on each tile type
    DETAIL_COLORS = {
        GRASS:  (68, 138, 55),
        GRASS2: (60, 122, 48),
        FOREST: (40,  92, 40),
        DIRT:   (158, 118, 72),
        PATH:   (188, 152, 95),
    }


# ---------------------------------------------------------------------------
# Helper: castle / hideout shape
# ---------------------------------------------------------------------------
def _draw_hideout(surf, cx, cy, tw, th, is_garrison=False):
    c  = C_GARRISON      if is_garrison else C_HIDEOUT
    cd = C_GARRISON_DARK if is_garrison else C_HIDEOUT_DARK
    hw = min(tw, th) // 2
    body = pygame.Rect(cx - hw + 2, cy - hw + 4, hw*2 - 4, hw*2 - 6)
    pygame.draw.rect(surf, c,  body, border_radius=3)
    pygame.draw.rect(surf, cd, body, width=2, border_radius=3)
    # Battlements
    btw = max(3, hw // 3)
    for i in range(3):
        bx = cx - hw + 3 + i * (btw + 2)
        by = cy - hw
        pygame.draw.rect(surf, c, (bx, by, btw, 4))
    # Door arch
    dw, dh = max(4, hw // 2), max(5, hw // 2)
    pygame.draw.rect(surf, cd, (cx - dw//2, cy + hw - dh - 2, dw, dh),
                     border_radius=2)
    # Window slits
    pygame.draw.rect(surf, cd, (cx - hw//2, cy - 2, max(2, hw//4), max(4, hw//3)))
    pygame.draw.rect(surf, cd, (cx + hw//6, cy - 2, max(2, hw//4), max(4, hw//3)))


def _draw_tree(surf, cx, cy, tw, th):
    hw = min(tw, th) // 2
    # Trunk
    pygame.draw.rect(surf, C_TILE_DIRT, (cx - 2, cy, 4, hw // 2))
    # Canopy — three layered circles
    colors = [
        (int(C_TILE_FOREST[0] * 1.2), int(C_TILE_FOREST[1] * 1.2), int(C_TILE_FOREST[2] * 1.2)),
        C_TILE_FOREST,
        (max(0, C_TILE_FOREST[0]-10), max(0, C_TILE_FOREST[1]-10), max(0, C_TILE_FOREST[2]-10)),
    ]
    for i, cc in enumerate(colors):
        r = hw - i * 2
        yoff = cy - i * 3 - 2
        pygame.draw.circle(surf, cc, (cx, yoff), max(2, r))
    pygame.draw.circle(surf, C_HIDEOUT, (cx, cy - hw // 2), max(1, hw - 4), width=1)


# ---------------------------------------------------------------------------
# GameRenderer
# ---------------------------------------------------------------------------
class GameRenderer:
    """Renders the simulation world, HUD, and minimap."""

    def __init__(self, screen: pygame.Surface, sim: EldoriaSimulation):
        self.screen = screen
        self.sim    = sim
        self._time  = 0.0

        # Tile dimensions — w (x) and h (y) may differ to fill map area
        self._tile_w = TILE_SIZE
        self._tile_h = TILE_SIZE
        self._tile_size = TILE_SIZE   # min(tw, th) kept for backward compat

        self._tilemap    = TileMap(sim.grid_size)
        self._tile_surf  = None
        self._tile_dirty = True

        # Sprite images (optional PNG assets)
        self._sprites: dict[str, pygame.Surface] = {}
        self._load_sprites()

        # Layout rects
        self.hud_rect = pygame.Rect(
            screen.get_width() - HUD_WIDTH, 0, HUD_WIDTH, screen.get_height()
        )
        self.map_rect = pygame.Rect(
            0, 0, screen.get_width() - HUD_WIDTH, screen.get_height()
        )

        # Reusable progress bars
        self._stam_bar = ProgressBar(pygame.Rect(0, 0, 40, 5))
        self._enrg_bar = ProgressBar(pygame.Rect(0, 0, 40, 5),
                                     color_high=C_BAR_ENERGY,
                                     color_mid=C_BAR_ENERGY,
                                     color_low=C_BAR_ENERGY)

        # Camera offset (pixels)
        self.cam_x = 0
        self.cam_y = 0
        self._minimap_surf = None

        # HUD bottom y — set by _draw_hud, read by play state
        self._hud_bottom_y = 200

    # ------------------------------------------------------------------
    # Sprite loading
    # ------------------------------------------------------------------
    def _load_sprites(self):
        mapping = {
            "hunter":   "hunter.png",
            "knight":   "knight.png",
            "hideout":  "hideout.png",
            "garrison": "garrison.png",
            "bronze":   "bronze.png",
            "silver":   "silver.png",
            "gold":     "gold.png",
        }
        ts = min(self._tile_w, self._tile_h)
        for key, fname in mapping.items():
            path = os.path.join(ASSETS_DIR, fname)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    self._sprites[key] = pygame.transform.smoothscale(img, (ts, ts))
                except Exception:
                    pass

    def resize_sprites(self):
        self._tile_dirty = True
        self._load_sprites()

    # ------------------------------------------------------------------
    # Tile size — fills the ENTIRE map area with non-square tiles
    # ------------------------------------------------------------------
    def fit_tile_size(self):
        gs  = self.sim.grid_size
        mw  = self.map_rect.width
        mh  = self.map_rect.height
        tw  = max(8, mw // gs)
        th  = max(8, mh // gs)
        ts  = min(tw, th)
        if tw != self._tile_w or th != self._tile_h:
            self._tile_w    = tw
            self._tile_h    = th
            self._tile_size = ts
            self.resize_sprites()
        return tw, th

    # ------------------------------------------------------------------
    # Tile surface cache — sized to fill the full map area
    # ------------------------------------------------------------------
    def _build_tile_surface(self):
        gs  = self.sim.grid_size
        tw  = self._tile_w
        th  = self._tile_h
        surf_w = gs * tw
        surf_h = gs * th
        s = pygame.Surface((surf_w, surf_h))

        for x in range(gs):
            for y in range(gs):
                tt  = self._tilemap.get(x, y)
                col = TileMap.COLORS.get(tt, C_TILE_GRASS)
                pygame.draw.rect(s, col, (x*tw, y*th, tw, th))

                # Sub-tile texture detail
                detail = self._tilemap.get_detail(x, y)
                if detail and tw >= 10 and th >= 10:
                    dx_f, dy_f, dr = detail
                    dc = TileMap.DETAIL_COLORS.get(tt, col)
                    px = int(x*tw + dx_f * tw)
                    py = int(y*th + dy_f * th)
                    pygame.draw.circle(s, dc, (px, py), dr)

                # Forest tiles get a small tree indicator
                if tt == TileMap.FOREST and tw >= 12 and th >= 12:
                    _draw_tree(s, x*tw + tw//2, y*th + th//2, tw, th)

        # Subtle grid lines
        for xi in range(gs + 1):
            pygame.draw.line(s, C_GRID, (xi*tw, 0), (xi*tw, surf_h), 1)
        for yi in range(gs + 1):
            pygame.draw.line(s, C_GRID, (0, yi*th), (surf_w, yi*th), 1)

        self._tile_surf  = s
        self._tile_dirty = False

    # ------------------------------------------------------------------
    # World → screen coordinate conversion
    # ------------------------------------------------------------------
    def _world_to_screen(self, pos):
        wx = pos[0] * self._tile_w - self.cam_x + self.map_rect.left
        wy = pos[1] * self._tile_h - self.cam_y + self.map_rect.top
        return int(wx), int(wy)

    # ------------------------------------------------------------------
    # Main draw entry point
    # ------------------------------------------------------------------
    def draw(self, dt: float, cam=(0, 0)):
        self._time += dt
        self.cam_x, self.cam_y = cam

        self.fit_tile_size()
        if self._tile_dirty:
            self._build_tile_surface()

        # Fill map background and blit tile surface
        self.screen.fill(C_BG, self.map_rect)
        self.screen.set_clip(self.map_rect)
        if self._tile_surf:
            self.screen.blit(
                self._tile_surf,
                self.map_rect.topleft,
                area=pygame.Rect(self.cam_x, self.cam_y,
                                 self.map_rect.width, self.map_rect.height),
            )

        # Entities
        self._draw_entities()
        self.screen.set_clip(None)

        # HUD panels
        self._draw_hud()
        self._draw_minimap()

    # ------------------------------------------------------------------
    # Entity drawing
    # ------------------------------------------------------------------
    def _draw_entities(self):
        t     = self._time
        bob   = int(math.sin(t * BOB_SPEED) * BOB_AMOUNT)
        pulse = 0.5 + 0.5 * math.sin(t * PULSE_SPEED)

        treasures = [e for e in self.sim.entities if isinstance(e, Treasure)]
        buildings = [e for e in self.sim.entities if isinstance(e, (Hideout, Garrison))]
        hunters   = [e for e in self.sim.entities if isinstance(e, Hunter)]
        knights   = [e for e in self.sim.entities if isinstance(e, Knight)]

        for e in treasures:
            self._draw_treasure(e, pulse)
        for e in buildings:
            self._draw_building(e)
        for e in hunters:
            self._draw_hunter(e, bob)
        for e in knights:
            self._draw_knight(e, bob)

    def _draw_treasure(self, e: Treasure, pulse: float):
        tw, th = self._tile_w, self._tile_h
        ts = self._tile_size
        sx, sy = self._world_to_screen(e.position)
        cx, cy = sx + tw // 2, sy + th // 2
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
            # Pulsing glow ring
            r_glow = int(ts * 0.38 + ts * 0.12 * pulse)
            glow_s = pygame.Surface((r_glow*2+4, r_glow*2+4), pygame.SRCALPHA)
            gc = (*c, 50)
            pygame.draw.circle(glow_s, gc, (r_glow+2, r_glow+2), r_glow)
            self.screen.blit(glow_s, (cx - r_glow - 2, cy - r_glow - 2))
            # Core gem
            r = max(4, int(ts * 0.30))
            pygame.draw.circle(self.screen, c, (cx, cy), r)
            # Highlight shimmer
            hi = tuple(min(255, int(v * 1.5)) for v in c[:3])
            pygame.draw.circle(self.screen, hi, (cx - r//3, cy - r//3), max(2, r//3))
            pygame.draw.circle(self.screen, C_WHITE, (cx, cy), r, 1)

    def _draw_building(self, e):
        tw, th = self._tile_w, self._tile_h
        sx, sy = self._world_to_screen(e.position)
        mr = self.map_rect
        if not (mr.left <= sx < mr.right and mr.top <= sy < mr.bottom):
            return
        cx, cy = sx + tw // 2, sy + th // 2
        is_garrison = isinstance(e, Garrison)
        key = "garrison" if is_garrison else "hideout"

        if key in self._sprites:
            self.screen.blit(self._sprites[key], (sx, sy))
        else:
            _draw_hideout(self.screen, cx, cy, tw, th, is_garrison)

    def _draw_hunter(self, e: Hunter, bob: int):
        tw, th = self._tile_w, self._tile_h
        ts = self._tile_size
        sx, sy = self._world_to_screen(e.position)
        mr = self.map_rect
        if not (mr.left <= sx < mr.right and mr.top <= sy < mr.bottom):
            return
        cx, cy = sx + tw // 2, sy + th // 2 + bob

        c = (C_HUNTER_HERO if e.is_hero else
             {HunterSkill.NAVIGATION: C_HUNTER_NAV,
              HunterSkill.ENDURANCE:  C_HUNTER_END,
              HunterSkill.STEALTH:    C_HUNTER_STH}.get(e.skill, C_HUNTER_NAV))

        r = max(5, int(ts * 0.36))

        if e.state == HunterState.COLLAPSED:
            pygame.draw.line(self.screen, C_RED, (cx-r, cy-r), (cx+r, cy+r), 2)
            pygame.draw.line(self.screen, C_RED, (cx+r, cy-r), (cx-r, cy+r), 2)
            return

        if "hunter" in self._sprites and not e.is_hero:
            self.screen.blit(self._sprites["hunter"], (sx, sy + bob))
        else:
            # Shadow
            pygame.draw.ellipse(self.screen, (0, 0, 0),
                                (cx - r, cy + r - 2, r*2, 4))
            # Body circle
            pygame.draw.circle(self.screen, c, (cx, cy), r)
            # Outline
            outline = tuple(min(255, int(v * 1.4)) for v in c[:3])
            pygame.draw.circle(self.screen, outline, (cx, cy), r, 2)
            # Skill-coloured inner dot
            dot_c = {HunterSkill.NAVIGATION: (120, 210, 255),
                     HunterSkill.ENDURANCE:  (120, 255, 165),
                     HunterSkill.STEALTH:    (230, 165, 255)}.get(e.skill, C_WHITE)
            pygame.draw.circle(self.screen, dot_c, (cx + r//3, cy - r//3), max(2, r//3))

            # Hero: gold crown ring
            if e.is_hero:
                pygame.draw.circle(self.screen, C_TREASURE_GOLD, (cx, cy), r + 3, 2)

        # Carried treasure indicator (gem above head)
        if e.carried_treasure:
            tc = {EntityType.TREASURE_BRONZE: C_TREASURE_BRONZE,
                  EntityType.TREASURE_SILVER: C_TREASURE_SILVER,
                  EntityType.TREASURE_GOLD:   C_TREASURE_GOLD}.get(
                e.carried_treasure.entity_type, C_TREASURE_GOLD)
            pygame.draw.circle(self.screen, tc, (cx, cy - r - 5), 4)
            pygame.draw.circle(self.screen, C_WHITE, (cx, cy - r - 5), 4, 1)

        # Stamina bar below entity
        bw = max(4, tw - 4)
        bh = 4
        bx, by = sx + 2, sy + th - 6
        self._stam_bar.rect = pygame.Rect(bx, by, bw, bh)
        self._stam_bar.value     = e.stamina
        self._stam_bar.max_value = e.max_stamina
        self._stam_bar.draw(self.screen)

    def _draw_knight(self, e: Knight, bob: int):
        tw, th = self._tile_w, self._tile_h
        ts = self._tile_size
        sx, sy = self._world_to_screen(e.position)
        mr = self.map_rect
        if not (mr.left <= sx < mr.right and mr.top <= sy < mr.bottom):
            return
        cx, cy = sx + tw // 2, sy + th // 2 + bob

        pursuing = e.state == KnightState.PURSUING
        c = C_KNIGHT_PURSUE if pursuing else C_KNIGHT

        if "knight" in self._sprites:
            self.screen.blit(self._sprites["knight"], (sx, sy + bob))
        else:
            r = max(5, int(ts * 0.36))
            # Shadow
            pygame.draw.ellipse(self.screen, (0, 0, 0),
                                (cx - r, cy + r - 2, r*2, 4))
            # Diamond shield shape
            pts = [(cx, cy-r), (cx+r, cy), (cx, cy+r), (cx-r, cy)]
            pygame.draw.polygon(self.screen, c, pts)
            pygame.draw.polygon(self.screen, C_KNIGHT_DARK, pts, 2)
            # Inner cross detail
            half = r // 2
            pygame.draw.line(self.screen, C_KNIGHT_DARK, (cx, cy-half), (cx, cy+half), 1)
            pygame.draw.line(self.screen, C_KNIGHT_DARK, (cx-half, cy), (cx+half, cy), 1)

        # State indicator (! or X above)
        if e.state == KnightState.PURSUING:
            fs = max(10, ts // 2)
            font = get_font(fs, bold=True)
            t = font.render("!", True, C_YELLOW)
            self.screen.blit(t, (cx - t.get_width()//2, cy - ts - 2 + bob))
        elif e.state == KnightState.CHALLENGING:
            fs = max(10, ts // 2)
            font = get_font(fs, bold=True)
            t = font.render("X", True, C_RED)
            self.screen.blit(t, (cx - t.get_width()//2, cy - ts - 2 + bob))

        # Energy bar below entity
        bw = max(4, tw - 4)
        bh = 4
        bx, by = sx + 2, sy + th - 6
        self._enrg_bar.rect = pygame.Rect(bx, by, bw, bh)
        self._enrg_bar.value     = e.energy
        self._enrg_bar.max_value = e.max_energy
        self._enrg_bar.draw(self.screen)

    # ------------------------------------------------------------------
    # HUD  (right panel)
    # ------------------------------------------------------------------
    def _draw_hud(self):
        s   = self.screen
        hr  = self.hud_rect
        stats = self.sim.statistics()

        # Panel background with a subtle gradient effect (two rects)
        pygame.draw.rect(s, C_UI_PANEL, hr)
        inner = hr.inflate(-4, 0)
        inner.left += 2
        pygame.draw.rect(s, (C_UI_PANEL[0]+4, C_UI_PANEL[1]+3, C_UI_PANEL[2]+1), inner)
        pygame.draw.line(s, C_UI_BORDER, hr.topleft, hr.bottomleft, 2)

        x  = hr.left + 14
        y  = 14
        w  = hr.width - 28

        # ── Title ──
        draw_text(s, "KNIGHTS OF ELDORIA",
                  hr.centerx, y, size=15, color=C_UI_TEXT_BRIGHT,
                  bold=True, align="center", shadow=True)
        y += 24
        # Gold divider with gem
        pygame.draw.line(s, C_UI_BORDER, (hr.left+8, y), (hr.right-8, y), 1)
        pygame.draw.circle(s, C_TREASURE_GOLD, (hr.centerx, y), 4)
        y += 10

        # ── Step / Simulation ──
        draw_text(s, f"Step  {stats['step']:>5}", x, y, size=14, color=C_UI_TEXT)
        y += 20
        pygame.draw.line(s, C_UI_PANEL_2, (hr.left+6, y), (hr.right-6, y), 1)
        y += 6

        # ── Treasure Progress ──
        draw_text(s, "TREASURE PROGRESS", x, y, size=12,
                  color=C_UI_TEXT_DIM, bold=True)
        y += 16
        pct   = stats["pct"] / 100.0
        bar_r = pygame.Rect(x, y, w, 14)
        pygame.draw.rect(s, C_BAR_BG, bar_r, border_radius=5)
        pygame.draw.rect(s, C_BAR_BORDER, bar_r, width=1, border_radius=5)
        if pct > 0:
            fill_w = max(6, int(w * pct))
            fill_r = pygame.Rect(x, y, fill_w, 14)
            fc = C_GREEN if pct > 0.7 else C_YELLOW if pct > 0.3 else C_RED
            pygame.draw.rect(s, fc, fill_r, border_radius=5)
            # Shine
            shine = pygame.Rect(x+2, y+2, max(2, fill_w-4), 3)
            shine_c = tuple(min(255, int(v*1.4)) for v in fc[:3])
            pygame.draw.rect(s, shine_c, shine, border_radius=2)
        pct_txt = f"{stats['pct']:.1f}%"
        draw_text(s, pct_txt, hr.right - 10, y - 1,
                  size=13, color=C_UI_TEXT_DIM, align="right")
        y += 20
        pygame.draw.line(s, C_UI_BORDER, (hr.left+6, y), (hr.right-6, y), 1)
        y += 8

        # ── Entity Counts ──
        draw_text(s, "ENTITIES", x, y, size=12, color=C_UI_TEXT_DIM, bold=True)
        y += 16
        rows = [
            ("Hunters",  stats["hunters"],   C_HUNTER_NAV),
            ("Knights",  stats["knights"],   C_KNIGHT),
            ("Hideouts", stats["hideouts"],  C_HIDEOUT),
        ]
        for label, val, col in rows:
            draw_text(s, label, x + 4, y, size=14, color=C_UI_TEXT_DIM)
            draw_text(s, str(val), hr.right - 14, y,
                      size=14, color=col, align="right", bold=True)
            y += 18

        pygame.draw.line(s, C_UI_PANEL_2, (hr.left+6, y), (hr.right-6, y), 1)
        y += 6

        # ── Treasure Breakdown ──
        draw_text(s, "TREASURES", x, y, size=12, color=C_UI_TEXT_DIM, bold=True)
        y += 16
        treasure_rows = [
            ("  On Map",  stats["treasures"], C_TREASURE_GOLD),
            ("  Bronze",  stats["bronze"],    C_TREASURE_BRONZE),
            ("  Silver",  stats["silver"],    C_TREASURE_SILVER),
            ("  Gold",    stats["gold"],      C_TREASURE_GOLD),
        ]
        for label, val, col in treasure_rows:
            draw_text(s, label, x + 4, y, size=13, color=C_UI_TEXT_DIM)
            draw_text(s, str(val), hr.right - 14, y,
                      size=13, color=col, align="right", bold=True)
            y += 17

        pygame.draw.line(s, C_UI_BORDER, (hr.left+6, y), (hr.right-6, y), 1)
        y += 8

        # ── Score ──
        draw_text(s, "SCORE", x, y, size=12, color=C_UI_TEXT_DIM, bold=True)
        y += 16
        draw_text(s, f"{stats['score']:,}", hr.centerx, y,
                  size=22, color=C_UI_TEXT_BRIGHT, bold=True, align="center", shadow=True)
        y += 28

        self._hud_bottom_y = y

    # ------------------------------------------------------------------
    # Minimap
    # ------------------------------------------------------------------
    def _draw_minimap(self):
        hr = self.hud_rect
        ms = MINIMAP_SIZE
        mp = MINIMAP_PAD
        mx = hr.left + (hr.width - ms) // 2
        my = hr.bottom - ms - mp
        mr = pygame.Rect(mx, my, ms, ms)

        # Background
        pygame.draw.rect(self.screen, C_UI_PANEL_2, mr)
        pygame.draw.rect(self.screen, C_UI_BORDER, mr, width=1)

        gs    = self.sim.grid_size
        scale = ms / gs

        # Tile base
        for x in range(gs):
            for y in range(gs):
                tc = TileMap.COLORS.get(self._tilemap.get(x, y), C_TILE_GRASS)
                px = int(mx + x * scale)
                py = int(my + y * scale)
                pw = max(1, int(scale))
                pygame.draw.rect(self.screen, tc, (px, py, pw, pw))

        # Camera viewport indicator
        if self._tile_w > 0 and self._tile_h > 0:
            vx = int(mx + self.cam_x / self._tile_w * scale)
            vy = int(my + self.cam_y / self._tile_h * scale)
            vw = int(self.map_rect.width  / self._tile_w * scale)
            vh = int(self.map_rect.height / self._tile_h * scale)
            vr = pygame.Rect(vx, vy, vw, vh).clip(mr)
            if vr.width > 0 and vr.height > 0:
                pygame.draw.rect(self.screen, C_UI_BORDER_HI, vr, width=1)

        # Entities
        for e in self.sim.entities:
            ex, ey = e.position
            px = int(mx + ex * scale)
            py = int(my + ey * scale)
            r  = max(1, int(scale * 0.85))
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

        # Label
        draw_text(self.screen, "MINIMAP", mx + ms // 2, my - 18,
                  size=12, color=C_UI_TEXT_DIM, bold=True, align="center")


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
