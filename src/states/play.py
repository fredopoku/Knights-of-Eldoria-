"""Main gameplay state — Watch, Command, and Hero modes.
New features: combo system, boss knight spawning, objectives panel.
"""
from __future__ import annotations
import math
import random
import pygame

from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, HUD_WIDTH, TILE_SIZE,
    MODE_WATCH, MODE_COMMAND, MODE_HERO,
    DIFF_NORMAL, GRID_SIZE,
    C_UI_TEXT, C_UI_TEXT_BRIGHT, C_UI_TEXT_DIM,
    C_UI_PANEL, C_UI_PANEL_2, C_UI_BORDER, C_UI_BORDER_HI, C_UI_ACCENT,
    C_GREEN, C_RED, C_YELLOW, C_WHITE, C_BLACK, C_ORANGE,
    C_HUNTER_NAV, C_HUNTER_END, C_HUNTER_STH, C_HUNTER_HERO,
    C_TREASURE_GOLD, C_KNIGHT, C_COMBO,
    C_SPARK_BRONZE, C_SPARK_SILVER, C_SPARK_GOLD,
    C_BOSS_KNIGHT,
)
from src.simulation import (
    EldoriaSimulation, Hunter, Knight, Treasure, Hideout, Garrison,
    EntityType, HunterSkill, HunterState, KnightState, astar, dist,
)
from src.renderer import GameRenderer, FadeTransition
from src.particles import ParticleSystem
from src.ui import Button, ScrollText, draw_text, draw_panel, draw_hline, get_font


class PlayState:
    _SPEED = {1: 0.3, 2: 0.6, 3: 1.0, 4: 2.0, 5: 3.5,
              6: 6.0, 7: 10.0, 8: 16.0, 9: 24.0, 10: 40.0}

    # Steps between boss knight promotion checks
    _BOSS_INTERVAL = 150

    def __init__(self, game):
        self.game       = game
        self.sim        = None
        self.renderer   = None
        self.particles  = ParticleSystem()
        self.fade       = FadeTransition(0.4)

        self.mode       = MODE_WATCH
        self.difficulty = DIFF_NORMAL
        self.speed      = 5
        self._step_acc  = 0.0
        self._running   = True

        # Stats
        self._total_collects = 0
        self._total_gold     = 0
        self._hero_collect   = False
        self._evasions       = 0

        # Camera
        self._cam_x  = 0.0
        self._cam_y  = 0.0
        self._hero   = None

        # Command mode
        self._selected = None

        # UI
        self._log:     ScrollText | None = None
        self._toolbar: list[Button] = []

        # Toast
        self._toast_queue = []
        self._toast_timer = 0.0
        self._toast_text  = ""

        # Danger flash
        self._danger_alpha = 0.0

        # Pause overlay
        self._paused_overlay = False
        self._pause_btns:  list[Button] = []

        # Combo system
        self._combo_count = 0
        self._combo_timer = 0.0
        self._combo_reset_sec = 5.0

        # Boss knight
        self._boss_step_counter = 0   # steps since last boss check
        self._current_boss: Knight | None = None

        # Step counter (mirrors sim.step_count for local use)
        self._steps_taken = 0

    # ------------------------------------------------------------------
    def enter(self, mode=MODE_WATCH, difficulty=DIFF_NORMAL,
              _resume=False, **kwargs):
        if _resume and self.sim is not None:
            self._running = True
            return

        self.mode       = mode
        self.difficulty = difficulty
        self._running   = True
        self._step_acc  = 0.0
        self._total_collects = 0
        self._total_gold     = 0
        self._hero_collect   = False
        self._evasions       = 0
        self.particles       = ParticleSystem()
        self._danger_alpha   = 0.0
        self._paused_overlay = False
        self._combo_count    = 0
        self._combo_timer    = 0.0
        self._boss_step_counter = 0
        self._current_boss   = None
        self._steps_taken    = 0

        gs = self.game.settings["grid_size"]
        self.sim = EldoriaSimulation(grid_size=gs, difficulty=difficulty)
        self.sim.initialize()
        self._hook_events()

        if mode == MODE_HERO:
            hideouts = [e for e in self.sim.entities if isinstance(e, Hideout)]
            start = hideouts[0].position if hideouts else (0, 0)
            self._hero = Hunter(start, HunterSkill.NAVIGATION,
                                is_hero=True, difficulty=difficulty)
            self._hero.known_hideouts = {e.position for e in self.sim.entities
                                         if isinstance(e, Hideout)}
            self.sim.add_entity(self._hero)
            self._cam_to_hero()
        else:
            self._hero = None

        # Renderer — no screen stored; always passed in draw()
        self.renderer = GameRenderer(self.sim)

        # Event log
        log_rect = pygame.Rect(
            WINDOW_WIDTH - HUD_WIDTH + 8,
            WINDOW_HEIGHT - 206,
            HUD_WIDTH - 16, 196,
        )
        self._log = ScrollText(log_rect, font_size=13)
        self._log.add("Simulation started!", C_UI_TEXT_BRIGHT)

        self.speed = self.game.settings["sim_speed"]
        self._build_toolbar()

        bw, bh = 252, 50
        cx = WINDOW_WIDTH // 2
        self._pause_btns = [
            Button(pygame.Rect(cx - bw // 2, 274, bw, bh), "RESUME",
                   callback=self._close_pause, font_size=22),
            Button(pygame.Rect(cx - bw // 2, 336, bw, bh), "SETTINGS",
                   callback=lambda: self.game.change_state("settings", return_to="play"),
                   font_size=22),
            Button(pygame.Rect(cx - bw // 2, 398, bw, bh), "MAIN MENU",
                   callback=lambda: self.game.change_state("menu"), font_size=22),
        ]

        if mode == MODE_WATCH: self.game.achievements.unlock("watch_mode")
        if mode == MODE_HERO:  self.game.achievements.unlock("hero_mode")

        self.fade.fade_in()
        self.game.audio.play_music()

    def exit(self):
        self.game.audio.stop_music()

    # ------------------------------------------------------------------
    def _hook_events(self):
        sim = self

        def on_collect():
            self._total_collects += 1
            self._combo_count    += 1
            self._combo_timer     = self._combo_reset_sec
            self._log.add(
                f"Treasure collected! (#{self._total_collects})"
                + (f"  x{self._combo_count} COMBO!" if self._combo_count > 1 else ""),
                C_TREASURE_GOLD,
            )

        def on_challenge():
            self._log.add("A hunter was challenged!", C_RED)
            self._combo_count = 0   # challenge resets combo

        def on_warning():
            self._log.add("Knight spotted a hunter!", C_YELLOW)

        def on_deposit():
            self._log.add("Treasure deposited at hideout.", C_GREEN)

        def on_recruit():
            self._log.add("New hunter recruited!", C_HUNTER_NAV)

        self.sim.add_listener("collect_treasure", on_collect)
        self.sim.add_listener("collect_treasure",
                              lambda: self.game.audio.play("collect"))
        self.sim.add_listener("challenge",        on_challenge)
        self.sim.add_listener("challenge",
                              lambda: self.game.audio.play("challenge"))
        self.sim.add_listener("warning",          on_warning)
        self.sim.add_listener("warning",
                              lambda: self.game.audio.play("warning"))
        self.sim.add_listener("deposit",          on_deposit)
        self.sim.add_listener("recruit",          on_recruit)
        self.sim.add_listener("recruit",
                              lambda: self.game.achievements.unlock("recruiter"))

    def _open_pause(self):
        self._paused_overlay = True
        self._running = False

    def _close_pause(self):
        self._paused_overlay = False
        self._running = True

    # ------------------------------------------------------------------
    def _build_toolbar(self):
        bh = 30
        y0 = 6
        x0 = WINDOW_WIDTH - HUD_WIDTH + 8
        self._toolbar = []

        def dec():
            self.speed = max(1, self.speed - 1)
            self.game.settings["sim_speed"] = self.speed

        def inc():
            self.speed = min(10, self.speed + 1)
            self.game.settings["sim_speed"] = self.speed

        def tog():
            self._running = not self._running

        self._toolbar += [
            Button(pygame.Rect(x0,      y0, 34, bh), "–",    callback=dec,          font_size=20),
            Button(pygame.Rect(x0 + 36, y0, 34, bh), "+",   callback=inc,          font_size=20),
            Button(pygame.Rect(x0 + 76, y0, 68, bh), "PAUSE", callback=tog,        font_size=14),
            Button(pygame.Rect(x0 + 150, y0, 64, bh), "MENU", callback=self._open_pause, font_size=14),
            Button(pygame.Rect(x0 + 220, y0, 58, bh), "STEP", callback=self._do_step, font_size=13),
        ]

    # ------------------------------------------------------------------
    def handle_event(self, event):
        if self._paused_overlay:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._close_pause()
                return
            for b in self._pause_btns:
                if b.handle_event(event):
                    self.game.audio.play("ui_click")
                    return
            return

        if self._log:
            self._log.handle_event(event)
        for b in self._toolbar:
            if b.handle_event(event):
                self.game.audio.play("ui_click")

        if event.type == pygame.KEYDOWN:
            self._key(event)
        if self.mode == MODE_COMMAND and event.type == pygame.MOUSEBUTTONDOWN:
            self._cmd_click(event)

    def _key(self, event):
        k = event.key

        if self.mode == MODE_HERO and self._hero:
            dx = dy = 0
            if k in (pygame.K_w, pygame.K_UP):     dy = -1
            elif k in (pygame.K_s, pygame.K_DOWN): dy =  1
            elif k in (pygame.K_a, pygame.K_LEFT): dx = -1
            elif k in (pygame.K_d, pygame.K_RIGHT):dx =  1
            if dx or dy:
                self._hero.hero_dx = dx
                self._hero.hero_dy = dy
                self._hero.update(self.sim)
                self._cam_to_hero()
                if self._hero.carried_treasure:
                    self._hero_collect = True
                if self.renderer:
                    tw = self.renderer._tile_w
                    th = self.renderer._tile_h
                    mr = self.renderer.map_rect
                    sx = self._hero.position[0] * tw - int(self._cam_x) + mr.left
                    sy = self._hero.position[1] * th - int(self._cam_y) + mr.top
                    self.particles.dust(sx + tw // 2, sy + th // 2)
                return

        if k == pygame.K_ESCAPE:
            self._close_pause() if self._paused_overlay else self._open_pause()
        elif k == pygame.K_SPACE:
            self._running = not self._running
        elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.speed = max(1, self.speed - 1)
        elif k in (pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.speed = min(10, self.speed + 1)
        elif k == pygame.K_s:
            self._do_step()

    def _cmd_click(self, event):
        if not self.renderer:
            return
        tw = self.renderer._tile_w
        th = self.renderer._tile_h
        mx, my = event.pos
        mr = self.renderer.map_rect
        if not mr.collidepoint(mx, my):
            return
        gx = (mx - mr.left + int(self._cam_x)) // max(1, tw)
        gy = (my - mr.top  + int(self._cam_y)) // max(1, th)
        gx = max(0, min(self.sim.grid_size - 1, gx))
        gy = max(0, min(self.sim.grid_size - 1, gy))
        pos = (gx, gy)

        clicked = None
        for e in self.sim.entities:
            if isinstance(e, Hunter) and not e.is_hero and e.position == pos:
                clicked = e
                break

        if clicked:
            self._selected = clicked
            self._log.add(f"Hunter selected ({clicked.skill.name})", C_UI_ACCENT)
            self.game.achievements.unlock("command_mode")
        elif self._selected and self._selected in self.sim.entities:
            h = self._selected
            h.target_position = pos
            h.current_path    = astar(h.position, pos, set(), self.sim.grid_size)
            h.state           = HunterState.COLLECTING
            self._log.add(f"Command: move to {pos}", C_UI_TEXT_DIM)

    # ------------------------------------------------------------------
    def _do_step(self):
        if not self.sim or self.sim.is_complete():
            return
        self.sim.step()
        self._steps_taken += 1
        self._process_events()
        self._check_boss_spawn()
        self._check_end()

    def _check_boss_spawn(self):
        """Every _BOSS_INTERVAL steps, promote a random knight to boss."""
        self._boss_step_counter += 1
        if self._boss_step_counter < self._BOSS_INTERVAL:
            return
        self._boss_step_counter = 0

        knights = [e for e in self.sim.entities if isinstance(e, Knight)]
        if not knights:
            return

        # Demote old boss first
        if self._current_boss and self._current_boss in self.sim.entities:
            self._current_boss.is_boss = False

        new_boss = random.choice(knights)
        new_boss.is_boss = True
        self._current_boss = new_boss
        self._toast_queue.append({
            "icon": "!!",
            "name": "BOSS KNIGHT",
            "desc": "A fearsome knight has emerged!",
        })
        self._log.add("A BOSS KNIGHT has appeared!", C_RED)

    def _process_events(self):
        if not self.sim or not self.renderer:
            return
        tw = self.renderer._tile_w
        th = self.renderer._tile_h
        mr = self.renderer.map_rect

        for name, entity in self.sim.events:
            if entity is None:
                continue
            sx = entity.position[0] * tw - int(self._cam_x) + mr.left
            sy = entity.position[1] * th - int(self._cam_y) + mr.top
            cx, cy = sx + tw // 2, sy + th // 2

            if name == "collect_treasure" and isinstance(entity, Hunter):
                ct    = entity.carried_treasure
                label = ct.label() if ct else "gold"
                self.particles.burst_collect(cx, cy, label)
                pts = {"bronze": "+3", "silver": "+7", "gold": "+13"}.get(label, "+pts")
                col = {"bronze": C_SPARK_BRONZE,
                       "silver": C_SPARK_SILVER,
                       "gold":   C_SPARK_GOLD}.get(label, C_TREASURE_GOLD)
                self.particles.add_popup(cx, cy - 20, pts, col)
                # Extra combo popup
                if self._combo_count > 1:
                    self.particles.add_popup(cx, cy - 38,
                                            f"x{self._combo_count}!", C_COMBO)

            elif name in ("challenge", "challenge_hit"):
                self.particles.burst_combat(cx, cy)
                self._danger_alpha = 1.0

            elif name == "footsteps":
                if isinstance(entity, Hunter):
                    self.particles.dust(cx, cy)

    def _check_end(self):
        if not self.sim:
            return
        stats = self.sim.statistics()
        self.game.achievements.check_stats(
            stats, self.mode, self._total_collects,
            self._total_gold, self._hero_collect, self._evasions)
        a = self.game.achievements.pop_pending()
        if a:
            self._toast_queue.append(a)
        if self.sim.is_complete():
            self._running = False
            result = "victory" if stats["pct"] >= 50 else "gameover"
            self.game.change_state(result, stats=stats,
                                   mode=self.mode, difficulty=self.difficulty)

    # ------------------------------------------------------------------
    def _cam_to_hero(self):
        if not self._hero or not self.renderer:
            return
        tw = self.renderer._tile_w
        th = self.renderer._tile_h
        mr = self.renderer.map_rect
        gs = self.sim.grid_size
        tx = self._hero.position[0] * tw - mr.width  // 2
        ty = self._hero.position[1] * th - mr.height // 2
        self._cam_x = max(0.0, min(float(tx), gs * tw - mr.width))
        self._cam_y = max(0.0, min(float(ty), gs * th - mr.height))

    def _check_danger(self):
        if not self.sim:
            return False
        hunters = [e for e in self.sim.entities if isinstance(e, Hunter)]
        knights = [e for e in self.sim.entities if isinstance(e, Knight)]
        gs = self.sim.grid_size
        for k in knights:
            if k.state == KnightState.PURSUING:
                for h in hunters:
                    if dist(k.position, h.position, gs) <= 4:
                        return True
        return False

    # ------------------------------------------------------------------
    def update(self, dt: float):
        self.fade.update(dt)
        for b in self._toolbar:    b.update(dt)
        for b in self._pause_btns: b.update(dt)

        # Toast management
        if self._toast_queue and self._toast_timer <= 0:
            a = self._toast_queue.pop(0)
            self._toast_text  = f"  {a.get('icon', '')}  {a.get('name', '')}: {a.get('desc', '')}"
            self._toast_timer = 4.0
        if self._toast_timer > 0:
            self._toast_timer -= dt

        # Combo timeout
        if self._combo_count > 0:
            self._combo_timer -= dt
            if self._combo_timer <= 0:
                self._combo_count = 0

        # Sync combo to renderer for HUD display
        if self.renderer:
            self.renderer.combo_count = self._combo_count
            self.renderer.combo_timer = self._combo_timer

        # Danger flash fade
        if self._danger_alpha > 0:
            self._danger_alpha = max(0.0, self._danger_alpha - dt * 1.8)

        self.particles.update(dt)

        if not self._running or self._paused_overlay:
            return

        sps = self._SPEED.get(self.speed, 3.5)
        self._step_acc += sps * dt
        steps = int(self._step_acc)
        self._step_acc -= steps
        for _ in range(steps):
            if self.sim and not self.sim.is_complete():
                self._do_step()
            else:
                break

        if self.mode == MODE_HERO and self._hero:
            self._cam_to_hero()

        # Danger sparkles
        if self._check_danger():
            self._danger_alpha = min(1.0, self._danger_alpha + dt * 3)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        if not self.renderer:
            surface.fill((10, 0, 0))
            font = pygame.font.Font(None, 36)
            surface.blit(font.render("Initialising…", True, (255, 200, 100)), (40, 40))
            return

        cam = (int(self._cam_x), int(self._cam_y))
        self.renderer.draw(surface, dt=0.016, cam=cam)
        self.particles.draw(surface)

        self._draw_toolbar(surface)

        # Mode label
        ml = {"watch": "WATCH", "command": "COMMAND", "hero": "HERO"}.get(
            self.mode, self.mode.upper())
        draw_text(surface, f"Mode: {ml}",
                  WINDOW_WIDTH - HUD_WIDTH + 12, WINDOW_HEIGHT - 228,
                  size=13, color=C_UI_ACCENT, bold=True)

        # Speed label (nicer)
        self._draw_speed_indicator(surface)

        # PAUSED banner
        if not self._running and not self._paused_overlay:
            self._draw_pause_banner(surface)

        # Danger red vignette flash
        if self._danger_alpha > 0.02:
            da = int(self._danger_alpha * 70)
            ds = pygame.Surface((WINDOW_WIDTH - HUD_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            ds.fill((220, 30, 30, da))
            surface.blit(ds, (0, 0))

        # Command selection ring
        if self.mode == MODE_COMMAND and self._selected:
            h = self._selected
            if h in self.sim.entities:
                tw = self.renderer._tile_w
                th = self.renderer._tile_h
                mr = self.renderer.map_rect
                sx = h.position[0] * tw - int(self._cam_x) + mr.left
                sy = h.position[1] * th - int(self._cam_y) + mr.top
                rr = pygame.Rect(sx - 3, sy - 3, tw + 6, th + 6)
                pygame.draw.rect(surface, C_TREASURE_GOLD, rr, width=2, border_radius=4)
                pygame.draw.rect(surface, C_UI_BORDER_HI,  rr.inflate(4, 4), width=1,
                                 border_radius=6)

        if self.mode == MODE_HERO and self._hero:
            self._draw_hero_hud(surface)

        # Objectives panel
        self._draw_objectives(surface)

        if self._log:
            self._log.draw(surface)

        if self._toast_timer > 0:
            self._draw_toast(surface)

        if self._paused_overlay:
            self._draw_pause_overlay(surface)

        self.fade.draw(surface)

    # ------------------------------------------------------------------
    def _draw_toolbar(self, surface):
        for b in self._toolbar:
            b.draw(surface)

    def _draw_speed_indicator(self, surface):
        """Nicer speed bar in the toolbar area."""
        x0 = WINDOW_WIDTH - HUD_WIDTH + 148
        y0 = 10
        draw_text(surface, f"Speed: {self.speed}x",
                  x0, y0, size=13, color=C_UI_TEXT_DIM)
        # Tiny segmented bar
        seg_w, seg_h = 6, 14
        bx = x0 + 76
        by = y0 - 1
        for i in range(10):
            col = C_GREEN if i < self.speed else (30, 25, 50)
            pygame.draw.rect(surface, col,
                             pygame.Rect(bx + i * (seg_w + 2), by, seg_w, seg_h),
                             border_radius=2)

    def _draw_pause_banner(self, surface):
        from pygame.time import get_ticks
        t = get_ticks() / 1000.0
        a = int(200 + 55 * math.sin(t * 3.0))
        draw_text(surface, "|| PAUSED",
                  WINDOW_WIDTH // 2, 10,
                  size=28, color=(a, int(a * 0.85), 40),
                  bold=True, align="center", shadow=True)

    def _draw_hero_hud(self, surface):
        h  = self._hero
        px = WINDOW_WIDTH - HUD_WIDTH + 14
        py = WINDOW_HEIGHT - 252
        w  = HUD_WIDTH - 28
        draw_text(surface, "YOUR HUNTER", px, py, size=13,
                  color=C_UI_TEXT_BRIGHT, bold=True)
        py += 18
        draw_text(surface, "Stamina", px, py, size=12, color=C_UI_TEXT_DIM)
        from src.ui import ProgressBar
        pb = ProgressBar(pygame.Rect(px + 58, py, w - 58, 10), h.stamina, h.max_stamina)
        pb.draw(surface)
        py += 16
        draw_text(surface, f"Wealth: {h.wealth:.0f}", px, py, size=12, color=C_TREASURE_GOLD)
        py += 16
        draw_text(surface, f"Found:  {h.treasures_found}", px, py, size=12, color=C_UI_TEXT)
        py += 16
        draw_text(surface, "WASD / Arrows to move", px, py, size=11, color=C_UI_TEXT_DIM)

    def _draw_objectives(self, surface):
        """Small objectives panel on the map (top-left area)."""
        if not self.sim:
            return
        stats  = self.sim.statistics()
        pct    = stats.get("pct", 0)
        hunters= stats.get("hunters", 0)

        ox, oy, ow, oh = 8, 44, 210, 64
        panel_rect = pygame.Rect(ox, oy, ow, oh)
        # Semi-transparent panel
        ps = pygame.Surface((ow, oh), pygame.SRCALPHA)
        ps.fill((18, 14, 36, 200))
        pygame.draw.rect(ps, (*[60, 45, 100], 180), ps.get_rect(), width=1, border_radius=6)
        surface.blit(ps, (ox, oy))

        draw_text(surface, "OBJECTIVES", ox + 6, oy + 4,
                  size=11, color=C_UI_TEXT_DIM, bold=True)

        obj1_col = C_GREEN if pct >= 50 else C_YELLOW if pct >= 25 else C_UI_TEXT_DIM
        draw_text(surface, f"Collect 50% treasure  {pct:.0f}%",
                  ox + 6, oy + 20, size=12, color=obj1_col)

        obj2_col = C_GREEN if hunters >= 2 else C_RED
        draw_text(surface, f"Keep 2+ hunters alive  {hunters}",
                  ox + 6, oy + 38, size=12, color=obj2_col)

    def _draw_toast(self, surface):
        alpha = min(1.0, self._toast_timer / 0.7)
        a     = int(255 * alpha)
        s     = pygame.Surface((560, 54), pygame.SRCALPHA)
        s.fill((18, 14, 32, min(230, a)))
        pygame.draw.rect(s, (*C_UI_BORDER_HI, a), s.get_rect(), width=1, border_radius=6)
        font = get_font(16, bold=True)
        ts   = font.render(self._toast_text, True, (235, 215, 168))
        s.blit(ts, (12, 17))
        surface.blit(s, (16, WINDOW_HEIGHT - 66))

    def _draw_pause_overlay(self, surface):
        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 175))
        surface.blit(dim, (0, 0))
        pw, ph = 320, 248
        pr = pygame.Rect((WINDOW_WIDTH - pw) // 2, (WINDOW_HEIGHT - ph) // 2 - 20, pw, ph)
        draw_panel(surface, pr)
        draw_text(surface, "PAUSED",
                  WINDOW_WIDTH // 2, pr.top + 18,
                  size=34, color=C_UI_TEXT_BRIGHT, bold=True,
                  align="center", shadow=True)
        draw_hline(surface, pr.left + 12, pr.right - 12, pr.top + 56)
        for b in self._pause_btns:
            b.draw(surface)
