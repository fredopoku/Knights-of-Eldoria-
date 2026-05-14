"""
GameRenderer — dark-fantasy "glowing world" style.
draw() always takes the current surface as its first argument so the
renderer NEVER holds a stale surface reference (root cause of black screens).
"""
from __future__ import annotations
import math
import os
import random
import pygame
from src.constants import (
    TILE_SIZE, GRID_SIZE, HUD_WIDTH, MINIMAP_SIZE, MINIMAP_PAD,
    C_BG, C_TILE_GRASS, C_TILE_GRASS_2, C_TILE_FOREST,
    C_TILE_DIRT, C_TILE_PATH, C_GRID,
    C_HUNTER_NAV, C_HUNTER_END, C_HUNTER_STH, C_HUNTER_HERO,
    C_KNIGHT, C_KNIGHT_DARK, C_KNIGHT_PURSUE,
    C_TREASURE_BRONZE, C_TREASURE_SILVER, C_TREASURE_GOLD,
    C_HIDEOUT, C_HIDEOUT_DARK, C_GARRISON, C_GARRISON_DARK,
    C_UI_PANEL, C_UI_PANEL_2, C_UI_BORDER, C_UI_BORDER_HI,
    C_UI_TEXT, C_UI_TEXT_DIM, C_UI_TEXT_BRIGHT, C_UI_ACCENT,
    C_BAR_BG, C_BAR_BORDER,
    C_BAR_STAMINA_HI, C_BAR_STAMINA_MID, C_BAR_STAMINA_LOW, C_BAR_ENERGY,
    C_GREEN, C_RED, C_YELLOW, C_WHITE, C_BLACK,
    BOB_SPEED, BOB_AMOUNT, PULSE_SPEED,
    ASSETS_DIR,
)
from src.simulation import (
    EntityType, HunterSkill, HunterState, KnightState,
    Hunter, Knight, Treasure, Hideout, Garrison, EldoriaSimulation,
)
from src.ui import draw_text, draw_panel, draw_hline, get_font, ProgressBar


# ---------------------------------------------------------------------------
# Glow surface factory
# ---------------------------------------------------------------------------
_glow_cache: dict[tuple, pygame.Surface] = {}

def make_glow(radius: int, color: tuple, rings: int = 4, peak: int = 110) -> pygame.Surface:
    key = (radius, color[:3], rings, peak)
    if key in _glow_cache:
        return _glow_cache[key]
    size = radius * 2 * (rings + 1)
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    for i in range(rings, 0, -1):
        r = radius * i
        a = max(0, min(255, peak * (rings - i + 1) // (rings * rings)))
        if r > 0:
            pygame.draw.circle(surf, (*color[:3], a), (cx, cy), r)
    _glow_cache[key] = surf
    return surf


# ---------------------------------------------------------------------------
# Procedural tile map
# ---------------------------------------------------------------------------
class TileMap:
    GRASS  = 0
    GRASS2 = 1
    FOREST = 2
    DIRT   = 3
    PATH   = 4

    COLORS = {
        GRASS:  C_TILE_GRASS,
        GRASS2: C_TILE_GRASS_2,
        FOREST: C_TILE_FOREST,
        DIRT:   C_TILE_DIRT,
        PATH:   C_TILE_PATH,
    }

    def __init__(self, grid_size: int, seed: int = 42):
        rng = random.Random(seed)
        self._tiles  = {}
        self._detail = {}
        for x in range(grid_size):
            for y in range(grid_size):
                r = rng.random()
                if r < 0.05:
                    t = self.FOREST
                elif r < 0.10:
                    t = self.DIRT
                elif r < 0.22:
                    t = self.GRASS2
                else:
                    t = self.GRASS
                self._tiles[(x, y)] = t
                if rng.random() < 0.38:
                    self._detail[(x, y)] = (
                        rng.uniform(0.18, 0.82),
                        rng.uniform(0.18, 0.82),
                        rng.randint(1, 2),
                    )
        # Organic road paths
        for _ in range(grid_size // 3):
            px, py = rng.randint(1, grid_size-2), rng.randint(1, grid_size-2)
            for _ in range(rng.randint(3, 8)):
                self._tiles[(px, py)] = self.PATH
                step = rng.choice([(1,0),(-1,0),(0,1),(0,-1)])
                px = max(0, min(grid_size-1, px+step[0]))
                py = max(0, min(grid_size-1, py+step[1]))

    def get(self, x, y): return self._tiles.get((x, y), self.GRASS)
    def detail(self, x, y): return self._detail.get((x, y))


# ---------------------------------------------------------------------------
# Building drawing helpers
# ---------------------------------------------------------------------------
def _draw_castle(surf, cx, cy, sz, is_garrison):
    c  = C_GARRISON      if is_garrison else C_HIDEOUT
    cd = C_GARRISON_DARK if is_garrison else C_HIDEOUT_DARK
    hw = sz // 2
    # Base
    body = pygame.Rect(cx-hw+2, cy-hw+4, hw*2-4, hw*2-5)
    pygame.draw.rect(surf, c,  body, border_radius=3)
    pygame.draw.rect(surf, cd, body, width=2, border_radius=3)
    # Battlements
    bw = max(3, sz//7)
    for i in range(3):
        bx = cx - hw + 3 + i*(bw+2)
        pygame.draw.rect(surf, c, (bx, cy-hw, bw, 4))
    # Door
    dw, dh = max(4, sz//5), max(5, sz//4)
    pygame.draw.rect(surf, cd, (cx-dw//2, cy+hw-dh-2, dw, dh), border_radius=2)
    # Windows
    ew = max(2, sz//8)
    pygame.draw.rect(surf, cd, (cx-hw//2, cy-2, ew, max(4, sz//5)))
    pygame.draw.rect(surf, cd, (cx+hw//4, cy-2, ew, max(4, sz//5)))
    # Warm window glow
    wg_col = (200, 140, 50) if not is_garrison else (200, 80, 60)
    pygame.draw.rect(surf, wg_col, (cx-hw//2+1, cy-1, max(1, ew-2), max(2, sz//6)))
    pygame.draw.rect(surf, wg_col, (cx+hw//4+1, cy-1, max(1, ew-2), max(2, sz//6)))


# ---------------------------------------------------------------------------
# GameRenderer
# ---------------------------------------------------------------------------
class GameRenderer:
    def __init__(self, sim: EldoriaSimulation):
        self.sim      = sim
        self._time    = 0.0

        # Tile dimensions
        self._tile_w  = TILE_SIZE
        self._tile_h  = TILE_SIZE
        self._tile_size = TILE_SIZE

        # Tile surface cache
        self._tilemap    = TileMap(sim.grid_size)
        self._tile_surf  = None
        self._tile_dirty = True

        # Smooth visual positions: id(entity) → [px_x, px_y]
        self._smooth: dict[int, list] = {}

        # Camera
        self.cam_x = 0
        self.cam_y = 0

        # Layout — recalculated in draw() from surface size
        self.map_rect = pygame.Rect(0, 0, 980, 720)
        self.hud_rect = pygame.Rect(980, 0, 300, 720)

        # Reusable progress bars
        self._stam_bar = ProgressBar(pygame.Rect(0, 0, 40, 5))
        self._enrg_bar = ProgressBar(pygame.Rect(0, 0, 40, 5),
                                     color_high=C_BAR_ENERGY,
                                     color_mid=C_BAR_ENERGY,
                                     color_low=C_BAR_ENERGY)

        # HUD bottom — read by play state
        self._hud_bottom_y = 200

        # Vignette surface (rebuilt on size change)
        self._vignette: pygame.Surface | None = None
        self._vignette_size = (0, 0)

    # ------------------------------------------------------------------
    def _update_layout(self, surface: pygame.Surface):
        sw, sh = surface.get_size()
        map_w = sw - HUD_WIDTH
        self.map_rect = pygame.Rect(0, 0, map_w, sh)
        self.hud_rect = pygame.Rect(map_w, 0, HUD_WIDTH, sh)

    def _fit_tiles(self):
        gs = self.sim.grid_size
        tw = max(8, self.map_rect.width  // gs)
        th = max(8, (self.map_rect.height + gs - 1) // gs)
        if tw != self._tile_w or th != self._tile_h:
            self._tile_w    = tw
            self._tile_h    = th
            self._tile_size = min(tw, th)
            self._tile_dirty = True
            _glow_cache.clear()

    def _build_tile_surface(self):
        gs = self.sim.grid_size
        tw, th = self._tile_w, self._tile_h
        s = pygame.Surface((gs*tw, gs*th))
        det_colors = {
            TileMap.GRASS:  (45, 85, 36),
            TileMap.GRASS2: (38, 72, 30),
            TileMap.FOREST: (28, 60, 28),
            TileMap.DIRT:   (108, 80, 50),
            TileMap.PATH:   (128, 102, 66),
        }
        for x in range(gs):
            for y in range(gs):
                tt  = self._tilemap.get(x, y)
                col = TileMap.COLORS.get(tt, C_TILE_GRASS)
                pygame.draw.rect(s, col, (x*tw, y*th, tw, th))
                d = self._tilemap.detail(x, y)
                if d and tw >= 8:
                    dc = det_colors.get(tt, col)
                    dx = int(x*tw + d[0]*tw)
                    dy = int(y*th + d[1]*th)
                    pygame.draw.circle(s, dc, (dx, dy), d[2])
                # Subtle grid
                pygame.draw.line(s, C_GRID, (x*tw, y*th), ((x+1)*tw, y*th), 1)
                pygame.draw.line(s, C_GRID, (x*tw, y*th), (x*tw, (y+1)*th), 1)
        self._tile_surf  = s
        self._tile_dirty = False

    # ------------------------------------------------------------------
    # World → screen
    # ------------------------------------------------------------------
    def _w2s(self, gx, gy):
        return (gx * self._tile_w - self.cam_x + self.map_rect.left,
                gy * self._tile_h - self.cam_y + self.map_rect.top)

    # ------------------------------------------------------------------
    # Smooth position update
    # ------------------------------------------------------------------
    def _get_smooth(self, entity, dt: float):
        eid = id(entity)
        tw, th = self._tile_w, self._tile_h
        gs = self.sim.grid_size
        target_x = entity.position[0] * tw
        target_y = entity.position[1] * th
        if eid not in self._smooth:
            self._smooth[eid] = [float(target_x), float(target_y)]
            return target_x, target_y
        sp = self._smooth[eid]
        # Wrap-aware spring
        dx = target_x - sp[0]
        dy = target_y - sp[1]
        hw, hh = gs * tw / 2, gs * th / 2
        if abs(dx) > hw: dx -= math.copysign(gs * tw, dx)
        if abs(dy) > hh: dy -= math.copysign(gs * th, dy)
        speed = min(1.0, dt * 16)
        sp[0] += dx * speed
        sp[1] += dy * speed
        # Wrap within world
        sp[0] = sp[0] % (gs * tw)
        sp[1] = sp[1] % (gs * th)
        return sp[0], sp[1]

    # ------------------------------------------------------------------
    # MAIN DRAW — always receives current surface
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, dt: float, cam=(0, 0)):
        self._time += dt
        self.cam_x, self.cam_y = cam

        self._update_layout(surface)
        self._fit_tiles()
        if self._tile_dirty:
            self._build_tile_surface()

        # ── Map ──
        surface.fill(C_BG, self.map_rect)
        surface.set_clip(self.map_rect)
        if self._tile_surf:
            surface.blit(self._tile_surf, self.map_rect.topleft,
                         area=pygame.Rect(self.cam_x, self.cam_y,
                                         self.map_rect.width, self.map_rect.height))
        self._draw_entities(surface, dt)

        # Vignette overlay on map
        self._draw_vignette(surface)

        surface.set_clip(None)

        # ── HUD ──
        self._draw_hud(surface)
        self._draw_minimap(surface)

    # ------------------------------------------------------------------
    def _draw_entities(self, surface: pygame.Surface, dt: float):
        t     = self._time
        bob   = int(math.sin(t * BOB_SPEED) * BOB_AMOUNT)
        pulse = 0.5 + 0.5 * math.sin(t * PULSE_SPEED)

        treasures = [e for e in self.sim.entities if isinstance(e, Treasure)]
        buildings = [e for e in self.sim.entities if isinstance(e, (Hideout, Garrison))]
        hunters   = [e for e in self.sim.entities if isinstance(e, Hunter)]
        knights   = [e for e in self.sim.entities if isinstance(e, Knight)]

        for e in treasures: self._draw_treasure(surface, e, pulse, dt)
        for e in buildings: self._draw_building(surface, e, t, dt)
        for e in hunters:   self._draw_hunter  (surface, e, bob, dt)
        for e in knights:   self._draw_knight  (surface, e, bob, dt)

    # ------------------------------------------------------------------
    def _blit_glow(self, surface, cx, cy, radius, color, peak=110):
        g = make_glow(radius, color, rings=3, peak=peak)
        gx = int(cx - g.get_width()  // 2)
        gy = int(cy - g.get_height() // 2)
        surface.blit(g, (gx, gy))

    # ------------------------------------------------------------------
    def _draw_treasure(self, surface, e: Treasure, pulse: float, dt: float):
        ts = self._tile_size
        px, py = self._get_smooth(e, dt)
        sx, sy = (px - self.cam_x + self.map_rect.left,
                  py - self.cam_y + self.map_rect.top)
        cx, cy = int(sx + self._tile_w//2), int(sy + self._tile_h//2)
        mr = self.map_rect
        if not mr.collidepoint(cx, cy):
            return

        c = {EntityType.TREASURE_BRONZE: C_TREASURE_BRONZE,
             EntityType.TREASURE_SILVER: C_TREASURE_SILVER,
             EntityType.TREASURE_GOLD:   C_TREASURE_GOLD}.get(e.entity_type, C_TREASURE_GOLD)

        # Pulsing glow
        glow_r = int(ts * 0.5 + ts * 0.2 * pulse)
        self._blit_glow(surface, cx, cy, max(4, glow_r), c, peak=90)

        r = max(5, int(ts * 0.32))
        # Shadow
        pygame.draw.ellipse(surface, (0,0,0), (cx-r, cy+r-1, r*2, 4))
        # Body
        pygame.draw.circle(surface, c, (cx, cy), r)
        # Highlight shimmer
        hi = tuple(min(255, int(v*1.6)) for v in c)
        pygame.draw.circle(surface, hi, (cx - r//3, cy - r//3), max(2, r//3))
        # White ring
        pygame.draw.circle(surface, C_WHITE, (cx, cy), r, 1)

    # ------------------------------------------------------------------
    def _draw_building(self, surface, e, t: float, dt: float):
        tw, th = self._tile_w, self._tile_h
        ts = self._tile_size
        px, py = self._get_smooth(e, dt)
        sx, sy = (px - self.cam_x + self.map_rect.left,
                  py - self.cam_y + self.map_rect.top)
        cx, cy = int(sx + tw//2), int(sy + th//2)
        mr = self.map_rect
        if not mr.collidepoint(cx, cy):
            return
        is_gar = isinstance(e, Garrison)
        # Warm torch glow
        torch_c = (220, 100, 50) if is_gar else (220, 150, 50)
        glow_alpha = int(60 + 30 * math.sin(t * 4.0 + id(e)))
        g = make_glow(ts//2, torch_c, rings=2, peak=glow_alpha)
        surface.blit(g, (cx - g.get_width()//2, cy - g.get_height()//2))
        _draw_castle(surface, cx, cy, ts, is_gar)

    # ------------------------------------------------------------------
    def _draw_hunter(self, surface, e: Hunter, bob: int, dt: float):
        tw, th = self._tile_w, self._tile_h
        ts = self._tile_size
        px, py = self._get_smooth(e, dt)
        sx, sy = (px - self.cam_x + self.map_rect.left,
                  py - self.cam_y + self.map_rect.top)
        cx = int(sx + tw//2)
        cy = int(sy + th//2) + bob
        mr = self.map_rect
        if not mr.collidepoint(cx, cy):
            return

        c = (C_HUNTER_HERO if e.is_hero else
             {HunterSkill.NAVIGATION: C_HUNTER_NAV,
              HunterSkill.ENDURANCE:  C_HUNTER_END,
              HunterSkill.STEALTH:    C_HUNTER_STH}.get(e.skill, C_HUNTER_NAV))

        r = max(6, int(ts * 0.38))

        if e.state == HunterState.COLLAPSED:
            pygame.draw.line(surface, C_RED, (cx-r,cy-r), (cx+r,cy+r), 3)
            pygame.draw.line(surface, C_RED, (cx+r,cy-r), (cx-r,cy+r), 3)
            return

        # Glow
        glow_pk = 130 if not e.is_hero else 160
        self._blit_glow(surface, cx, cy, r, c, peak=glow_pk)

        # Shadow
        pygame.draw.ellipse(surface, (0,0,0), (cx-r, cy+r-1, r*2, 5))

        # Body
        pygame.draw.circle(surface, c, (cx, cy), r)
        outline = tuple(min(255, int(v*1.5)) for v in c)
        pygame.draw.circle(surface, outline, (cx, cy), r, 2)

        # Inner highlight (top-left)
        hi = tuple(min(255, int(v*1.8)) for v in c)
        pygame.draw.circle(surface, hi, (cx - r//3, cy - r//3), max(2, r//3))

        # Skill dot (bottom-right)
        dot = {HunterSkill.NAVIGATION: (140, 220, 255),
               HunterSkill.ENDURANCE:  (140, 255, 170),
               HunterSkill.STEALTH:    (240, 180, 255)}.get(e.skill, C_WHITE)
        pygame.draw.circle(surface, dot, (cx + r//2, cy + r//2), max(2, r//4))

        if e.is_hero:
            # Gold crown ring
            pygame.draw.circle(surface, C_TREASURE_GOLD, (cx, cy), r+4, 2)

        # Evading flicker
        if e.state == HunterState.EVADING:
            t_evade = int(self._time * 8) % 2
            if t_evade:
                pygame.draw.circle(surface, C_RED, (cx, cy), r+5, 1)

        # Carried-treasure gem
        if e.carried_treasure:
            tc = {EntityType.TREASURE_BRONZE: C_TREASURE_BRONZE,
                  EntityType.TREASURE_SILVER: C_TREASURE_SILVER,
                  EntityType.TREASURE_GOLD:   C_TREASURE_GOLD}.get(
                e.carried_treasure.entity_type, C_TREASURE_GOLD)
            pygame.draw.circle(surface, tc,    (cx, cy - r - 5), 5)
            pygame.draw.circle(surface, C_WHITE, (cx, cy - r - 5), 5, 1)

        # Stamina bar
        bw = max(4, tw - 4)
        bx = int(sx) + 2
        by = int(sy) + th - 6
        self._stam_bar.rect = pygame.Rect(bx, by, bw, 4)
        self._stam_bar.value = e.stamina
        self._stam_bar.max_value = e.max_stamina
        self._stam_bar.draw(surface)

    # ------------------------------------------------------------------
    def _draw_knight(self, surface, e: Knight, bob: int, dt: float):
        tw, th = self._tile_w, self._tile_h
        ts = self._tile_size
        px, py = self._get_smooth(e, dt)
        sx, sy = (px - self.cam_x + self.map_rect.left,
                  py - self.cam_y + self.map_rect.top)
        cx = int(sx + tw//2)
        cy = int(sy + th//2) + bob
        mr = self.map_rect
        if not mr.collidepoint(cx, cy):
            return

        pursuing = e.state == KnightState.PURSUING
        c = C_KNIGHT_PURSUE if pursuing else C_KNIGHT
        r = max(6, int(ts * 0.38))

        # Intense glow when pursuing
        glow_pk = 160 if pursuing else 100
        self._blit_glow(surface, cx, cy, r, c, peak=glow_pk)

        # Shadow
        pygame.draw.ellipse(surface, (0,0,0), (cx-r, cy+r-1, r*2, 5))

        # Diamond shape
        pts = [(cx, cy-r), (cx+r, cy), (cx, cy+r), (cx-r, cy)]
        pygame.draw.polygon(surface, c, pts)
        # Inner cross
        half = r // 2
        pygame.draw.line(surface, C_KNIGHT_DARK, (cx, cy-half), (cx, cy+half), 2)
        pygame.draw.line(surface, C_KNIGHT_DARK, (cx-half, cy), (cx+half, cy), 2)
        pygame.draw.polygon(surface, C_KNIGHT_DARK, pts, 2)

        # Pulse ring when pursuing
        if pursuing:
            pr = int(r + 4 + 3 * math.sin(self._time * 8))
            pygame.draw.polygon(surface,
                                C_KNIGHT_PURSUE,
                                [(cx, cy-pr),(cx+pr, cy),(cx, cy+pr),(cx-pr, cy)], 1)

        # State indicator
        if e.state in (KnightState.PURSUING, KnightState.CHALLENGING):
            lbl = "!" if e.state == KnightState.PURSUING else "✕"
            fs = max(10, ts//2)
            font = get_font(fs, bold=True)
            ts_r = font.render(lbl, True, C_YELLOW if pursuing else C_RED)
            surface.blit(ts_r, (cx - ts_r.get_width()//2, cy - r - ts_r.get_height() - 2))

        # Energy bar
        bw = max(4, tw - 4)
        bx = int(sx) + 2
        by = int(sy) + th - 6
        self._enrg_bar.rect = pygame.Rect(bx, by, bw, 4)
        self._enrg_bar.value = e.energy
        self._enrg_bar.max_value = e.max_energy
        self._enrg_bar.draw(surface)

    # ------------------------------------------------------------------
    # Vignette — dark corners for atmosphere
    # ------------------------------------------------------------------
    def _draw_vignette(self, surface: pygame.Surface):
        mr = self.map_rect
        sz = (mr.width, mr.height)
        if sz != self._vignette_size or self._vignette is None:
            self._vignette_size = sz
            v = pygame.Surface(sz, pygame.SRCALPHA)
            cx, cy = sz[0]//2, sz[1]//2
            max_r  = int(math.sqrt(cx*cx + cy*cy))
            for r in range(0, min(180, max_r, min(sz)//2), 6):
                a = int(80 * (1.0 - r / max(1, max_r)))
                pygame.draw.rect(v, (0, 0, 0, a),
                                 (r, r, sz[0]-2*r, sz[1]-2*r), 6)
            self._vignette = v
        if self._vignette:
            surface.blit(self._vignette, mr.topleft)

    # ------------------------------------------------------------------
    # HUD
    # ------------------------------------------------------------------
    def _draw_hud(self, surface: pygame.Surface):
        hr    = self.hud_rect
        stats = self.sim.statistics()

        # Panel
        pygame.draw.rect(surface, C_UI_PANEL, hr)
        # Subtle inner gradient strip
        inner = pygame.Rect(hr.left+2, hr.top, hr.width-2, hr.height)
        pygame.draw.rect(surface, (22, 18, 38), inner)
        pygame.draw.line(surface, C_UI_BORDER, hr.topleft, hr.bottomleft, 2)

        x  = hr.left + 14
        y  = 14
        w  = hr.width - 28

        # Title
        draw_text(surface, "KNIGHTS OF ELDORIA",
                  hr.centerx, y, size=14, color=C_UI_TEXT_BRIGHT,
                  bold=True, align="center", shadow=True)
        y += 22
        # Gold gem divider
        pygame.draw.line(surface, C_UI_BORDER, (hr.left+10, y), (hr.right-10, y), 1)
        pygame.draw.circle(surface, C_TREASURE_GOLD, (hr.centerx, y), 4)
        y += 10

        # Step
        draw_text(surface, f"Step  {stats['step']:>5}", x, y, size=14, color=C_UI_TEXT)
        y += 20
        pygame.draw.line(surface, C_UI_PANEL_2, (hr.left+8, y), (hr.right-8, y), 1)
        y += 6

        # Treasure progress
        draw_text(surface, "TREASURE COLLECTED", x, y, size=11, color=C_UI_TEXT_DIM, bold=True)
        y += 14
        pct = stats["pct"] / 100.0
        bar = pygame.Rect(x, y, w, 16)
        pygame.draw.rect(surface, C_BAR_BG, bar, border_radius=5)
        pygame.draw.rect(surface, C_BAR_BORDER, bar, width=1, border_radius=5)
        if pct > 0:
            fw = max(6, int(w * pct))
            fc = C_GREEN if pct > 0.7 else C_YELLOW if pct > 0.35 else C_RED
            fr = pygame.Rect(x, y, fw, 16)
            pygame.draw.rect(surface, fc, fr, border_radius=5)
            # Shine
            pygame.draw.rect(surface,
                             tuple(min(255, int(v*1.5)) for v in fc),
                             pygame.Rect(x+2, y+2, max(1, fw-4), 3),
                             border_radius=2)
        draw_text(surface, f"{stats['pct']:.1f}%",
                  hr.right-10, y-1, size=13, color=C_UI_TEXT_DIM, align="right")
        y += 22
        pygame.draw.line(surface, C_UI_BORDER, (hr.left+8, y), (hr.right-8, y), 1)
        y += 8

        # Entities
        draw_text(surface, "ENTITIES", x, y, size=11, color=C_UI_TEXT_DIM, bold=True)
        y += 14
        for label, val, col in [
            ("Hunters",  stats["hunters"],  C_HUNTER_NAV),
            ("Knights",  stats["knights"],  C_KNIGHT),
            ("Hideouts", stats["hideouts"], C_HIDEOUT),
        ]:
            draw_text(surface, label, x+4, y, size=13, color=C_UI_TEXT_DIM)
            # Coloured dot
            pygame.draw.circle(surface, col, (hr.right-24, y+7), 5)
            draw_text(surface, str(val), hr.right-14, y,
                      size=13, color=col, align="right", bold=True)
            y += 17
        pygame.draw.line(surface, C_UI_PANEL_2, (hr.left+8, y), (hr.right-8, y), 1)
        y += 6

        # Treasure breakdown
        draw_text(surface, "TREASURES ON MAP", x, y, size=11, color=C_UI_TEXT_DIM, bold=True)
        y += 14
        for label, val, col in [
            ("  Bronze", stats["bronze"], C_TREASURE_BRONZE),
            ("  Silver", stats["silver"], C_TREASURE_SILVER),
            ("  Gold",   stats["gold"],   C_TREASURE_GOLD),
        ]:
            draw_text(surface, label, x+4, y, size=13, color=C_UI_TEXT_DIM)
            draw_text(surface, str(val), hr.right-14, y,
                      size=13, color=col, align="right", bold=True)
            y += 16
        pygame.draw.line(surface, C_UI_BORDER, (hr.left+8, y), (hr.right-8, y), 1)
        y += 8

        # Score (big, animated glow)
        draw_text(surface, "SCORE", hr.centerx, y, size=11,
                  color=C_UI_TEXT_DIM, bold=True, align="center")
        y += 14
        draw_text(surface, f"{stats['score']:,}", hr.centerx, y,
                  size=26, color=C_UI_TEXT_BRIGHT, bold=True,
                  align="center", shadow=True)
        y += 32

        self._hud_bottom_y = y

    # ------------------------------------------------------------------
    # Minimap
    # ------------------------------------------------------------------
    def _draw_minimap(self, surface: pygame.Surface):
        hr = self.hud_rect
        ms = MINIMAP_SIZE
        mp = MINIMAP_PAD
        mx = hr.left + (hr.width - ms) // 2
        my = hr.bottom - ms - mp
        mr = pygame.Rect(mx, my, ms, ms)

        pygame.draw.rect(surface, (10, 8, 20), mr)
        pygame.draw.rect(surface, C_UI_BORDER, mr, width=1)

        gs    = self.sim.grid_size
        scale = ms / gs

        for x in range(gs):
            for y in range(gs):
                tc = TileMap.COLORS.get(self._tilemap.get(x, y), C_TILE_GRASS)
                px = int(mx + x * scale)
                py = int(my + y * scale)
                pw = max(1, int(scale))
                pygame.draw.rect(surface, tc, (px, py, pw, pw))

        # Camera viewport box
        if self._tile_w > 0:
            vx = int(mx + self.cam_x / self._tile_w * scale)
            vy = int(my + self.cam_y / self._tile_h * scale)
            vw = int(self.map_rect.width  / self._tile_w * scale)
            vh = int(self.map_rect.height / self._tile_h * scale)
            vr = pygame.Rect(vx, vy, vw, vh).clip(mr)
            if vr.width > 0:
                pygame.draw.rect(surface, C_UI_BORDER_HI, vr, width=1)

        for e in self.sim.entities:
            ex, ey = e.position
            px = int(mx + ex * scale)
            py = int(my + ey * scale)
            r  = max(1, int(scale * 0.9))
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
            pygame.draw.circle(surface, c, (px, py), r)

        draw_text(surface, "MAP", mx + ms//2, my - 16,
                  size=11, color=C_UI_TEXT_DIM, bold=True, align="center")


# ---------------------------------------------------------------------------
# Fade transition
# ---------------------------------------------------------------------------
class FadeTransition:
    def __init__(self, duration=0.4):
        self.duration = duration
        self._t    = 0.0
        self._mode = "none"
        self._done = False

    @property
    def done(self): return self._done

    def fade_in(self):  self._t = 0.0; self._mode = "in";  self._done = False
    def fade_out(self): self._t = 0.0; self._mode = "out"; self._done = False

    def update(self, dt):
        if self._mode == "none":
            return
        self._t += dt / self.duration
        if self._t >= 1.0:
            self._t = 1.0; self._done = True; self._mode = "none"

    def draw(self, surface):
        if self._mode == "none" and not self._done:
            return
        alpha = int(255 * (1.0-self._t) if self._mode == "in" else 255*self._t)
        if alpha <= 0:
            return
        s = pygame.Surface(surface.get_size())
        s.fill(C_BLACK)
        s.set_alpha(alpha)
        surface.blit(s, (0, 0))
