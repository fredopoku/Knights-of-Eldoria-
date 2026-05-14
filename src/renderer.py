"""
GameRenderer — dark-fantasy "glowing world" style.
Features: weather system (rain/storm), day/night cycle, boss knight visuals.
draw() always takes the current surface as its first argument so the
renderer NEVER holds a stale surface reference.
"""
from __future__ import annotations
import math
import random
import pygame
from src.constants import (
    TILE_SIZE, GRID_SIZE, HUD_WIDTH, MINIMAP_SIZE, MINIMAP_PAD,
    C_BG, C_TILE_GRASS, C_TILE_GRASS_2, C_TILE_FOREST,
    C_TILE_DIRT, C_TILE_PATH, C_GRID,
    C_HUNTER_NAV, C_HUNTER_END, C_HUNTER_STH, C_HUNTER_HERO,
    C_KNIGHT, C_KNIGHT_DARK, C_KNIGHT_PURSUE,
    C_BOSS_KNIGHT, C_BOSS_KNIGHT_DARK,
    C_TREASURE_BRONZE, C_TREASURE_SILVER, C_TREASURE_GOLD,
    C_HIDEOUT, C_HIDEOUT_DARK, C_GARRISON, C_GARRISON_DARK,
    C_UI_PANEL, C_UI_PANEL_2, C_UI_BORDER, C_UI_BORDER_HI,
    C_UI_TEXT, C_UI_TEXT_DIM, C_UI_TEXT_BRIGHT, C_UI_ACCENT,
    C_BAR_BG, C_BAR_BORDER,
    C_BAR_STAMINA_HI, C_BAR_STAMINA_MID, C_BAR_STAMINA_LOW, C_BAR_ENERGY,
    C_GREEN, C_RED, C_YELLOW, C_WHITE, C_BLACK,
    C_WEATHER_RAIN, C_DAY_TINT, C_NIGHT_TINT, C_COMBO,
    BOB_SPEED, BOB_AMOUNT, PULSE_SPEED,
    WEATHER_NONE, WEATHER_RAIN, WEATHER_STORM,
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
                if rng.random() < 0.40:
                    self._detail[(x, y)] = (
                        rng.uniform(0.18, 0.82),
                        rng.uniform(0.18, 0.82),
                        rng.randint(1, 3),
                    )
        # Organic road paths
        for _ in range(grid_size // 3):
            px, py = rng.randint(1, grid_size - 2), rng.randint(1, grid_size - 2)
            for _ in range(rng.randint(4, 10)):
                self._tiles[(px, py)] = self.PATH
                step = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
                px = max(0, min(grid_size - 1, px + step[0]))
                py = max(0, min(grid_size - 1, py + step[1]))

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
    body = pygame.Rect(cx - hw + 2, cy - hw + 4, hw * 2 - 4, hw * 2 - 5)
    pygame.draw.rect(surf, c,  body, border_radius=3)
    pygame.draw.rect(surf, cd, body, width=2, border_radius=3)
    # Battlements (top teeth)
    bw = max(3, sz // 7)
    for i in range(3):
        bx = cx - hw + 3 + i * (bw + 2)
        pygame.draw.rect(surf, c, (bx, cy - hw, bw, 5))
    # Door arch
    dw, dh = max(4, sz // 5), max(6, sz // 4)
    pygame.draw.rect(surf, cd, (cx - dw // 2, cy + hw - dh - 2, dw, dh), border_radius=2)
    # Windows
    ew = max(2, sz // 8)
    pygame.draw.rect(surf, cd, (cx - hw // 2, cy - 2, ew, max(4, sz // 5)))
    pygame.draw.rect(surf, cd, (cx + hw // 4, cy - 2, ew, max(4, sz // 5)))
    # Warm window glow
    wg_col = (200, 140, 50) if not is_garrison else (200, 80, 60)
    pygame.draw.rect(surf, wg_col,
                     (cx - hw // 2 + 1, cy - 1, max(1, ew - 2), max(2, sz // 6)))
    pygame.draw.rect(surf, wg_col,
                     (cx + hw // 4 + 1, cy - 1, max(1, ew - 2), max(2, sz // 6)))


# ---------------------------------------------------------------------------
# GameRenderer
# ---------------------------------------------------------------------------
class GameRenderer:
    def __init__(self, sim: EldoriaSimulation):
        self.sim       = sim
        self._time     = 0.0

        # Tile dimensions
        self._tile_w   = TILE_SIZE
        self._tile_h   = TILE_SIZE
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
        self._vignette:      pygame.Surface | None = None
        self._vignette_size: tuple                 = (0, 0)

        # ---- Weather system ----
        self._weather       = WEATHER_NONE
        self._weather_timer = 0.0
        self._lightning_flash = 0.0
        self._rain_particles: list[list] = []   # each: [x, y, speed]
        self._init_rain()

        # ---- Day/night cycle ----
        # 0.0 = midnight, 0.5 = noon, wraps at 1.0
        self._day_cycle = 0.5   # start at noon

        # ---- Combo display (set by play state) ----
        self.combo_count  = 0
        self.combo_timer  = 0.0

    # ------------------------------------------------------------------
    def _init_rain(self):
        """Pre-populate rain particles across the full map area."""
        self._rain_particles = [
            [random.uniform(0, 1280), random.uniform(0, 720),
             random.uniform(200, 350)]
            for _ in range(120)
        ]

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
            self._tile_w     = tw
            self._tile_h     = th
            self._tile_size  = min(tw, th)
            self._tile_dirty = True
            _glow_cache.clear()

    def _build_tile_surface(self):
        gs = self.sim.grid_size
        tw, th = self._tile_w, self._tile_h
        s = pygame.Surface((gs * tw, gs * th))
        det_colors = {
            TileMap.GRASS:  (42, 90, 32),
            TileMap.GRASS2: (34, 76, 26),
            TileMap.FOREST: (22, 64, 22),
            TileMap.DIRT:   (112, 84, 52),
            TileMap.PATH:   (132, 106, 68),
        }
        for x in range(gs):
            for y in range(gs):
                tt  = self._tilemap.get(x, y)
                col = TileMap.COLORS.get(tt, C_TILE_GRASS)
                pygame.draw.rect(s, col, (x * tw, y * th, tw, th))
                d = self._tilemap.detail(x, y)
                if d and tw >= 8:
                    dc = det_colors.get(tt, col)
                    dx = int(x * tw + d[0] * tw)
                    dy = int(y * th + d[1] * th)
                    pygame.draw.circle(s, dc, (dx, dy), d[2])
                # Subtle grid lines
                pygame.draw.line(s, C_GRID, (x * tw, y * th), ((x + 1) * tw, y * th), 1)
                pygame.draw.line(s, C_GRID, (x * tw, y * th), (x * tw, (y + 1) * th), 1)
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
        dx = target_x - sp[0]
        dy = target_y - sp[1]
        hw, hh = gs * tw / 2, gs * th / 2
        if abs(dx) > hw: dx -= math.copysign(gs * tw, dx)
        if abs(dy) > hh: dy -= math.copysign(gs * th, dy)
        speed = min(1.0, dt * 16)
        sp[0] += dx * speed
        sp[1] += dy * speed
        sp[0]  = sp[0] % (gs * tw)
        sp[1]  = sp[1] % (gs * th)
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

        # ── Weather + day/night update ──
        self._update_weather(dt)
        self._day_cycle = (self._day_cycle + dt / 120.0) % 1.0

        # ── Map ──
        surface.fill(C_BG, self.map_rect)
        if self._tile_surf:
            surface.blit(self._tile_surf, self.map_rect.topleft,
                         area=pygame.Rect(self.cam_x, self.cam_y,
                                         self.map_rect.width,
                                         self.map_rect.height))

        self._draw_entities(surface, dt)

        # Day/night tint overlay
        self._draw_day_night(surface)

        # Rain / storm overlay
        if self._weather in (WEATHER_RAIN, WEATHER_STORM):
            self._draw_rain(surface, dt)

        # Lightning flash
        if self._lightning_flash > 0:
            self._draw_lightning(surface, dt)

        # Vignette overlay
        self._draw_vignette(surface)

        # ── HUD ──
        self._draw_hud(surface)
        self._draw_minimap(surface)

    # ------------------------------------------------------------------
    def _update_weather(self, dt: float):
        self._weather_timer += dt
        # Change weather every 40 seconds
        if self._weather_timer > 40.0:
            self._weather_timer = 0.0
            self._weather = random.choice([
                WEATHER_NONE, WEATHER_NONE, WEATHER_RAIN, WEATHER_STORM
            ])
        # Lightning flicker
        if self._weather == WEATHER_STORM:
            if random.random() < dt * 0.5:   # ~0.5 flashes/second
                self._lightning_flash = 0.25
        if self._lightning_flash > 0:
            self._lightning_flash = max(0.0, self._lightning_flash - dt * 3.0)

    def _draw_day_night(self, surface: pygame.Surface):
        """Overlay a semi-transparent tint based on day/night cycle."""
        mr = self.map_rect
        # _day_cycle: 0=midnight, 0.5=noon, 1=midnight
        # Use a cosine curve: cos(2π * cycle) gives 1 at midnight, -1 at noon
        night_t = 0.5 + 0.5 * math.cos(self._day_cycle * math.tau)
        # Clamp to [0..1]
        night_t = max(0.0, min(1.0, night_t))
        alpha = int(night_t * 90)   # max 90/255 at midnight
        if alpha < 4:
            return
        tint = pygame.Surface((mr.width, mr.height), pygame.SRCALPHA)
        if night_t > 0.5:
            # Night: blue tint
            tint.fill((*C_NIGHT_TINT, alpha))
        else:
            # Day: warm tint (very subtle)
            warm_a = int((0.5 - night_t) * 2 * 25)
            if warm_a < 4:
                return
            tint.fill((*C_DAY_TINT, warm_a))
        surface.blit(tint, mr.topleft)

    def _draw_rain(self, surface: pygame.Surface, dt: float):
        mr = self.map_rect
        for p in self._rain_particles:
            p[1] += p[2] * dt
            p[0] -= p[2] * dt * 0.3   # diagonal slant
            if p[1] > mr.height + 20:
                p[1] = random.uniform(-20, 0)
                p[0] = random.uniform(0, mr.width + 50)
            x1 = int(p[0]) + mr.left
            y1 = int(p[1]) + mr.top
            x2 = int(p[0] - 5) + mr.left
            y2 = int(p[1] + 12) + mr.top
            # Bounds check (no set_clip)
            if (mr.left <= x1 <= mr.right and mr.top <= y1 <= mr.bottom and
                    mr.left <= x2 <= mr.right and mr.top <= y2 <= mr.bottom):
                alpha_val = 140 if self._weather == WEATHER_STORM else 90
                col = (*C_WEATHER_RAIN, alpha_val)
                rain_line = pygame.Surface((12, 18), pygame.SRCALPHA)
                pygame.draw.line(rain_line, col, (5, 0), (0, 18), 1)
                surface.blit(rain_line, (x2, y2 - 18))

    def _draw_lightning(self, surface: pygame.Surface, dt: float):
        mr = self.map_rect
        alpha = int(self._lightning_flash * 200)
        if alpha > 0:
            flash = pygame.Surface((mr.width, mr.height), pygame.SRCALPHA)
            flash.fill((255, 255, 255, alpha))
            surface.blit(flash, mr.topleft)

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
        g  = make_glow(radius, color, rings=3, peak=peak)
        gx = int(cx - g.get_width()  // 2)
        gy = int(cy - g.get_height() // 2)
        surface.blit(g, (gx, gy))

    # ------------------------------------------------------------------
    def _draw_treasure(self, surface, e: Treasure, pulse: float, dt: float):
        ts = self._tile_size
        px, py = self._get_smooth(e, dt)
        sx = px - self.cam_x + self.map_rect.left
        sy = py - self.cam_y + self.map_rect.top
        cx, cy = int(sx + self._tile_w // 2), int(sy + self._tile_h // 2)
        mr = self.map_rect
        if not mr.collidepoint(cx, cy):
            return

        c = {EntityType.TREASURE_BRONZE: C_TREASURE_BRONZE,
             EntityType.TREASURE_SILVER: C_TREASURE_SILVER,
             EntityType.TREASURE_GOLD:   C_TREASURE_GOLD}.get(e.entity_type, C_TREASURE_GOLD)

        # Pulsing glow
        glow_r = int(ts * 0.55 + ts * 0.22 * pulse)
        self._blit_glow(surface, cx, cy, max(5, glow_r), c, peak=100)

        r = max(5, int(ts * 0.34))
        # Shadow
        pygame.draw.ellipse(surface, (0, 0, 0), (cx - r, cy + r - 1, r * 2, 4))
        # Body
        pygame.draw.circle(surface, c, (cx, cy), r)
        # Highlight shimmer
        hi = tuple(min(255, int(v * 1.7)) for v in c)
        pygame.draw.circle(surface, hi, (cx - r // 3, cy - r // 3), max(2, r // 3))
        # White ring
        pygame.draw.circle(surface, C_WHITE, (cx, cy), r, 1)

    # ------------------------------------------------------------------
    def _draw_building(self, surface, e, t: float, dt: float):
        tw, th = self._tile_w, self._tile_h
        ts = self._tile_size
        px, py = self._get_smooth(e, dt)
        sx = px - self.cam_x + self.map_rect.left
        sy = py - self.cam_y + self.map_rect.top
        cx, cy = int(sx + tw // 2), int(sy + th // 2)
        mr = self.map_rect
        if not mr.collidepoint(cx, cy):
            return
        is_gar = isinstance(e, Garrison)
        torch_c    = (220, 100, 50) if is_gar else (220, 155, 50)
        glow_alpha = int(65 + 32 * math.sin(t * 4.0 + id(e)))
        g = make_glow(ts // 2, torch_c, rings=2, peak=glow_alpha)
        surface.blit(g, (cx - g.get_width() // 2, cy - g.get_height() // 2))
        _draw_castle(surface, cx, cy, ts, is_gar)

    # ------------------------------------------------------------------
    def _draw_hunter(self, surface, e: Hunter, bob: int, dt: float):
        tw, th = self._tile_w, self._tile_h
        ts = self._tile_size
        px, py = self._get_smooth(e, dt)
        sx = px - self.cam_x + self.map_rect.left
        sy = py - self.cam_y + self.map_rect.top
        cx = int(sx + tw // 2)
        cy = int(sy + th // 2) + bob
        mr = self.map_rect
        if not mr.collidepoint(cx, cy):
            return

        c = (C_HUNTER_HERO if e.is_hero else
             {HunterSkill.NAVIGATION: C_HUNTER_NAV,
              HunterSkill.ENDURANCE:  C_HUNTER_END,
              HunterSkill.STEALTH:    C_HUNTER_STH}.get(e.skill, C_HUNTER_NAV))

        r = max(7, int(ts * 0.40))

        if e.state == HunterState.COLLAPSED:
            pygame.draw.line(surface, C_RED, (cx - r, cy - r), (cx + r, cy + r), 3)
            pygame.draw.line(surface, C_RED, (cx + r, cy - r), (cx - r, cy + r), 3)
            return

        # Glow
        glow_pk = 140 if not e.is_hero else 180
        self._blit_glow(surface, cx, cy, r, c, peak=glow_pk)

        # Shadow
        pygame.draw.ellipse(surface, (0, 0, 0), (cx - r, cy + r - 1, r * 2, 5))

        # Body
        pygame.draw.circle(surface, c, (cx, cy), r)
        outline = tuple(min(255, int(v * 1.55)) for v in c)
        pygame.draw.circle(surface, outline, (cx, cy), r, 2)

        # Inner highlight
        hi = tuple(min(255, int(v * 1.9)) for v in c)
        pygame.draw.circle(surface, hi, (cx - r // 3, cy - r // 3), max(2, r // 3))

        # Skill dot (bottom-right)
        dot = {HunterSkill.NAVIGATION: (140, 225, 255),
               HunterSkill.ENDURANCE:  (140, 255, 175),
               HunterSkill.STEALTH:    (245, 185, 255)}.get(e.skill, C_WHITE)
        pygame.draw.circle(surface, dot, (cx + r // 2, cy + r // 2), max(2, r // 4))

        if e.is_hero:
            # Gold crown ring
            pygame.draw.circle(surface, C_TREASURE_GOLD, (cx, cy), r + 5, 2)
            # Crown points
            for angle in range(0, 360, 90):
                rad = math.radians(angle)
                px2 = int(cx + (r + 8) * math.cos(rad))
                py2 = int(cy + (r + 8) * math.sin(rad))
                pygame.draw.circle(surface, C_TREASURE_GOLD, (px2, py2), 2)

        # Evading flicker ring
        if e.state == HunterState.EVADING:
            t_ev = int(self._time * 8) % 2
            if t_ev:
                pygame.draw.circle(surface, C_RED, (cx, cy), r + 5, 1)

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
        self._stam_bar.value     = e.stamina
        self._stam_bar.max_value = e.max_stamina
        self._stam_bar.draw(surface)

    # ------------------------------------------------------------------
    def _draw_knight(self, surface, e: Knight, bob: int, dt: float):
        tw, th = self._tile_w, self._tile_h
        ts = self._tile_size

        # Check for boss attribute
        is_boss = getattr(e, 'is_boss', False)

        px, py = self._get_smooth(e, dt)
        sx = px - self.cam_x + self.map_rect.left
        sy = py - self.cam_y + self.map_rect.top
        cx = int(sx + tw // 2)
        cy = int(sy + th // 2) + bob
        mr = self.map_rect
        if not mr.collidepoint(cx, cy):
            return

        pursuing = e.state == KnightState.PURSUING
        if is_boss:
            c = C_BOSS_KNIGHT
        else:
            c = C_KNIGHT_PURSUE if pursuing else C_KNIGHT

        # Boss knight is larger
        r = max(7, int(ts * (0.50 if is_boss else 0.38)))

        # Glow — more intense for boss
        glow_pk = 200 if is_boss else (165 if pursuing else 105)
        self._blit_glow(surface, cx, cy, r, c, peak=glow_pk)

        # Shadow
        pygame.draw.ellipse(surface, (0, 0, 0), (cx - r, cy + r - 1, r * 2, 5))

        # Diamond body
        pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
        pygame.draw.polygon(surface, c, pts)
        cd = C_BOSS_KNIGHT_DARK if is_boss else C_KNIGHT_DARK
        half = r // 2
        pygame.draw.line(surface, cd, (cx, cy - half), (cx, cy + half), 2)
        pygame.draw.line(surface, cd, (cx - half, cy), (cx + half, cy), 2)
        pygame.draw.polygon(surface, cd, pts, 2)

        # Boss crown decoration — spikes above diamond
        if is_boss:
            spike_col = (255, 200, 50)
            for off in (-r // 2, 0, r // 2):
                sx2 = cx + off
                pygame.draw.polygon(surface, spike_col,
                                   [(sx2, cy - r - 8), (sx2 - 4, cy - r + 2),
                                    (sx2 + 4, cy - r + 2)])

        # Pulse ring when pursuing or boss
        if pursuing or is_boss:
            pr = int(r + 4 + 3 * math.sin(self._time * 8))
            pygame.draw.polygon(surface,
                                C_KNIGHT_PURSUE if pursuing else C_BOSS_KNIGHT,
                                [(cx, cy - pr), (cx + pr, cy),
                                 (cx, cy + pr), (cx - pr, cy)], 1)

        # State indicator label
        if e.state in (KnightState.PURSUING, KnightState.CHALLENGING):
            lbl = "!" if e.state == KnightState.PURSUING else "X"
            if is_boss:
                lbl = "!!" if e.state == KnightState.PURSUING else "X"
            fs  = max(10, ts // 2)
            font = get_font(fs, bold=True)
            ts_r = font.render(lbl, True, C_YELLOW if pursuing else C_RED)
            surface.blit(ts_r,
                         (cx - ts_r.get_width() // 2, cy - r - ts_r.get_height() - 2))

        # Energy bar
        bw = max(4, tw - 4)
        bx = int(sx) + 2
        by = int(sy) + th - 6
        self._enrg_bar.rect      = pygame.Rect(bx, by, bw, 4)
        self._enrg_bar.value     = e.energy
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
            cx, cy = sz[0] // 2, sz[1] // 2
            max_r  = int(math.sqrt(cx * cx + cy * cy))
            for r in range(0, min(180, max_r, min(sz) // 2), 6):
                a = int(85 * (1.0 - r / max(1, max_r)))
                pygame.draw.rect(v, (0, 0, 0, a),
                                 (r, r, sz[0] - 2 * r, sz[1] - 2 * r), 6)
            self._vignette = v
        if self._vignette:
            surface.blit(self._vignette, mr.topleft)

    # ------------------------------------------------------------------
    # HUD — right panel
    # ------------------------------------------------------------------
    def _draw_hud(self, surface: pygame.Surface):
        hr    = self.hud_rect
        stats = self.sim.statistics()

        # Panel background
        pygame.draw.rect(surface, C_UI_PANEL, hr)
        inner = pygame.Rect(hr.left + 2, hr.top, hr.width - 2, hr.height)
        pygame.draw.rect(surface, (20, 16, 40), inner)
        pygame.draw.line(surface, C_UI_BORDER, hr.topleft, hr.bottomleft, 2)

        x = hr.left + 14
        y = 14
        w = hr.width - 28

        # Title
        draw_text(surface, "KNIGHTS OF ELDORIA",
                  hr.centerx, y, size=14, color=C_UI_TEXT_BRIGHT,
                  bold=True, align="center", shadow=True)
        y += 22
        # Decorative divider
        pygame.draw.line(surface, C_UI_BORDER, (hr.left + 10, y), (hr.right - 10, y), 1)
        pygame.draw.circle(surface, C_TREASURE_GOLD, (hr.centerx, y), 4)
        y += 10

        # Step count
        draw_text(surface, f"Step  {stats['step']:>5}", x, y, size=14, color=C_UI_TEXT)
        y += 20

        # Weather + day/night indicators
        weather_icons = {WEATHER_NONE: "Clear", WEATHER_RAIN: "Rain", WEATHER_STORM: "Storm"}
        wlbl = weather_icons.get(self._weather, "Clear")
        day_phase = self._get_day_phase_label()
        draw_text(surface, f"{wlbl}  |  {day_phase}", hr.right - 12, y - 20,
                  size=11, color=C_UI_TEXT_DIM, align="right")

        pygame.draw.line(surface, C_UI_PANEL_2, (hr.left + 8, y), (hr.right - 8, y), 1)
        y += 6

        # Treasure progress bar
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
            pygame.draw.rect(surface,
                             tuple(min(255, int(v * 1.5)) for v in fc),
                             pygame.Rect(x + 2, y + 2, max(1, fw - 4), 3),
                             border_radius=2)
        draw_text(surface, f"{stats['pct']:.1f}%",
                  hr.right - 10, y - 1, size=13, color=C_UI_TEXT_DIM, align="right")
        y += 22
        pygame.draw.line(surface, C_UI_BORDER, (hr.left + 8, y), (hr.right - 8, y), 1)
        y += 8

        # Entity counts
        draw_text(surface, "ENTITIES", x, y, size=11, color=C_UI_TEXT_DIM, bold=True)
        y += 14
        for label, val, col in [
            ("Hunters",  stats["hunters"],  C_HUNTER_NAV),
            ("Knights",  stats["knights"],  C_KNIGHT),
            ("Hideouts", stats["hideouts"], C_HIDEOUT),
        ]:
            draw_text(surface, label, x + 4, y, size=13, color=C_UI_TEXT_DIM)
            pygame.draw.circle(surface, col, (hr.right - 24, y + 7), 5)
            draw_text(surface, str(val), hr.right - 14, y,
                      size=13, color=col, align="right", bold=True)
            y += 17
        pygame.draw.line(surface, C_UI_PANEL_2, (hr.left + 8, y), (hr.right - 8, y), 1)
        y += 6

        # Treasure breakdown
        draw_text(surface, "TREASURES ON MAP", x, y, size=11, color=C_UI_TEXT_DIM, bold=True)
        y += 14
        for label, val, col in [
            ("  Bronze", stats["bronze"], C_TREASURE_BRONZE),
            ("  Silver", stats["silver"], C_TREASURE_SILVER),
            ("  Gold",   stats["gold"],   C_TREASURE_GOLD),
        ]:
            draw_text(surface, label, x + 4, y, size=13, color=C_UI_TEXT_DIM)
            draw_text(surface, str(val), hr.right - 14, y,
                      size=13, color=col, align="right", bold=True)
            y += 16
        pygame.draw.line(surface, C_UI_BORDER, (hr.left + 8, y), (hr.right - 8, y), 1)
        y += 8

        # Score — big animated
        draw_text(surface, "SCORE", hr.centerx, y, size=11,
                  color=C_UI_TEXT_DIM, bold=True, align="center")
        y += 14
        draw_text(surface, f"{stats['score']:,}", hr.centerx, y,
                  size=26, color=C_UI_TEXT_BRIGHT, bold=True,
                  align="center", shadow=True)
        y += 32

        # Combo display
        if self.combo_count > 1:
            pulse = 0.5 + 0.5 * math.sin(self._time * 6)
            ca    = int(200 + 55 * pulse)
            combo_col = (ca, int(ca * 0.78), 0)
            draw_text(surface, f"COMBO x{self.combo_count}",
                      hr.centerx, y, size=18, color=combo_col,
                      bold=True, align="center", shadow=True)
            y += 24

        self._hud_bottom_y = y

    # ------------------------------------------------------------------
    def _get_day_phase_label(self) -> str:
        c = self._day_cycle
        if c < 0.15 or c > 0.85:
            return "Midnight"
        elif c < 0.35:
            return "Dawn"
        elif c < 0.65:
            return "Noon"
        else:
            return "Dusk"

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

        pygame.draw.rect(surface, (8, 6, 18), mr)
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
                c = C_BOSS_KNIGHT if getattr(e, 'is_boss', False) else C_KNIGHT
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

        draw_text(surface, "MAP", mx + ms // 2, my - 16,
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
        alpha = int(255 * (1.0 - self._t) if self._mode == "in" else 255 * self._t)
        if alpha <= 0:
            return
        s = pygame.Surface(surface.get_size())
        s.fill(C_BLACK)
        s.set_alpha(alpha)
        surface.blit(s, (0, 0))
