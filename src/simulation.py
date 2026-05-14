"""
Core simulation: entities, AI state-machines, A* pathfinding, world logic.
"""
from __future__ import annotations
import enum
import math
import random
from typing import Optional

from src.constants import (
    GRID_SIZE, VISIBILITY_RANGE, KNIGHT_DETECTION_RANGE,
    STAMINA_MOVEMENT_COST, STAMINA_CRITICAL_LEVEL,
    KNIGHT_CHASE_ENERGY_COST, KNIGHT_LOW_ENERGY,
    TREASURE_DECAY_RATE,
    DIFFICULTY_SETTINGS, DIFF_NORMAL,
)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------
class EntityType(enum.Enum):
    EMPTY           = 0
    TREASURE_BRONZE = 1
    TREASURE_SILVER = 2
    TREASURE_GOLD   = 3
    HUNTER          = 4
    HIDEOUT         = 5
    KNIGHT          = 6
    GARRISON        = 7


class HunterSkill(enum.Enum):
    NAVIGATION = 0   # Farther sight, better paths
    ENDURANCE  = 1   # Lower stamina cost, faster recovery
    STEALTH    = 2   # Harder for knights to detect


class HunterState(enum.Enum):
    EXPLORING  = 0
    COLLECTING = 1
    RETURNING  = 2
    RESTING    = 3
    EVADING    = 4
    COLLAPSED  = 5


class KnightState(enum.Enum):
    PATROLLING  = 0
    PURSUING    = 1
    CHALLENGING = 2
    RESTING     = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def dist(p1, p2, grid=GRID_SIZE) -> float:
    dx = min(abs(p2[0] - p1[0]), grid - abs(p2[0] - p1[0]))
    dy = min(abs(p2[1] - p1[1]), grid - abs(p2[1] - p1[1]))
    return math.sqrt(dx * dx + dy * dy)


def neighbors(pos, grid=GRID_SIZE):
    x, y = pos
    return [
        ((x + dx) % grid, (y + dy) % grid)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        if not (dx == 0 and dy == 0)
    ]


def astar(start, goal, obstacles, grid=GRID_SIZE):
    if start == goal:
        return [start]

    def h(p):
        dx = min(abs(goal[0] - p[0]), grid - abs(goal[0] - p[0]))
        dy = min(abs(goal[1] - p[1]), grid - abs(goal[1] - p[1]))
        return dx + dy

    open_set = {start}
    closed   = set()
    g = {start: 0}
    f = {start: h(start)}
    par = {}

    while open_set:
        cur = min(open_set, key=lambda p: f.get(p, 1e9))
        if cur == goal:
            path = [cur]
            while cur in par:
                cur = par[cur]
                path.append(cur)
            return path[::-1]
        open_set.discard(cur)
        closed.add(cur)
        for nb in neighbors(cur, grid):
            if nb in closed or nb in obstacles:
                continue
            tg = g[cur] + 1
            if nb not in open_set:
                open_set.add(nb)
            elif tg >= g.get(nb, 1e9):
                continue
            par[nb] = cur
            g[nb]   = tg
            f[nb]   = tg + h(nb)
    return []


# ---------------------------------------------------------------------------
# Entity base
# ---------------------------------------------------------------------------
class Entity:
    def __init__(self, etype: EntityType, pos):
        self.entity_type = etype
        self.position    = tuple(pos)
        self.id          = id(self)

    def update(self, sim: "EldoriaSimulation"):
        pass

    def __eq__(self, o):
        return isinstance(o, Entity) and self.id == o.id

    def __hash__(self):
        return hash(self.id)


# ---------------------------------------------------------------------------
# Treasure
# ---------------------------------------------------------------------------
class Treasure(Entity):
    _VALUES = {
        EntityType.TREASURE_BRONZE: 100.0,
        EntityType.TREASURE_SILVER: 200.0,
        EntityType.TREASURE_GOLD:   300.0,
    }
    _PCT = {
        EntityType.TREASURE_BRONZE: 3.0,
        EntityType.TREASURE_SILVER: 7.0,
        EntityType.TREASURE_GOLD:   13.0,
    }
    _LABELS = {
        EntityType.TREASURE_BRONZE: "bronze",
        EntityType.TREASURE_SILVER: "silver",
        EntityType.TREASURE_GOLD:   "gold",
    }

    def __init__(self, ttype: EntityType, pos):
        super().__init__(ttype, pos)
        self.initial_value  = self._VALUES.get(ttype, 100.0)
        self.current_value  = self.initial_value

    def value_pct(self) -> float:
        return self._PCT.get(self.entity_type, 0.0)

    def label(self) -> str:
        return self._LABELS.get(self.entity_type, "treasure")

    def update(self, sim):
        self.current_value -= self.initial_value * (TREASURE_DECAY_RATE / 100)
        if self.current_value <= 0:
            sim.remove_entity(self)


# ---------------------------------------------------------------------------
# Hunter
# ---------------------------------------------------------------------------
class Hunter(Entity):
    def __init__(self, pos, skill: HunterSkill, is_hero: bool = False,
                 difficulty: str = DIFF_NORMAL):
        super().__init__(EntityType.HUNTER, pos)
        self.skill            = skill
        self.is_hero          = is_hero
        self.stamina          = 100.0
        self.max_stamina      = 100.0
        self.state            = HunterState.EXPLORING
        self.carried_treasure: Optional[Treasure] = None
        self.wealth           = 0.0
        self.collapsed_counter = 0
        self.steps_taken      = 0
        self.treasures_found  = 0

        # Difficulty scaling
        ds = DIFFICULTY_SETTINGS.get(difficulty, DIFFICULTY_SETTINGS[DIFF_NORMAL])
        self._stamina_cost_mult = ds["stamina_cost"]

        # Memory
        self.known_treasures: dict[tuple, EntityType] = {}
        self.known_hideouts:  set[tuple]              = set()
        self.known_knights:   dict[tuple, int]        = {}

        # Pathfinding
        self.current_path:   list[tuple] = []
        self.target_position: Optional[tuple] = None

        # Hero input (set externally when is_hero=True)
        self.hero_dx = 0
        self.hero_dy = 0

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------
    def update(self, sim):
        if self.is_hero:
            self._update_hero(sim)
            return
        self._update_knowledge(sim)
        if self.state == HunterState.COLLAPSED:
            self._collapsed(sim)
        elif self.stamina <= 0:
            self.state = HunterState.COLLAPSED
            self.collapsed_counter = 3
        elif self.state == HunterState.RESTING:
            self._resting(sim)
        elif self.stamina <= STAMINA_CRITICAL_LEVEL:
            self._seek_hideout(sim)
        elif self.state == HunterState.EVADING:
            self._evading(sim)
        elif self.state == HunterState.RETURNING:
            self._returning(sim)
        elif self.state == HunterState.COLLECTING:
            self._collecting(sim)
        else:
            self._exploring(sim)

    def _update_hero(self, sim):
        """Process player-input movement for hero mode."""
        self._update_knowledge(sim)
        if self.hero_dx != 0 or self.hero_dy != 0:
            nx = (self.position[0] + self.hero_dx) % sim.grid_size
            ny = (self.position[1] + self.hero_dy) % sim.grid_size
            self.position = (nx, ny)
            cost = STAMINA_MOVEMENT_COST * self._stamina_cost_mult
            if self.skill == HunterSkill.ENDURANCE:
                cost *= 0.8
            self.stamina = max(0, self.stamina - cost)
            self.steps_taken += 1
            self.hero_dx = self.hero_dy = 0
            sim.trigger_event("footsteps", self)
            # Auto-collect any treasure at position
            for e in sim.get_entities_at(self.position):
                if isinstance(e, Treasure) and self.carried_treasure is None:
                    self.carried_treasure = e
                    self.treasures_found += 1
                    sim.remove_entity(e)
                    sim.trigger_event("collect_treasure", self)
                    break
        # Auto-deposit at hideout
        if self.carried_treasure:
            for e in sim.get_entities_at(self.position):
                if isinstance(e, Hideout):
                    val = self.carried_treasure.value_pct()
                    self.wealth += val
                    e.store_treasure(self.carried_treasure)
                    self.carried_treasure = None
                    sim.trigger_event("deposit", self)
                    break
        # Regen stamina at hideout
        for e in sim.get_entities_at(self.position):
            if isinstance(e, Hideout):
                regen = 1.5
                if self.skill == HunterSkill.ENDURANCE:
                    regen = 2.5
                self.stamina = min(self.max_stamina, self.stamina + regen)

    # ------------------------------------------------------------------
    # AI helpers
    # ------------------------------------------------------------------
    def _update_knowledge(self, sim):
        vr = VISIBILITY_RANGE + (1 if self.skill == HunterSkill.NAVIGATION else 0)
        for dx in range(-vr, vr + 1):
            for dy in range(-vr, vr + 1):
                if dx * dx + dy * dy > vr * vr:
                    continue
                x = (self.position[0] + dx) % sim.grid_size
                y = (self.position[1] + dy) % sim.grid_size
                p = (x, y)
                for e in sim.get_entities_at(p):
                    if isinstance(e, Treasure):
                        self.known_treasures[p] = e.entity_type
                    elif isinstance(e, Hideout):
                        self.known_hideouts.add(p)
                    elif isinstance(e, Knight):
                        self.known_knights[p] = sim.current_step
        # Prune stale treasure knowledge
        to_del = [p for p in self.known_treasures
                  if not any(isinstance(e, Treasure)
                             for e in sim.get_entities_at(p))]
        for p in to_del:
            del self.known_treasures[p]

    def _obstacles(self, sim):
        obs = set()
        for kp in self.known_knights:
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    obs.add(((kp[0]+dx) % sim.grid_size,
                             (kp[1]+dy) % sim.grid_size))
        return obs

    def _move(self, sim, next_pos):
        self.position = next_pos
        self.current_path = self.current_path[1:]
        cost = STAMINA_MOVEMENT_COST * self._stamina_cost_mult
        if self.skill == HunterSkill.ENDURANCE:
            cost *= 0.8
        self.stamina -= cost
        self.steps_taken += 1
        if random.random() < 0.04:
            sim.trigger_event("footsteps", self)

    def _move_along_path(self, sim):
        if len(self.current_path) > 1:
            self._move(sim, self.current_path[1])

    def _knight_nearby(self, sim):
        return any(isinstance(e, Knight) and
                   dist(self.position, e.position, sim.grid_size) <= KNIGHT_DETECTION_RANGE
                   for e in sim.entities)

    def _collapsed(self, sim):
        self.collapsed_counter -= 1
        if self.collapsed_counter <= 0:
            if self.carried_treasure:
                self.carried_treasure.position = self.position
                sim.add_entity(self.carried_treasure)
                self.carried_treasure = None
            sim.remove_entity(self)

    def _resting(self, sim):
        regen = 1.0
        if self.skill == HunterSkill.ENDURANCE:
            regen = 1.5
        self.stamina = min(self.max_stamina, self.stamina + regen)

        hideout = next((e for e in sim.get_entities_at(self.position)
                        if isinstance(e, Hideout)), None)
        if not hideout:
            self.state = HunterState.EXPLORING
            return

        if self.carried_treasure:
            self.wealth += self.carried_treasure.value_pct()
            self.treasures_found += 1
            hideout.store_treasure(self.carried_treasure)
            self.carried_treasure = None
            sim.trigger_event("deposit", self)

        # Share knowledge
        for e in sim.get_entities_at(self.position):
            if isinstance(e, Hunter) and e is not self:
                e.known_treasures.update(self.known_treasures)
                e.known_hideouts.update(self.known_hideouts)
                for p, t in self.known_knights.items():
                    if p not in e.known_knights or t > e.known_knights[p]:
                        e.known_knights[p] = t

        if self.stamina >= 90:
            self.state = HunterState.EXPLORING

    def _seek_hideout(self, sim):
        if not self.known_hideouts:
            self._exploring(sim, conservative=True)
            return
        closest = min(self.known_hideouts,
                      key=lambda p: dist(self.position, p, sim.grid_size))
        self.target_position = closest
        self.current_path = astar(self.position, closest, self._obstacles(sim),
                                  sim.grid_size)
        if len(self.current_path) > 1:
            self._move_along_path(sim)
        else:
            self.state = HunterState.RESTING

    def _evading(self, sim):
        if not self._knight_nearby(sim):
            self.state = (HunterState.RETURNING if self.carried_treasure
                          else HunterState.EXPLORING)
            return
        safe = [nb for nb in neighbors(self.position, sim.grid_size)
                if all(dist(nb, e.position, sim.grid_size) > KNIGHT_DETECTION_RANGE - 1
                       for e in sim.entities if isinstance(e, Knight))]
        dest = random.choice(safe) if safe else random.choice(
            neighbors(self.position, sim.grid_size))
        if self.carried_treasure and random.random() < 0.25:
            self.carried_treasure.position = self.position
            sim.add_entity(self.carried_treasure)
            self.carried_treasure = None
        self._move(sim, dest)
        self.current_path = [self.position]

    def _returning(self, sim):
        if not self.carried_treasure:
            self.state = HunterState.EXPLORING
            return
        if self._knight_nearby(sim):
            self.state = HunterState.EVADING
            return
        if not self.known_hideouts:
            self._exploring(sim)
            return
        closest = min(self.known_hideouts,
                      key=lambda p: dist(self.position, p, sim.grid_size))
        if self.target_position != closest:
            self.target_position = closest
            self.current_path = astar(self.position, closest,
                                      self._obstacles(sim), sim.grid_size)
        if len(self.current_path) > 1:
            self._move_along_path(sim)
        else:
            self.state = HunterState.RESTING

    def _collecting(self, sim):
        if self.carried_treasure:
            self.state = HunterState.RETURNING
            return
        if self._knight_nearby(sim):
            self.state = HunterState.EVADING
            return
        if not self.target_position or self.target_position not in self.known_treasures:
            self.state = HunterState.EXPLORING
            return
        if len(self.current_path) > 1:
            self._move_along_path(sim)
        else:
            treasures = [e for e in sim.get_entities_at(self.position)
                         if isinstance(e, Treasure)]
            if treasures:
                t = max(treasures, key=lambda x: x.value_pct())
                self.carried_treasure = t
                sim.remove_entity(t)
                sim.trigger_event("collect_treasure", self)
                self.state = HunterState.RETURNING
            else:
                self.known_treasures.pop(self.position, None)
                self.state = HunterState.EXPLORING

    def _exploring(self, sim, conservative=False):
        if self._knight_nearby(sim):
            self.state = HunterState.EVADING
            return
        if self.carried_treasure:
            self.state = HunterState.RETURNING
            return
        if self.known_treasures:
            def priority(item):
                p, t = item
                val = {EntityType.TREASURE_GOLD: 3,
                       EntityType.TREASURE_SILVER: 2}.get(t, 1)
                return val / (dist(self.position, p, sim.grid_size) + 1)
            best = max(self.known_treasures.items(), key=priority)
            self.target_position = best[0]
            self.current_path = astar(self.position, best[0],
                                      self._obstacles(sim), sim.grid_size)
            self.state = HunterState.COLLECTING
            return
        if conservative or not self.current_path:
            self._new_explore_path(sim)
        if self.current_path:
            self._move_along_path(sim)

    def _new_explore_path(self, sim):
        explored = set(self.known_treasures) | self.known_hideouts
        unexplored = [(x, y)
                      for x in range(sim.grid_size)
                      for y in range(sim.grid_size)
                      if (x, y) not in explored]
        if not unexplored:
            target = (random.randint(0, sim.grid_size-1),
                      random.randint(0, sim.grid_size-1))
        else:
            target = min(unexplored,
                         key=lambda p: dist(self.position, p, sim.grid_size))
        self.current_path = astar(self.position, target,
                                   self._obstacles(sim), sim.grid_size)
        self.target_position = target


# ---------------------------------------------------------------------------
# Hideout
# ---------------------------------------------------------------------------
class Hideout(Entity):
    def __init__(self, pos):
        super().__init__(EntityType.HIDEOUT, pos)
        self.treasure_count = 0
        self.total_value    = 0.0
        self.hunters_inside: list[Hunter] = []
        self.skill_counts: dict[HunterSkill, int] = {s: 0 for s in HunterSkill}

    def update(self, sim):
        self.hunters_inside = [e for e in sim.get_entities_at(self.position)
                               if isinstance(e, Hunter)]
        self.skill_counts   = {s: 0 for s in HunterSkill}
        for h in self.hunters_inside:
            self.skill_counts[h.skill] += 1

        # Recruit if diverse skills and not too crowded
        if 0 < len(self.hunters_inside) < 5:
            if min(self.skill_counts.values()) > 0 and random.random() < 0.15:
                self._recruit(sim)

    def store_treasure(self, t: Treasure):
        self.treasure_count += 1
        self.total_value    += t.value_pct()

    def _recruit(self, sim):
        skill = random.choice(list(HunterSkill))
        nh = Hunter(self.position, skill)
        for h in self.hunters_inside:
            nh.known_treasures.update(h.known_treasures)
            nh.known_hideouts.update(h.known_hideouts)
            for p, t in h.known_knights.items():
                if p not in nh.known_knights or t > nh.known_knights[p]:
                    nh.known_knights[p] = t
        sim.add_entity(nh)
        sim.trigger_event("recruit", nh)


# ---------------------------------------------------------------------------
# Knight
# ---------------------------------------------------------------------------
class Knight(Entity):
    def __init__(self, pos, difficulty: str = DIFF_NORMAL):
        super().__init__(EntityType.KNIGHT, pos)
        ds = DIFFICULTY_SETTINGS.get(difficulty, DIFFICULTY_SETTINGS[DIFF_NORMAL])
        self.energy        = 100.0
        self.max_energy    = 100.0
        self.state         = KnightState.PATROLLING
        self.target_hunter: Optional[Hunter] = None
        self.patrol_path:  list[tuple] = []
        self.current_path: list[tuple] = []
        self.target_pos:   Optional[tuple] = None
        self._detect_mult  = ds["knight_scale"]
        self.challenges    = 0

    def update(self, sim):
        prev = self.state
        if self.state == KnightState.RESTING:
            self._resting(sim)
        elif self.energy <= KNIGHT_LOW_ENERGY:
            self._seek_garrison(sim)
        elif self.state == KnightState.CHALLENGING:
            self._challenging(sim)
        elif self.state == KnightState.PURSUING:
            self._pursuing(sim)
        else:
            self._patrolling(sim)
        if prev != self.state:
            if self.state == KnightState.PURSUING:
                sim.trigger_event("warning", self)
            elif self.state == KnightState.CHALLENGING:
                sim.trigger_event("challenge", self)

    def _resting(self, sim):
        self.energy = min(self.max_energy, self.energy + 10)
        if self.energy >= 100:
            self.state = KnightState.PATROLLING
            self._gen_patrol()

    def _seek_garrison(self, sim):
        garrisons = [e for e in sim.entities if e.entity_type == EntityType.GARRISON]
        if not garrisons:
            self.state = KnightState.RESTING
            return
        g = min(garrisons, key=lambda x: dist(self.position, x.position, sim.grid_size))
        self.target_pos   = g.position
        self.current_path = astar(self.position, g.position, set(), sim.grid_size)
        if len(self.current_path) > 1:
            self.position     = self.current_path[1]
            self.current_path = self.current_path[1:]
        else:
            self.state = KnightState.RESTING

    def _challenging(self, sim):
        target_here = any(e is self.target_hunter
                          for e in sim.get_entities_at(self.position))
        if not target_here:
            self.target_hunter = None
            self.state = KnightState.PATROLLING
            return
        h = self.target_hunter
        h.stamina -= (5.0 if random.random() < 0.5 else 20.0) * self._detect_mult
        if h.carried_treasure:
            h.carried_treasure.position = self.position
            sim.add_entity(h.carried_treasure)
            h.carried_treasure = None
        self.challenges += 1
        sim.trigger_event("challenge_hit", h)
        self.target_hunter = None
        self.state = KnightState.PATROLLING

    def _pursuing(self, sim):
        if not self.target_hunter or self.target_hunter not in sim.entities:
            self.target_hunter = None
            self.state = KnightState.PATROLLING
            return
        if self.position == self.target_hunter.position:
            self.state = KnightState.CHALLENGING
            return
        self.current_path = astar(self.position, self.target_hunter.position,
                                  set(), sim.grid_size)
        if len(self.current_path) > 1:
            self.energy  -= KNIGHT_CHASE_ENERGY_COST * self._detect_mult
            self.position = self.current_path[1]
            self.current_path = self.current_path[1:]
        else:
            self.target_hunter = None
            self.state = KnightState.PATROLLING

    def _patrolling(self, sim):
        detected = []
        for e in sim.entities:
            if not isinstance(e, Hunter):
                continue
            d = dist(self.position, e.position, sim.grid_size)
            if d > KNIGHT_DETECTION_RANGE * self._detect_mult:
                continue
            prob = 1.0 if e.skill != HunterSkill.STEALTH else 0.5
            if random.random() < prob:
                detected.append(e)
        if detected:
            self.target_hunter = min(detected,
                                     key=lambda h: dist(self.position, h.position, sim.grid_size))
            self.state = KnightState.PURSUING
            return
        if not self.patrol_path:
            self._gen_patrol()
        if self.patrol_path:
            nxt = self.patrol_path[0]
            self.position   = nxt
            self.patrol_path = self.patrol_path[1:] + [nxt]

    def _gen_patrol(self):
        cx, cy = self.position
        r   = random.randint(2, 5)
        n   = random.randint(4, 8)
        pts = []
        for i in range(n):
            a = 2 * math.pi * i / n
            x = (cx + int(r * math.cos(a))) % GRID_SIZE
            y = (cy + int(r * math.sin(a))) % GRID_SIZE
            pts.append((x, y))
        self.patrol_path = pts


# ---------------------------------------------------------------------------
# Garrison
# ---------------------------------------------------------------------------
class Garrison(Entity):
    def __init__(self, pos):
        super().__init__(EntityType.GARRISON, pos)


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------
class EldoriaSimulation:
    def __init__(self, grid_size: int = GRID_SIZE,
                 difficulty: str = DIFF_NORMAL,
                 num_hunters: int = 0):
        self.grid_size   = grid_size
        self.difficulty  = difficulty
        self.num_hunters_override = num_hunters
        self.entities:   list[Entity] = []
        self.current_step = 0
        self.total_treasure_value    = 0.0
        self.collected_treasure_value = 0.0
        self.events: list[tuple[str, object]] = []   # (event_name, entity)
        self._listeners: dict[str, list] = {
            "collect_treasure": [], "challenge": [], "challenge_hit": [],
            "warning": [], "footsteps": [], "deposit": [], "recruit": [],
        }

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def initialize(self):
        self.entities = []
        self.current_step = 0
        self.total_treasure_value = 0.0
        self.collected_treasure_value = 0.0
        self.events = []

        ds = DIFFICULTY_SETTINGS[self.difficulty]
        g  = self.grid_size

        # Hideouts
        n_hideouts = max(2, g // 10)
        for pos in self._rand_positions(n_hideouts):
            self.add_entity(Hideout(pos))

        # Garrisons + Knights
        n_knights   = max(3, int((g // 7) * ds["knight_scale"]))
        n_garrisons = max(2, n_knights // 2)
        for pos in self._rand_positions(n_garrisons):
            self.add_entity(Garrison(pos))
        for pos in self._rand_positions(n_knights):
            self.add_entity(Knight(pos, self.difficulty))

        # Treasure
        n_bronze = int(g       * ds["treasure_scale"])
        n_silver = int(g // 2  * ds["treasure_scale"])
        n_gold   = int(g // 4  * ds["treasure_scale"])
        for pos in self._rand_positions(n_bronze):
            t = Treasure(EntityType.TREASURE_BRONZE, pos)
            self.add_entity(t)
            self.total_treasure_value += t.value_pct()
        for pos in self._rand_positions(n_silver):
            t = Treasure(EntityType.TREASURE_SILVER, pos)
            self.add_entity(t)
            self.total_treasure_value += t.value_pct()
        for pos in self._rand_positions(n_gold):
            t = Treasure(EntityType.TREASURE_GOLD, pos)
            self.add_entity(t)
            self.total_treasure_value += t.value_pct()

        # Hunters
        hideouts = [e for e in self.entities if isinstance(e, Hideout)]
        for hideout in hideouts:
            count = (self.num_hunters_override // max(1, len(hideouts))
                     if self.num_hunters_override else random.randint(2, 3))
            for _ in range(count):
                skill = random.choice(list(HunterSkill))
                h = Hunter(hideout.position, skill, difficulty=self.difficulty)
                h.known_hideouts.add(hideout.position)
                self.add_entity(h)

    def _rand_positions(self, count: int):
        occupied = {e.position for e in self.entities}
        positions = []
        attempts  = 0
        while len(positions) < count and attempts < count * 20:
            attempts += 1
            p = (random.randint(0, self.grid_size-1),
                 random.randint(0, self.grid_size-1))
            if p not in occupied:
                positions.append(p)
                occupied.add(p)
        return positions

    # ------------------------------------------------------------------
    # Entity management
    # ------------------------------------------------------------------
    def add_entity(self, e: Entity):
        self.entities.append(e)

    def remove_entity(self, e: Entity):
        try:
            self.entities.remove(e)
        except ValueError:
            pass

    def get_entities_at(self, pos) -> list[Entity]:
        return [e for e in self.entities if e.position == pos]

    # ------------------------------------------------------------------
    # Step
    # ------------------------------------------------------------------
    def step(self):
        self.current_step += 1
        self.events = []
        for e in list(self.entities):
            e.update(self)
        self.collected_treasure_value = sum(
            h.total_value for h in self.entities if isinstance(h, Hideout)
        )

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def trigger_event(self, name: str, entity=None):
        self.events.append((name, entity))
        for cb in self._listeners.get(name, []):
            cb()

    def add_listener(self, name: str, cb):
        if name in self._listeners:
            self._listeners[name].append(cb)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def is_complete(self) -> bool:
        treasures = [e for e in self.entities if isinstance(e, Treasure)]
        hunters   = [e for e in self.entities if isinstance(e, Hunter)]
        if not treasures:
            return True
        if not hunters:
            # Check if recruitment is possible
            hideouts = [e for e in self.entities if isinstance(e, Hideout)]
            return not any(h.hunters_inside for h in hideouts)
        return False

    def statistics(self) -> dict:
        hunters  = [e for e in self.entities if isinstance(e, Hunter)]
        treasures = [e for e in self.entities if isinstance(e, Treasure)]
        return {
            "step":     self.current_step,
            "hunters":  len(hunters),
            "treasures": len(treasures),
            "hideouts": len([e for e in self.entities if isinstance(e, Hideout)]),
            "knights":  len([e for e in self.entities if isinstance(e, Knight)]),
            "bronze":   sum(1 for e in treasures if e.entity_type == EntityType.TREASURE_BRONZE),
            "silver":   sum(1 for e in treasures if e.entity_type == EntityType.TREASURE_SILVER),
            "gold":     sum(1 for e in treasures if e.entity_type == EntityType.TREASURE_GOLD),
            "collected": self.collected_treasure_value,
            "total":    self.total_treasure_value,
            "pct": (self.collected_treasure_value / self.total_treasure_value * 100
                    if self.total_treasure_value > 0 else 0),
            "score":    int(self.collected_treasure_value * 10),
        }
