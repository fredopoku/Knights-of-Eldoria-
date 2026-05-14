"""
Main gameplay state — handles Watch, Command, and Hero modes.
"""
from __future__ import annotations
import math
import pygame

from src.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, HUD_WIDTH, TILE_SIZE,
    MODE_WATCH, MODE_COMMAND, MODE_HERO,
    DIFF_NORMAL, GRID_SIZE,
    C_UI_TEXT, C_UI_TEXT_BRIGHT, C_UI_TEXT_DIM,
    C_UI_PANEL, C_UI_PANEL_2, C_UI_BORDER, C_UI_BORDER_HI,
    C_UI_ACCENT, C_BTN_NORMAL, C_BTN_BORDER, C_BTN_TEXT,
    C_GREEN, C_RED, C_YELLOW, C_WHITE, C_BLACK,
    C_HUNTER_NAV, C_HUNTER_END, C_HUNTER_STH, C_HUNTER_HERO,
    C_TREASURE_GOLD, C_KNIGHT,
)
from src.simulation import (
    EldoriaSimulation, Hunter, Knight, Treasure, Hideout, Garrison,
    EntityType, HunterSkill, HunterState, KnightState,
    astar,
)
from src.renderer import GameRenderer, FadeTransition
from src.particles import ParticleSystem
from src.ui import (
    Button, Panel, ScrollText, draw_text, draw_panel, draw_hline, get_font,
)


class PlayState:
    # Steps per second at speed=5 (1..10 → 0.5..10 steps/sec)
    _SPEED_TABLE = {1: 0.3, 2: 0.6, 3: 1.0, 4: 2.0, 5: 3.0,
                    6: 5.0, 7: 8.0, 8: 12.0, 9: 18.0, 10: 30.0}

    def __init__(self, game):
        self.game = game
        self.sim: EldoriaSimulation | None = None
        self.renderer: GameRenderer | None = None
        self.particles = ParticleSystem()
        self.fade = FadeTransition(0.35)

        self.mode       = MODE_WATCH
        self.difficulty = DIFF_NORMAL
        self.speed      = 5        # 1..10
        self._step_acc  = 0.0     # accumulator for sub-step timing
        self._running   = True
        self._paused    = False

        # Stats tracking for achievements
        self._total_collects = 0
        self._total_gold     = 0
        self._hero_collect   = False
        self._evasions       = 0

        # Hero camera
        self._cam_x = 0.0
        self._cam_y = 0.0
        self._hero: Hunter | None = None

        # Command mode
        self._selected_hunter: Hunter | None = None

        # Event log
        self._log: ScrollText | None = None

        # Toolbar buttons (built in enter())
        self._toolbar: list[Button] = []

        # Achievement toast display
        self._toast_queue: list[dict] = []
        self._toast_timer   = 0.0
        self._toast_text    = ""

        # Inline pause overlay
        self._show_pause_overlay = False
        self._pause_buttons: list[Button] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def enter(self, mode: str = MODE_WATCH,
              difficulty: str = DIFF_NORMAL,
              _resume: bool = False, **kwargs):
        # Resuming from pause / settings — don't tear down the simulation
        if _resume and self.sim is not None:
            self._running = True
            return

        self.mode       = mode
        self.difficulty = difficulty
        self._running   = True
        self._paused    = False
        self._step_acc  = 0.0
        self._total_collects = 0
        self._total_gold     = 0
        self._hero_collect   = False
        self._evasions       = 0
        self.particles  = ParticleSystem()

        # Build simulation
        self.sim = EldoriaSimulation(
            grid_size=self.game.settings["grid_size"],
            difficulty=difficulty,
        )
        self.sim.initialize()
        self._hook_events()

        # Hero mode: create player hunter
        if mode == MODE_HERO:
            hideouts = [e for e in self.sim.entities if isinstance(e, Hideout)]
            start = hideouts[0].position if hideouts else (0, 0)
            self._hero = Hunter(start, HunterSkill.NAVIGATION,
                                is_hero=True, difficulty=difficulty)
            self._hero.known_hideouts = {e.position
                                         for e in self.sim.entities
                                         if isinstance(e, Hideout)}
            self.sim.add_entity(self._hero)
            self._cam_target_entity()
        else:
            self._hero = None

        # Renderer
        self.renderer = GameRenderer(self.game.screen, self.sim)

        # Event log
        log_rect = pygame.Rect(
            WINDOW_WIDTH - HUD_WIDTH + 8,
            WINDOW_HEIGHT - 200,
            HUD_WIDTH - 16,
            190,
        )
        self._log = ScrollText(log_rect, font_size=13)
        self._log.add("Simulation started!", C_UI_TEXT_BRIGHT)

        # Toolbar
        self._build_toolbar()

        # Fetch saved speed
        self.speed = self.game.settings["sim_speed"]
        self._show_pause_overlay = False

        # Build inline pause overlay buttons
        bw, bh = 240, 48
        cx = WINDOW_WIDTH // 2
        self._pause_buttons = [
            Button(pygame.Rect(cx - bw//2, 280, bw, bh), "RESUME",
                   callback=self._close_pause, font_size=22),
            Button(pygame.Rect(cx - bw//2, 340, bw, bh), "SETTINGS",
                   callback=lambda: self.game.change_state(
                       "settings", return_to="play"), font_size=22),
            Button(pygame.Rect(cx - bw//2, 400, bw, bh), "MAIN MENU",
                   callback=lambda: self.game.change_state("menu"), font_size=22),
        ]

        # Achievement: mode-specific
        if mode == MODE_WATCH:
            self.game.achievements.unlock("watch_mode")
        elif mode == MODE_HERO:
            self.game.achievements.unlock("hero_mode")

        self.fade.fade_in()
        self.game.audio.play_music()

    def exit(self):
        self.game.audio.stop_music()

    # ------------------------------------------------------------------
    # Event wiring
    # ------------------------------------------------------------------
    def _hook_events(self):
        sim = self.sim

        def on_collect():
            self._total_collects += 1
            self._log.add(f"Treasure collected! (#{self._total_collects})", C_TREASURE_GOLD)

        def on_gold_collect():
            self._total_gold += 1

        def on_challenge():
            self._log.add("A hunter was challenged by a knight!", C_RED)

        def on_warning():
            self._log.add("Knight spotted a hunter — pursuing!", C_YELLOW)

        def on_deposit():
            self._log.add("Treasure deposited at hideout.", C_GREEN)

        def on_recruit():
            self._log.add("New hunter recruited!", C_HUNTER_NAV)

        sim.add_listener("collect_treasure", on_collect)
        sim.add_listener("collect_treasure", lambda: self.game.audio.play("collect"))
        sim.add_listener("challenge",        on_challenge)
        sim.add_listener("challenge",        lambda: self.game.audio.play("challenge"))
        sim.add_listener("warning",          on_warning)
        sim.add_listener("warning",          lambda: self.game.audio.play("warning"))
        sim.add_listener("deposit",          on_deposit)
        sim.add_listener("recruit",          on_recruit)
        sim.add_listener("recruit",          lambda: self.game.achievements.unlock("recruiter"))

    def _open_pause(self):
        self._show_pause_overlay = True
        self._running = False

    def _close_pause(self):
        self._show_pause_overlay = False
        self._running = True

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------
    def _build_toolbar(self):
        bw, bh = 70, 30
        y0 = 6
        x0 = WINDOW_WIDTH - HUD_WIDTH + 8
        self._toolbar = []

        # Speed - / +
        def dec_speed():
            self.speed = max(1, self.speed - 1)
            self.game.settings["sim_speed"] = self.speed

        def inc_speed():
            self.speed = min(10, self.speed + 1)
            self.game.settings["sim_speed"] = self.speed

        self._toolbar.append(Button(pygame.Rect(x0,       y0, 34, bh), "–",
                                    callback=dec_speed, font_size=20))
        self._toolbar.append(Button(pygame.Rect(x0 + 36,  y0, 34, bh), "+",
                                    callback=inc_speed, font_size=20))

        # Pause / resume
        def toggle_pause():
            self._running = not self._running

        self._toolbar.append(Button(pygame.Rect(x0 + 76, y0, 68, bh),
                                    "PAUSE", callback=toggle_pause, font_size=15))

        # Pause menu
        self._toolbar.append(Button(
            pygame.Rect(x0 + 150, y0, 68, bh), "MENU",
            callback=lambda: self._open_pause(),
            font_size=15,
        ))

        # Step (single advance)
        self._toolbar.append(Button(
            pygame.Rect(x0 + 224, y0, 54, bh), "STEP",
            callback=self._do_step, font_size=14,
        ))

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event):
        # Inline pause overlay gets first pick
        if self._show_pause_overlay:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._close_pause()
                return
            for b in self._pause_buttons:
                if b.handle_event(event):
                    self.game.audio.play("ui_click")
                    return
            return   # block all other input while overlay is open

        # Pass to log for scroll
        if self._log:
            self._log.handle_event(event)

        for b in self._toolbar:
            if b.handle_event(event):
                self.game.audio.play("ui_click")

        if event.type == pygame.KEYDOWN:
            self._handle_key(event)

        # Command mode: click to select/command
        if self.mode == MODE_COMMAND and event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_command_click(event)

    def _handle_key(self, event: pygame.event.Event):
        k = event.key

        # Hero mode — movement keys take full priority
        if self.mode == MODE_HERO and self._hero:
            dx, dy = 0, 0
            if   k in (pygame.K_w, pygame.K_UP):    dy = -1
            elif k in (pygame.K_s, pygame.K_DOWN):  dy =  1
            elif k in (pygame.K_a, pygame.K_LEFT):  dx = -1
            elif k in (pygame.K_d, pygame.K_RIGHT): dx =  1
            if dx != 0 or dy != 0:
                self._hero.hero_dx = dx
                self._hero.hero_dy = dy
                self._hero.update(self.sim)
                self._cam_target_entity()
                if self.renderer:
                    tw = self.renderer._tile_w
                    th = self.renderer._tile_h
                    mr = self.renderer.map_rect
                else:
                    tw = th = TILE_SIZE
                    mr = pygame.Rect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
                sx = self._hero.position[0]*tw - int(self._cam_x) + mr.left
                sy = self._hero.position[1]*th - int(self._cam_y) + mr.top
                self.particles.dust(sx + tw//2, sy + th//2)
                if self._hero.carried_treasure:
                    self._hero_collect = True
                return   # don't fall through to other key bindings

        # Non-hero key bindings
        if k == pygame.K_ESCAPE:
            if self._show_pause_overlay:
                self._close_pause()
            else:
                self._open_pause()
        elif k == pygame.K_SPACE:
            self._running = not self._running
        elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.speed = max(1, self.speed - 1)
        elif k in (pygame.K_EQUALS, pygame.K_KP_PLUS, pygame.K_KP_EQUALS):
            self.speed = min(10, self.speed + 1)
        elif k == pygame.K_s:
            self._do_step()

    def _handle_command_click(self, event: pygame.event.Event):
        """Click on a hunter to select, click elsewhere to move."""
        if not self.renderer:
            return
        tw  = self.renderer._tile_w
        th  = self.renderer._tile_h
        mx, my = event.pos
        mr  = self.renderer.map_rect
        if not mr.collidepoint(mx, my):
            return
        gx = (mx - mr.left + int(self._cam_x)) // max(1, tw)
        gy = (my - mr.top  + int(self._cam_y)) // max(1, th)
        gx = max(0, min(self.sim.grid_size-1, gx))
        gy = max(0, min(self.sim.grid_size-1, gy))
        pos = (gx, gy)

        # Check if clicking on a hunter
        clicked_hunter = None
        for e in self.sim.entities:
            if isinstance(e, Hunter) and not e.is_hero and e.position == pos:
                clicked_hunter = e
                break

        if clicked_hunter:
            self._selected_hunter = clicked_hunter
            self._log.add(f"Hunter selected ({clicked_hunter.skill.name})", C_UI_ACCENT)
            self.game.achievements.unlock("command_mode")
        elif self._selected_hunter and self._selected_hunter in self.sim.entities:
            h = self._selected_hunter
            h.target_position = pos
            h.current_path = astar(h.position, pos, set(), self.sim.grid_size)
            h.state = HunterState.COLLECTING
            self._log.add(f"Command issued: move to {pos}", C_UI_TEXT_DIM)

    # ------------------------------------------------------------------
    # Simulation step
    # ------------------------------------------------------------------
    def _do_step(self):
        if not self.sim or self.sim.is_complete():
            return
        self.sim.step()
        self._process_sim_events()
        self._check_completion()

    def _process_sim_events(self):
        if not self.sim:
            return
        if self.renderer:
            tw = self.renderer._tile_w
            th = self.renderer._tile_h
            mr = self.renderer.map_rect
        else:
            tw = th = TILE_SIZE
            mr = pygame.Rect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)

        for name, entity in self.sim.events:
            if entity is None:
                continue
            sx = entity.position[0]*tw - int(self._cam_x) + mr.left
            sy = entity.position[1]*th - int(self._cam_y) + mr.top
            cx, cy = sx + tw//2, sy + th//2

            if name == "collect_treasure" and isinstance(entity, Hunter):
                ct = entity.carried_treasure
                if ct:
                    label = ct.label()
                else:
                    label = "gold"
                self.particles.burst_collect(cx, cy, label)
            elif name in ("challenge", "challenge_hit"):
                self.particles.burst_combat(cx, cy)
            elif name == "footsteps" and isinstance(entity, Hunter):
                self.particles.dust(cx, cy)

    def _check_completion(self):
        if not self.sim:
            return
        stats = self.sim.statistics()
        # Achievements
        self.game.achievements.check_stats(
            stats, self.mode, self._total_collects,
            self._total_gold, self._hero_collect, self._evasions
        )
        # Queue any pending achievement toasts
        a = self.game.achievements.pop_pending()
        if a:
            self._toast_queue.append(a)

        if self.sim.is_complete():
            self._running = False
            self.game.change_state(
                "victory" if stats["pct"] >= 50 else "gameover",
                stats=stats, mode=self.mode, difficulty=self.difficulty,
            )

    # ------------------------------------------------------------------
    # Camera
    # ------------------------------------------------------------------
    def _cam_target_entity(self):
        if not self.renderer or not self._hero:
            return
        tw  = self.renderer._tile_w
        th  = self.renderer._tile_h
        mr  = self.renderer.map_rect
        gs  = self.sim.grid_size if self.sim else GRID_SIZE
        tx  = self._hero.position[0] * tw - mr.width  // 2
        ty  = self._hero.position[1] * th - mr.height // 2
        self._cam_x = max(0, min(tx, gs * tw - mr.width))
        self._cam_y = max(0, min(ty, gs * th - mr.height))

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, dt: float):
        self.fade.update(dt)

        for b in self._toolbar:
            b.update(dt)

        for b in self._pause_buttons:
            b.update(dt)

        # Toast
        if self._toast_queue and self._toast_timer <= 0:
            a = self._toast_queue.pop(0)
            self._toast_text  = f"{a['icon']} {a['name']}: {a['desc']}"
            self._toast_timer = 3.5
        if self._toast_timer > 0:
            self._toast_timer -= dt

        self.particles.update(dt)

        if not self._running or self._paused:
            return

        # Accumulate simulation steps
        sps = self._SPEED_TABLE.get(self.speed, 3.0)
        self._step_acc += sps * dt
        steps = int(self._step_acc)
        self._step_acc -= steps
        for _ in range(steps):
            if self.sim and not self.sim.is_complete():
                self._do_step()
            else:
                break

        # Smooth camera follow in hero mode
        if self.mode == MODE_HERO and self._hero and self.renderer:
            self._cam_target_entity()

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        if not self.renderer:
            return

        self.renderer.draw(dt=0.016, cam=(int(self._cam_x), int(self._cam_y)))
        self.particles.draw(surface)

        # Toolbar
        self._draw_toolbar(surface)

        # Mode label
        mode_lbl = {"watch": "WATCH", "command": "COMMAND", "hero": "HERO"}.get(
            self.mode, self.mode.upper())
        draw_text(surface, f"Mode: {mode_lbl}",
                  WINDOW_WIDTH - HUD_WIDTH + 12,
                  WINDOW_HEIGHT - 225,
                  size=13, color=C_UI_ACCENT, bold=True)

        # Sim speed
        draw_text(surface, f"Speed: {self.speed}x",
                  WINDOW_WIDTH - HUD_WIDTH + 148,
                  10, size=13, color=C_UI_TEXT_DIM)

        # Pause indicator
        if not self._running and not self._show_pause_overlay:
            draw_text(surface, "|| PAUSED", WINDOW_WIDTH//2, 12,
                      size=24, color=C_YELLOW, bold=True, align="center")

        # Command mode selection highlight
        if self.mode == MODE_COMMAND and self._selected_hunter:
            h = self._selected_hunter
            if h in self.sim.entities and self.renderer:
                tw  = self.renderer._tile_w
                th  = self.renderer._tile_h
                mr  = self.renderer.map_rect
                sx  = h.position[0]*tw - int(self._cam_x) + mr.left
                sy  = h.position[1]*th - int(self._cam_y) + mr.top
                r   = pygame.Rect(sx-2, sy-2, tw+4, th+4)
                pygame.draw.rect(surface, C_TREASURE_GOLD, r, width=2, border_radius=3)

        # Hero HUD extras
        if self.mode == MODE_HERO and self._hero:
            self._draw_hero_hud(surface)

        # Event log
        if self._log:
            self._log.draw(surface)

        # Achievement toast
        if self._toast_timer > 0:
            self._draw_toast(surface)

        # Inline pause overlay
        if self._show_pause_overlay:
            self._draw_pause_overlay(surface)

        self.fade.draw(surface)

    def _draw_toolbar(self, surface: pygame.Surface):
        for b in self._toolbar:
            b.draw(surface)

    def _draw_hero_hud(self, surface: pygame.Surface):
        h  = self._hero
        px = WINDOW_WIDTH - HUD_WIDTH + 12
        py = WINDOW_HEIGHT - 240
        w  = HUD_WIDTH - 24
        draw_text(surface, "YOUR HUNTER", px, py, size=14,
                  color=C_UI_TEXT_BRIGHT, bold=True)
        py += 18
        # Stamina bar
        draw_text(surface, "Stamina", px, py, size=12, color=C_UI_TEXT_DIM)
        bar = pygame.Rect(px + 60, py, w - 60, 10)
        from src.ui import ProgressBar
        pb = ProgressBar(bar, h.stamina, h.max_stamina)
        pb.draw(surface)
        py += 16
        # Wealth
        draw_text(surface, f"Wealth: {h.wealth:.0f}",
                  px, py, size=12, color=C_TREASURE_GOLD)
        py += 16
        draw_text(surface, f"Treasures: {h.treasures_found}",
                  px, py, size=12, color=C_UI_TEXT)
        py += 16
        draw_text(surface, "WASD / Arrows to move",
                  px, py, size=11, color=C_UI_TEXT_DIM)

    def _draw_toast(self, surface: pygame.Surface):
        alpha = min(1.0, self._toast_timer / 0.6)
        a     = int(255 * alpha)
        s     = pygame.Surface((500, 48), pygame.SRCALPHA)
        s.fill((22, 16, 8, min(220, a)))
        pygame.draw.rect(s, (*C_UI_BORDER_HI, a), s.get_rect(), width=1,
                         border_radius=5)
        font = get_font(16, bold=True)
        ts   = font.render(self._toast_text, True, (220, 200, 150))
        s.blit(ts, (10, 14))
        surface.blit(s, (20, WINDOW_HEIGHT - 60))

    def _draw_pause_overlay(self, surface: pygame.Surface):
        # Dim everything
        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        surface.blit(dim, (0, 0))

        # Panel
        pw, ph = 300, 220
        pr = pygame.Rect((WINDOW_WIDTH - pw)//2, (WINDOW_HEIGHT - ph)//2 - 20,
                         pw, ph)
        draw_panel(surface, pr)
        draw_text(surface, "PAUSED",
                  WINDOW_WIDTH//2, pr.top + 16,
                  size=32, color=C_UI_TEXT_BRIGHT, bold=True,
                  align="center", shadow=True)

        for b in self._pause_buttons:
            b.draw(surface)
