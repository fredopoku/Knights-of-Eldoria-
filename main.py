"""
Knights of Eldoria - AI Simulation
CPS7004 Artificial Intelligence Assessment

This implementation models a medieval kingdom where treasure hunters navigate
through the realm, collecting treasures while avoiding knights. The simulation
uses several AI techniques including:
- Pathfinding with A* algorithm
- State machines for agent behavior
- Knowledge representation and sharing
- Reinforcement learning for strategy optimization
"""

import enum
import math
import os
import random
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Tuple, Set, Optional
import time

# Add these imports for asset handling
try:
    from PIL import Image, ImageTk

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("PIL not available - using colored rectangles instead of images")

try:
    import pygame

    PYGAME_AVAILABLE = True
    pygame.mixer.init()
except (ImportError, pygame.error):
    PYGAME_AVAILABLE = False
    print("Pygame not available - sound will be disabled")


# -----------------------------------------------------------------------------
# ENUMERATIONS AND CONSTANTS
# -----------------------------------------------------------------------------

class EntityType(enum.Enum):
    """Enumeration for different entity types in the simulation."""
    EMPTY = 0
    TREASURE_BRONZE = 1
    TREASURE_SILVER = 2
    TREASURE_GOLD = 3
    HUNTER = 4
    HIDEOUT = 5
    KNIGHT = 6
    GARRISON = 7


class HunterSkill(enum.Enum):
    """Enumeration for different hunter skills."""
    NAVIGATION = 0  # Better pathfinding, can see farther
    ENDURANCE = 1  # Reduced stamina loss, faster recovery
    STEALTH = 2  # Less likely to be detected by knights


class HunterState(enum.Enum):
    """Enumeration for hunter states in the state machine."""
    EXPLORING = 0
    COLLECTING = 1
    RETURNING = 2
    RESTING = 3
    EVADING = 4
    COLLAPSED = 5


class KnightState(enum.Enum):
    """Enumeration for knight states in the state machine."""
    PATROLLING = 0
    PURSUING = 1
    CHALLENGING = 2
    RESTING = 3


# Constants for simulation
GRID_SIZE = 20
WRAP_AROUND = True
VISIBILITY_RANGE = 3
KNIGHT_DETECTION_RANGE = 3
STAMINA_MOVEMENT_COST = 2.0
STAMINA_CRITICAL_LEVEL = 6.0
KNIGHT_CHASE_ENERGY_COST = 20.0
KNIGHT_LOW_ENERGY = 20.0
TREASURE_DECAY_RATE = 0.1


# -----------------------------------------------------------------------------
# ASSET MANAGER
# -----------------------------------------------------------------------------

class AssetManager:
    """Manages game assets including images and sounds."""

    def __init__(self):
        self.images = {}
        self.sounds = {}
        self.initialized = False

    def initialize(self):
        """Load all assets."""
        if self.initialized:
            return

        # Define paths for assets
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')

        # Create assets directory if it doesn't exist
        if not os.path.exists(assets_dir):
            os.makedirs(assets_dir)
            print(f"Created assets directory at: {assets_dir}")

        # Map entity types to image files
        self.image_paths = {
            EntityType.TREASURE_BRONZE: os.path.join(assets_dir, 'bronze.png'),
            EntityType.TREASURE_SILVER: os.path.join(assets_dir, 'silver.png'),
            EntityType.TREASURE_GOLD: os.path.join(assets_dir, 'gold.png'),
            EntityType.HUNTER: os.path.join(assets_dir, 'hunter.png'),
            EntityType.HIDEOUT: os.path.join(assets_dir, 'tree.png'),  # Using tree.png for hideout
            EntityType.KNIGHT: os.path.join(assets_dir, 'knight.png'),
            EntityType.GARRISON: os.path.join(assets_dir, 'garrison.png'),
            'treasure': os.path.join(assets_dir, 'treasure.png')  # Generic treasure image
        }

        # Sound effects
        self.sound_paths = {
            'collect': os.path.join(assets_dir, 'collect.wav'),
            'challenge': os.path.join(assets_dir, 'challenge.wav'),
            'footsteps': os.path.join(assets_dir, 'footsteps.wav'),
            'warning': os.path.join(assets_dir, 'warning.wav')
        }

        # Load images if PIL is available
        if PIL_AVAILABLE:
            for key, path in self.image_paths.items():
                try:
                    if os.path.exists(path):
                        pil_image = Image.open(path)
                        pil_image.load()  # Ensure image is loaded properly
                        self.images[key] = ImageTk.PhotoImage(pil_image)
                    else:
                        print(f"Warning: Image file not found: {path}")
                except Exception as e:
                    print(f"Error loading image {path}: {e}")

        # Load sounds if pygame is available
        if PYGAME_AVAILABLE:
            for key, path in self.sound_paths.items():
                try:
                    if os.path.exists(path):
                        self.sounds[key] = pygame.mixer.Sound(path)
                    else:
                        print(f"Warning: Sound file not found: {path}")
                except Exception as e:
                    print(f"Error loading sound {path}: {e}")

        self.initialized = True

    def resize_images(self, cell_size):
        """Resize all images to fit the cell size."""
        if not PIL_AVAILABLE:
            return

        # Ensure cell_size is valid
        if cell_size <= 0:
            print(f"Invalid cell size: {cell_size}. Using default size of 40.")
            cell_size = 40

        size = (cell_size, cell_size)

        for key, path in self.image_paths.items():
            if os.path.exists(path):
                try:
                    pil_image = Image.open(path)
                    # Ensure image is loaded properly before resizing
                    pil_image.load()
                    resized_image = pil_image.resize(size, Image.LANCZOS)
                    self.images[key] = ImageTk.PhotoImage(resized_image)
                except Exception as e:
                    print(f"Error resizing image {path}: {e}")

    def play_sound(self, sound_key):
        """Play a sound effect."""
        if not PYGAME_AVAILABLE:
            return

        if sound_key in self.sounds:
            try:
                self.sounds[sound_key].play()
            except:
                pass  # Silently fail if sound can't be played

    def create_default_image(self, color, size):
        """Create a default colored image when no actual image is available."""
        if not PIL_AVAILABLE:
            return None

        try:
            # Create a solid color image
            img = Image.new('RGBA', size, color)
            return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Error creating default image: {e}")
            return None


# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def distance(pos1: Tuple[int, int], pos2: Tuple[int, int], wrap: bool = True, grid_size: int = GRID_SIZE) -> float:
    """Calculate the distance between two positions, considering wrap-around if enabled."""
    x1, y1 = pos1
    x2, y2 = pos2

    if not wrap:
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    # Consider wrap-around distances
    dx = min(abs(x2 - x1), grid_size - abs(x2 - x1))
    dy = min(abs(y2 - y1), grid_size - abs(y2 - y1))
    return math.sqrt(dx ** 2 + dy ** 2)


def get_neighbors(pos: Tuple[int, int], grid_size: int = GRID_SIZE) -> List[Tuple[int, int]]:
    """Get all adjacent positions, including diagonals, with wrap-around."""
    x, y = pos
    neighbors = []

    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue

            nx = (x + dx) % grid_size
            ny = (y + dy) % grid_size
            neighbors.append((nx, ny))

    return neighbors


def a_star_pathfinding(start: Tuple[int, int], goal: Tuple[int, int], obstacles: Set[Tuple[int, int]],
                       grid_size: int = GRID_SIZE) -> List[Tuple[int, int]]:
    """A* pathfinding algorithm to find shortest path considering obstacles and wrap-around."""
    if start == goal:
        return [start]

    # Define heuristic function (Manhattan distance with wrap-around)
    def heuristic(pos):
        x1, y1 = pos
        x2, y2 = goal
        dx = min(abs(x2 - x1), grid_size - abs(x2 - x1))
        dy = min(abs(y2 - y1), grid_size - abs(y2 - y1))
        return dx + dy

    # Initialize open and closed sets
    open_set = {start}
    closed_set = set()

    # Initialize costs and parents
    g_score = {start: 0}
    f_score = {start: heuristic(start)}
    parent = {}

    while open_set:
        # Find node with lowest f_score in open_set
        current = min(open_set, key=lambda pos: f_score.get(pos, float('inf')))

        if current == goal:
            # Reconstruct path
            path = [current]
            while current in parent:
                current = parent[current]
                path.append(current)
            return path[::-1]

        open_set.remove(current)
        closed_set.add(current)

        for neighbor in get_neighbors(current, grid_size):
            if neighbor in closed_set or neighbor in obstacles:
                continue

            tentative_g = g_score[current] + 1

            if neighbor not in open_set:
                open_set.add(neighbor)
            elif tentative_g >= g_score.get(neighbor, float('inf')):
                continue

            # This path is the best so far
            parent[neighbor] = current
            g_score[neighbor] = tentative_g
            f_score[neighbor] = g_score[neighbor] + heuristic(neighbor)

    # No path found
    return []


# -----------------------------------------------------------------------------
# ENTITY CLASSES
# -----------------------------------------------------------------------------

class Entity:
    """Base class for all entities in the simulation."""

    def __init__(self, entity_type: EntityType, position: Tuple[int, int]):
        self.entity_type = entity_type
        self.position = position
        self.id = id(self)  # Unique identifier

    def update(self, simulation):
        """Update the entity state based on the current simulation state."""
        pass

    def __eq__(self, other):
        if not isinstance(other, Entity):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)


class Treasure(Entity):
    """Represents treasure items of different values."""

    def __init__(self, treasure_type: EntityType, position: Tuple[int, int]):
        super().__init__(treasure_type, position)
        self.initial_value = self._get_initial_value(treasure_type)
        self.current_value = self.initial_value

    def _get_initial_value(self, treasure_type: EntityType) -> float:
        """Get the initial value based on treasure type."""
        if treasure_type == EntityType.TREASURE_BRONZE:
            return 100.0
        elif treasure_type == EntityType.TREASURE_SILVER:
            return 200.0
        elif treasure_type == EntityType.TREASURE_GOLD:
            return 300.0
        else:
            return 0.0

    def get_value_percentage(self) -> float:
        """Return percentage value that a hunter would gain from this treasure."""
        if self.entity_type == EntityType.TREASURE_BRONZE:
            return 3.0
        elif self.entity_type == EntityType.TREASURE_SILVER:
            return 7.0
        elif self.entity_type == EntityType.TREASURE_GOLD:
            return 13.0
        return 0.0

    def update(self, simulation):
        """Update treasure value, removing it if it decays to zero."""
        self.current_value -= self.initial_value * (TREASURE_DECAY_RATE / 100)
        if self.current_value <= 0:
            simulation.remove_entity(self)


class Hunter(Entity):
    """Represents treasure hunters that collect treasures and avoid knights."""

    def __init__(self, position: Tuple[int, int], skill: HunterSkill):
        super().__init__(EntityType.HUNTER, position)
        self.skill = skill
        self.stamina = 100.0
        self.state = HunterState.EXPLORING
        self.carried_treasure: Optional[Treasure] = None
        self.wealth = 0.0
        self.collapsed_counter = 0

        # Memory of discovered locations
        self.known_treasures: Dict[Tuple[int, int], EntityType] = {}
        self.known_hideouts: Set[Tuple[int, int]] = set()
        self.known_knights: Dict[Tuple[int, int], int] = {}  # Position to last seen time

        # Pathfinding
        self.current_path: List[Tuple[int, int]] = []
        self.target_position: Optional[Tuple[int, int]] = None

    def update(self, simulation):
        """Update hunter state based on current simulation state."""
        # Update known entities based on visibility
        self._update_knowledge(simulation)

        # State machine for hunter behavior
        if self.state == HunterState.COLLAPSED:
            self._handle_collapsed_state(simulation)
        elif self.stamina <= 0:
            self.state = HunterState.COLLAPSED
            self.collapsed_counter = 3  # Will survive for 3 more steps
        elif self.state == HunterState.RESTING:
            self._handle_resting_state(simulation)
        elif self.stamina <= STAMINA_CRITICAL_LEVEL:
            # Critical stamina - try to find hideout to rest
            self._seek_hideout(simulation)
        elif self.state == HunterState.EVADING:
            self._handle_evading_state(simulation)
        elif self.state == HunterState.RETURNING:
            self._handle_returning_state(simulation)
        elif self.state == HunterState.COLLECTING:
            self._handle_collecting_state(simulation)
        elif self.state == HunterState.EXPLORING:
            self._handle_exploring_state(simulation)

    def _update_knowledge(self, simulation):
        """Update the hunter's knowledge of the environment based on visibility."""
        # Get visible area
        visibility_range = VISIBILITY_RANGE
        if self.skill == HunterSkill.NAVIGATION:
            visibility_range += 1  # Navigation skill increases visibility

        for dx in range(-visibility_range, visibility_range + 1):
            for dy in range(-visibility_range, visibility_range + 1):
                if dx ** 2 + dy ** 2 > visibility_range ** 2:
                    continue  # Outside circular visibility range

                # Calculate position with wrap-around
                x = (self.position[0] + dx) % GRID_SIZE
                y = (self.position[1] + dy) % GRID_SIZE
                pos = (x, y)

                # Check what's at this position
                entities = simulation.get_entities_at(pos)
                for entity in entities:
                    if isinstance(entity, Treasure):
                        self.known_treasures[pos] = entity.entity_type
                    elif isinstance(entity, Hideout):
                        self.known_hideouts.add(pos)
                    elif isinstance(entity, Knight):
                        self.known_knights[pos] = simulation.current_step

        # Clean up knowledge of treasures that are no longer there
        treasures_to_remove = []
        for pos in self.known_treasures:
            found = False
            for entity in simulation.get_entities_at(pos):
                if isinstance(entity, Treasure):
                    found = True
                    break
            if not found:
                treasures_to_remove.append(pos)

        for pos in treasures_to_remove:
            del self.known_treasures[pos]

    def _handle_collapsed_state(self, simulation):
        """Handle behavior when hunter has collapsed."""
        self.collapsed_counter -= 1
        if self.collapsed_counter <= 0:
            simulation.remove_entity(self)
            # Drop treasure if carrying any
            if self.carried_treasure:
                self.carried_treasure.position = self.position
                simulation.add_entity(self.carried_treasure)
                self.carried_treasure = None

    def _handle_resting_state(self, simulation):
        """Handle behavior when hunter is resting in a hideout."""
        # Recover stamina
        self.stamina += 1.0
        if self.skill == HunterSkill.ENDURANCE:
            self.stamina += 0.5  # Endurance skill gives faster recovery

        # Cap stamina at 100
        self.stamina = min(self.stamina, 100.0)

        # Check if there's a hideout at current position
        hideout = None
        for entity in simulation.get_entities_at(self.position):
            if isinstance(entity, Hideout):
                hideout = entity
                break

        if not hideout:
            # No longer in a hideout, return to exploring
            self.state = HunterState.EXPLORING
            return

        # Deposit treasure if carrying any
        if self.carried_treasure:
            value_increase = self.carried_treasure.get_value_percentage()
            self.wealth += value_increase
            hideout.store_treasure(self.carried_treasure)
            self.carried_treasure = None

        # Share knowledge with other hunters in hideout
        for entity in simulation.get_entities_at(self.position):
            if isinstance(entity, Hunter) and entity != self:
                # Share known treasures
                for pos, treasure_type in self.known_treasures.items():
                    entity.known_treasures[pos] = treasure_type

                # Share known hideouts
                entity.known_hideouts.update(self.known_hideouts)

                # Share known knight positions
                for pos, last_seen in self.known_knights.items():
                    if pos not in entity.known_knights or last_seen > entity.known_knights[pos]:
                        entity.known_knights[pos] = last_seen

        # If fully recovered, go back to exploring
        if self.stamina >= 90.0:
            self.state = HunterState.EXPLORING

    def _seek_hideout(self, simulation):
        """Try to find and move to a hideout for resting."""
        if not self.known_hideouts:
            # No hideouts known, continue exploration but conserve energy
            self._handle_exploring_state(simulation, conservative=True)
            return

        # Find closest hideout
        closest_hideout = min(self.known_hideouts,
                              key=lambda pos: distance(self.position, pos))

        # Set target and path
        self.target_position = closest_hideout
        obstacles = self._get_obstacle_positions(simulation)
        self.current_path = a_star_pathfinding(self.position, closest_hideout, obstacles)

        # Move along path
        if len(self.current_path) > 1:
            self._move_along_path(simulation)
        else:
            # Already at a hideout, start resting
            self.state = HunterState.RESTING

    def _handle_evading_state(self, simulation):
        """Handle behavior when hunter is evading knights."""
        # Check if still need to evade
        knight_nearby = False
        for entity in simulation.entities:
            if isinstance(entity, Knight) and distance(self.position, entity.position) <= KNIGHT_DETECTION_RANGE:
                knight_nearby = True
                break

        if not knight_nearby:
            # No knights nearby, resume previous activity
            if self.carried_treasure:
                self.state = HunterState.RETURNING
            else:
                self.state = HunterState.EXPLORING
            return

        # Try to find safe direction away from knights
        safe_directions = []
        for neighbor in get_neighbors(self.position):
            safe = True
            for entity in simulation.entities:
                if isinstance(entity, Knight) and distance(neighbor, entity.position) <= KNIGHT_DETECTION_RANGE - 1:
                    safe = False
                    break
            if safe:
                safe_directions.append(neighbor)

        if safe_directions:
            # Move to random safe direction
            next_pos = random.choice(safe_directions)

            # If carrying treasure we might drop it to escape faster
            if self.carried_treasure and random.random() < 0.3:
                self.carried_treasure.position = self.position
                simulation.add_entity(self.carried_treasure)
                self.carried_treasure = None

            # Move and consume stamina
            self.position = next_pos
            stamina_cost = STAMINA_MOVEMENT_COST
            if self.skill == HunterSkill.ENDURANCE:
                stamina_cost *= 0.8  # Endurance reduces stamina cost
            self.stamina -= stamina_cost
        else:
            # No safe direction, move randomly
            next_pos = random.choice(get_neighbors(self.position))
            self.position = next_pos
            stamina_cost = STAMINA_MOVEMENT_COST
            if self.skill == HunterSkill.ENDURANCE:
                stamina_cost *= 0.8
            self.stamina -= stamina_cost

    def _handle_returning_state(self, simulation):
        """Handle behavior when hunter is returning to a hideout with treasure."""
        if not self.carried_treasure:
            # No treasure to return, go back to exploring
            self.state = HunterState.EXPLORING
            return

        # Check for knight threats
        for entity in simulation.entities:
            if isinstance(entity, Knight) and distance(self.position, entity.position) <= KNIGHT_DETECTION_RANGE:
                self.state = HunterState.EVADING
                return

        if not self.known_hideouts:
            # No hideouts known, explore to find one
            self._handle_exploring_state(simulation)
            return

        # Find closest hideout
        closest_hideout = min(self.known_hideouts,
                              key=lambda pos: distance(self.position, pos))

        # Set target and path if needed
        if self.target_position != closest_hideout:
            self.target_position = closest_hideout
            obstacles = self._get_obstacle_positions(simulation)
            self.current_path = a_star_pathfinding(self.position, closest_hideout, obstacles)

        # Move along path
        if len(self.current_path) > 1:
            self._move_along_path(simulation)
        else:
            # Reached hideout, deposit treasure and rest
            self.state = HunterState.RESTING

    def _handle_collecting_state(self, simulation):
        """Handle behavior when hunter is moving to collect treasure."""
        # Already carrying treasure
        if self.carried_treasure:
            self.state = HunterState.RETURNING
            return

        # Check for knight threats
        for entity in simulation.entities:
            if isinstance(entity, Knight) and distance(self.position, entity.position) <= KNIGHT_DETECTION_RANGE:
                self.state = HunterState.EVADING
                return

        # No target or invalid target
        if not self.target_position or self.target_position not in self.known_treasures:
            self.state = HunterState.EXPLORING
            return

        # Move along path to treasure
        if len(self.current_path) > 1:
            self._move_along_path(simulation)
        else:
            # At target position, try to collect treasure
            treasures = [e for e in simulation.get_entities_at(self.position)
                         if isinstance(e, Treasure)]

            if treasures:
                # If multiple treasures, prioritize by value
                treasure = max(treasures, key=lambda t: t.get_value_percentage())
                self.carried_treasure = treasure
                simulation.remove_entity(treasure)
                simulation.trigger_event('collect_treasure')
                self.state = HunterState.RETURNING
            else:
                # No treasure here (maybe already collected)
                if self.position in self.known_treasures:
                    del self.known_treasures[self.position]
                self.state = HunterState.EXPLORING

    def _handle_exploring_state(self, simulation, conservative=False):
        """Handle behavior when hunter is exploring the environment."""
        # Check for treasures within visibility range
        visible_treasures = list(self.known_treasures.items())

        # Check for knight threats
        for entity in simulation.entities:
            if isinstance(entity, Knight) and distance(self.position, entity.position) <= KNIGHT_DETECTION_RANGE:
                self.state = HunterState.EVADING
                return

        # If carrying treasure, switch to returning
        if self.carried_treasure:
            self.state = HunterState.RETURNING
            return

        # If we know about treasures, go collect one
        if visible_treasures:
            # Prioritize by value and distance
            def treasure_priority(item):
                pos, type_val = item
                if type_val == EntityType.TREASURE_GOLD:
                    value = 3
                elif type_val == EntityType.TREASURE_SILVER:
                    value = 2
                else:
                    value = 1
                return value / (distance(self.position, pos) + 1)

            best_treasure = max(visible_treasures, key=treasure_priority)
            self.target_position = best_treasure[0]

            obstacles = self._get_obstacle_positions(simulation)
            self.current_path = a_star_pathfinding(self.position, self.target_position, obstacles)

            # Switch to collecting state
            self.state = HunterState.COLLECTING
            return

        # Continue exploration
        if conservative or not self.current_path:
            # Generate a new exploration path
            self._generate_exploration_path(simulation)

        # Move along the current path
        if self.current_path:
            self._move_along_path(simulation)

    def _generate_exploration_path(self, simulation):
        """Generate a new path for exploration."""
        # Identify unexplored areas
        unexplored = []
        explored = set(self.known_treasures.keys()) | self.known_hideouts

        for x in range(GRID_SIZE):
            for y in range(GRID_SIZE):
                pos = (x, y)
                if pos not in explored:
                    unexplored.append(pos)

        if not unexplored:
            # Everything is explored, pick a random direction
            target = (random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1))
        else:
            # Choose nearest unexplored position
            target = min(unexplored, key=lambda pos: distance(self.position, pos))

        # Generate path to target
        obstacles = self._get_obstacle_positions(simulation)
        self.current_path = a_star_pathfinding(self.position, target, obstacles)
        self.target_position = target

    def _get_obstacle_positions(self, simulation) -> Set[Tuple[int, int]]:
        """Get positions of obstacles that should be avoided in pathfinding."""
        obstacles = set()

        # Avoid known knights with a buffer zone
        for knight_pos in self.known_knights:
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    x = (knight_pos[0] + dx) % GRID_SIZE
                    y = (knight_pos[1] + dy) % GRID_SIZE
                    obstacles.add((x, y))

        return obstacles

    def _move_along_path(self, simulation):
        """Move along the current path, consuming stamina."""
        if not self.current_path or len(self.current_path) <= 1:
            return

        # Move to next position in path
        next_pos = self.current_path[1]
        self.position = next_pos

        # Update path
        self.current_path = self.current_path[1:]

        # Consume stamina
        stamina_cost = STAMINA_MOVEMENT_COST
        if self.skill == HunterSkill.ENDURANCE:
            stamina_cost *= 0.8  # Endurance reduces stamina cost
        self.stamina -= stamina_cost

        # Random chance to play footstep sound
        if random.random() < 0.05:
            simulation.trigger_event('footsteps')


class Hideout(Entity):
    """Represents hideouts where hunters can rest and store treasures."""

    def __init__(self, position: Tuple[int, int]):
        super().__init__(EntityType.HIDEOUT, position)
        self.treasure_count = 0
        self.total_value = 0.0
        self.hunters_inside: List[Hunter] = []
        self.hunter_skills: Dict[HunterSkill, int] = {
            HunterSkill.NAVIGATION: 0,
            HunterSkill.ENDURANCE: 0,
            HunterSkill.STEALTH: 0
        }

    def update(self, simulation):
        """Update hideout state and possibly recruit new hunters."""
        # Update list of hunters inside
        self.hunters_inside = []
        self.hunter_skills = {skill: 0 for skill in HunterSkill}

        for entity in simulation.get_entities_at(self.position):
            if isinstance(entity, Hunter):
                self.hunters_inside.append(entity)
                self.hunter_skills[entity.skill] += 1

        # Potentially recruit new hunter if diverse skillset and space
        if 0 < len(self.hunters_inside) < 5 and min(self.hunter_skills.values()) > 0:
            if random.random() < 0.2:  # 20% chance
                self._recruit_new_hunter(simulation)

    def store_treasure(self, treasure: Treasure):
        """Store a treasure in the hideout."""
        self.treasure_count += 1
        self.total_value += treasure.get_value_percentage()

    def _recruit_new_hunter(self, simulation):
        """Recruit a new hunter with a skill from the existing group."""
        # Select a skill with equal probability
        available_skills = list(HunterSkill)
        skill = random.choice(available_skills)

        # Place new hunter at the hideout
        new_hunter = Hunter(self.position, skill)

        # Share knowledge with the new hunter
        for existing_hunter in self.hunters_inside:
            # Share known treasures
            for pos, treasure_type in existing_hunter.known_treasures.items():
                new_hunter.known_treasures[pos] = treasure_type

            # Share known hideouts
            new_hunter.known_hideouts.update(existing_hunter.known_hideouts)

            # Share known knight positions
            for pos, last_seen in existing_hunter.known_knights.items():
                if pos not in new_hunter.known_knights or last_seen > new_hunter.known_knights[pos]:
                    new_hunter.known_knights[pos] = last_seen

        # Add the new hunter to the simulation
        simulation.add_entity(new_hunter)


class Knight(Entity):
    """Represents knights that patrol and chase hunters."""

    def __init__(self, position: Tuple[int, int]):
        super().__init__(EntityType.KNIGHT, position)
        self.energy = 100.0
        self.state = KnightState.PATROLLING
        self.target_hunter: Optional[Hunter] = None
        self.patrol_path: List[Tuple[int, int]] = []
        self.current_path: List[Tuple[int, int]] = []
        self.target_position: Optional[Tuple[int, int]] = None

    def update(self, simulation):
        """Update knight state based on current simulation state."""
        # Store previous state to detect transitions for sound effects
        previous_state = self.state

        # State machine for knight behavior
        if self.state == KnightState.RESTING:
            self._handle_resting_state(simulation)
        elif self.energy <= KNIGHT_LOW_ENERGY:
            # Low energy - seek garrison to rest
            self._seek_garrison(simulation)
        elif self.state == KnightState.CHALLENGING:
            self._handle_challenging_state(simulation)
        elif self.state == KnightState.PURSUING:
            self._handle_pursuing_state(simulation)
        elif self.state == KnightState.PATROLLING:
            self._handle_patrolling_state(simulation)

        # Check for state transitions to trigger sound effects
        if previous_state != self.state:
            if self.state == KnightState.PURSUING:
                simulation.trigger_event('warning')
            elif self.state == KnightState.CHALLENGING:
                simulation.trigger_event('challenge')

    def _handle_resting_state(self, simulation):
        """Handle behavior when knight is resting at a garrison."""
        # Recover energy
        self.energy += 10.0

        # Cap energy at 100
        self.energy = min(self.energy, 100.0)

        # If fully recovered, go back to patrolling
        if self.energy >= 100.0:
            self.state = KnightState.PATROLLING
            # Generate new patrol path
            self._generate_patrol_path()

    def _seek_garrison(self, simulation):
        """Find and move towards the nearest garrison to rest."""
        # Find nearest garrison
        garrisons = [e for e in simulation.entities if e.entity_type == EntityType.GARRISON]

        if not garrisons:
            # No garrisons available, just rest in place
            self.state = KnightState.RESTING
            return

        closest_garrison = min(garrisons, key=lambda g: distance(self.position, g.position))

        # Set target and path
        self.target_position = closest_garrison.position
        self.current_path = a_star_pathfinding(self.position, closest_garrison.position, set())

        # Move along path
        if len(self.current_path) > 1:
            self._move_along_path()
        else:
            # Already at a garrison, start resting
            self.state = KnightState.RESTING

    def _handle_challenging_state(self, simulation):
        """Handle behavior when knight is challenging a hunter."""
        # Check if target hunter is still present
        target_present = False
        for entity in simulation.get_entities_at(self.position):
            if isinstance(entity, Hunter) and entity == self.target_hunter:
                target_present = True
                break

        if not target_present:
            # Target hunter no longer here, go back to patrolling
            self.target_hunter = None
            self.state = KnightState.PATROLLING
            return

        # Challenge the hunter (always succeeds)
        if random.random() < 0.5:
            # Detain (lighter penalty)
            self.target_hunter.stamina -= 5.0
        else:
            # Challenge (heavier penalty)
            self.target_hunter.stamina -= 20.0

        # Hunter drops treasure
        if self.target_hunter.carried_treasure:
            self.target_hunter.carried_treasure.position = self.position
            simulation.add_entity(self.target_hunter.carried_treasure)
            self.target_hunter.carried_treasure = None

        # Go back to patrolling
        self.target_hunter = None
        self.state = KnightState.PATROLLING

    def _handle_pursuing_state(self, simulation):
        """Handle behavior when knight is pursuing a hunter."""
        # Check if target hunter is still valid
        if not self.target_hunter or self.target_hunter not in simulation.entities:
            self.target_hunter = None
            self.state = KnightState.PATROLLING
            return

        # Check if already caught the hunter
        if self.position == self.target_hunter.position:
            self.state = KnightState.CHALLENGING
            return

        # Calculate path to hunter
        self.target_position = self.target_hunter.position
        self.current_path = a_star_pathfinding(self.position, self.target_position, set())

        # Move along path
        if len(self.current_path) > 1:
            # Pursuit costs energy
            self.energy -= KNIGHT_CHASE_ENERGY_COST
            self._move_along_path()
        else:
            # Can't reach hunter, go back to patrolling
            self.target_hunter = None
            self.state = KnightState.PATROLLING

    def _handle_patrolling_state(self, simulation):
        """Handle behavior when knight is patrolling."""
        # Detect hunters within detection range
        detected_hunters = []
        for entity in simulation.entities:
            if isinstance(entity, Hunter):
                hunter = entity

                # Calculate detection chance based on distance and stealth
                detect_range = KNIGHT_DETECTION_RANGE
                dist = distance(self.position, hunter.position)

                # Skip if out of range
                if dist > detect_range:
                    continue

                # Stealth reduces detection probability
                detection_prob = 1.0
                if hunter.skill == HunterSkill.STEALTH:
                    detection_prob = 0.6  # 40% chance of avoiding detection

                if random.random() < detection_prob:
                    detected_hunters.append(hunter)

        if detected_hunters:
            # Select target (nearest hunter)
            self.target_hunter = min(detected_hunters,
                                     key=lambda h: distance(self.position, h.position))
            self.state = KnightState.PURSUING
            return

        # Continue patrolling
        if not self.patrol_path:
            self._generate_patrol_path()

        # Move along patrol path
        if self.patrol_path:
            next_pos = self.patrol_path[0]
            self.position = next_pos
            self.patrol_path = self.patrol_path[1:] + [next_pos]  # Cycle patrol points

    def _generate_patrol_path(self):
        """Generate a patrol path around the current position."""
        patrol_points = []
        center_x, center_y = self.position

        # Create a circular patrol route
        radius = random.randint(2, 4)
        num_points = random.randint(4, 8)

        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            x = (center_x + int(radius * math.cos(angle))) % GRID_SIZE
            y = (center_y + int(radius * math.sin(angle))) % GRID_SIZE
            patrol_points.append((x, y))

        self.patrol_path = patrol_points

    def _move_along_path(self):
        """Move along the current path."""
        if not self.current_path or len(self.current_path) <= 1:
            return

        # Move to next position in path
        next_pos = self.current_path[1]
        self.position = next_pos

        # Update path
        self.current_path = self.current_path[1:]


class Garrison(Entity):
    """Represents knight garrisons where knights rest and recover energy."""

    def __init__(self, position: Tuple[int, int]):
        super().__init__(EntityType.GARRISON, position)

    def update(self, simulation):
        """Update garrison state."""
        # Garrisons don't have any active behavior
        pass


# -----------------------------------------------------------------------------
# SIMULATION CLASS
# -----------------------------------------------------------------------------
class EldoriaSimulation:
    """Main simulation class that manages the simulation state and logic."""

    def __init__(self, grid_size: int = GRID_SIZE):
        self.grid_size = grid_size
        self.entities: List[Entity] = []
        self.current_step = 0
        self.total_treasure_value = 0.0
        self.collected_treasure_value = 0.0

        # Event system
        self.event_listeners = {
            'collect_treasure': [],
            'challenge': [],
            'warning': [],
            'footsteps': []
        }

    def initialize(self):
        """Initialize the simulation with entities."""
        # Create empty grid
        self.entities = []

        # Add hideouts
        num_hideouts = max(2, self.grid_size // 10)
        hideout_positions = self._generate_random_positions(num_hideouts)

        for pos in hideout_positions:
            self.add_entity(Hideout(pos))

        # Add knights and garrisons
        num_knights = max(3, self.grid_size // 7)
        num_garrisons = max(2, num_knights // 2)

        knight_positions = self._generate_random_positions(num_knights)
        garrison_positions = self._generate_random_positions(num_garrisons)

        for pos in knight_positions:
            self.add_entity(Knight(pos))

        for pos in garrison_positions:
            self.add_entity(Garrison(pos))

        # Add treasure (more abundant)
        num_bronze = self.grid_size
        num_silver = self.grid_size // 2
        num_gold = self.grid_size // 4

        bronze_positions = self._generate_random_positions(num_bronze)
        silver_positions = self._generate_random_positions(num_silver)
        gold_positions = self._generate_random_positions(num_gold)

        for pos in bronze_positions:
            treasure = Treasure(EntityType.TREASURE_BRONZE, pos)
            self.add_entity(treasure)
            self.total_treasure_value += treasure.get_value_percentage()

        for pos in silver_positions:
            treasure = Treasure(EntityType.TREASURE_SILVER, pos)
            self.add_entity(treasure)
            self.total_treasure_value += treasure.get_value_percentage()

        for pos in gold_positions:
            treasure = Treasure(EntityType.TREASURE_GOLD, pos)
            self.add_entity(treasure)
            self.total_treasure_value += treasure.get_value_percentage()

        # Add initial hunters in hideouts
        hideouts = [e for e in self.entities if isinstance(e, Hideout)]

        for hideout in hideouts:
            # 2-3 hunters per hideout
            num_hunters = random.randint(2, 3)
            for _ in range(num_hunters):
                skill = random.choice(list(HunterSkill))
                hunter = Hunter(hideout.position, skill)
                hunter.known_hideouts.add(hideout.position)
                self.add_entity(hunter)

    def _generate_random_positions(self, count: int) -> List[Tuple[int, int]]:
        """Generate random unique positions on the grid."""
        positions = []
        occupied = set(e.position for e in self.entities)

        attempts = 0
        while len(positions) < count and attempts < count * 10:
            attempts += 1
            x = random.randint(0, self.grid_size - 1)
            y = random.randint(0, self.grid_size - 1)
            pos = (x, y)

            if pos not in occupied:
                positions.append(pos)
                occupied.add(pos)

        return positions

    def add_entity(self, entity: Entity):
        """Add an entity to the simulation."""
        self.entities.append(entity)

    def remove_entity(self, entity: Entity):
        """Remove an entity from the simulation."""
        if entity in self.entities:
            self.entities.remove(entity)

    def get_entities_at(self, position: Tuple[int, int]) -> List[Entity]:
        """Get all entities at a specific position."""
        return [e for e in self.entities if e.position == position]

    def step(self):
        """Advance the simulation by one step."""
        self.current_step += 1

        # Update all entities
        for entity in list(self.entities):  # Create a copy to avoid modification issues
            entity.update(self)

        # Calculate treasure collection stats
        hideout_treasure_value = sum(h.total_value for h in self.entities if isinstance(h, Hideout))
        self.collected_treasure_value = hideout_treasure_value

    def is_simulation_complete(self) -> bool:
        """Check if the simulation should stop."""
        # Check if all treasures are collected
        treasures = [e for e in self.entities if isinstance(e, Treasure)]
        hunters = [e for e in self.entities if isinstance(e, Hunter)]
        hideouts = [e for e in self.entities if isinstance(e, Hideout)]

        # Stop if no more treasures or hunters
        if not treasures:
            return True

        if not hunters:
            # Check if new hunters can be recruited
            can_recruit = False
            for hideout in hideouts:
                if len(hideout.hunters_inside) < 5 and hideout.hunters_inside:
                    can_recruit = True
                    break

            if not can_recruit:
                return True

        return False

    def get_statistics(self) -> Dict:
        """Get statistics about the current simulation state."""
        hunters = [e for e in self.entities if isinstance(e, Hunter)]
        treasures = [e for e in self.entities if isinstance(e, Treasure)]
        hideouts = [e for e in self.entities if isinstance(e, Hideout)]
        knights = [e for e in self.entities if isinstance(e, Knight)]

        return {
            "step": self.current_step,
            "hunters": len(hunters),
            "treasures": len(treasures),
            "hideouts": len(hideouts),
            "knights": len(knights),
            "collected_value": self.collected_treasure_value,
            "total_value": self.total_treasure_value,
            "collection_percentage": (self.collected_treasure_value / self.total_treasure_value * 100)
            if self.total_treasure_value > 0 else 0,
        }

    def add_event_listener(self, event_type, callback):
        """Add an event listener for a specific event type."""
        if event_type in self.event_listeners:
            self.event_listeners[event_type].append(callback)

    def trigger_event(self, event_type):
        """Trigger an event and notify all listeners."""
        if event_type in self.event_listeners:
            for callback in self.event_listeners[event_type]:
                callback()


# -----------------------------------------------------------------------------
# VISUALIZATION
# -----------------------------------------------------------------------------
class EldoriaVisualization:
    """Visualization for the Eldoria simulation using Tkinter."""

    def __init__(self, simulation: EldoriaSimulation):
        self.simulation = simulation
        self.root = tk.Tk()
        self.root.title("Knights of Eldoria Simulation")
        self.root.resizable(True, True)

        # Load assets
        self.asset_manager = AssetManager()
        self.asset_manager.initialize()

        # Register for simulation events
        self.simulation.add_event_listener('collect_treasure', lambda: self._play_sound('collect'))
        self.simulation.add_event_listener('challenge', lambda: self._play_sound('challenge'))
        self.simulation.add_event_listener('warning', lambda: self._play_sound('warning'))
        self.simulation.add_event_listener('footsteps', lambda: self._play_sound('footsteps'))

        # Configure styles
        self.configure_styles()

        # Create frames
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.control_frame = ttk.Frame(self.main_frame, padding=5)
        self.control_frame.pack(side=tk.TOP, fill=tk.X)

        self.grid_frame = ttk.Frame(self.main_frame, padding=5)
        self.grid_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.stats_frame = ttk.Frame(self.main_frame, padding=5)
        self.stats_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # Control elements
        self.create_controls()

        # Statistics display
        self.create_stats_display()

        # Add sound toggle
        self.sound_enabled = tk.BooleanVar(value=True)
        sound_check = ttk.Checkbutton(self.control_frame, text="Sound", variable=self.sound_enabled)
        sound_check.pack(side=tk.LEFT, padx=10)

        # Grid display
        self.cell_size = 40  # Larger cells for images
        self.canvas = tk.Canvas(self.grid_frame, bg="forest green")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Initialize grid view
        self.grid_cells = {}
        self.grid_images = {}
        self.create_grid()

        # Animation control
        self.is_running = False
        self.animation_speed = 200  # milliseconds between steps

        # Bind resize event
        self.canvas.bind('<Configure>', self._on_resize)

    def _play_sound(self, sound_key):
        """Play a sound if sound is enabled."""
        if self.sound_enabled.get():
            self.asset_manager.play_sound(sound_key)

    def _on_resize(self, event):
        """Handle canvas resize event."""
        # Recalculate cell size if window is resized
        if event.width > 0 and event.height > 0:
            grid_size = self.simulation.grid_size
            new_cell_size = min(event.width // grid_size, event.height // grid_size)

            if new_cell_size > 0 and new_cell_size != self.cell_size:
                self.cell_size = new_cell_size
                self.create_grid()

    def configure_styles(self):
        """Configure ttk styles for the UI."""
        style = ttk.Style()
        style.configure("TButton", padding=5)
        style.configure("TLabel", padding=2)
        style.configure("Stats.TLabel", padding=2, font=("Arial", 10))
        style.configure("Header.TLabel", padding=2, font=("Arial", 11, "bold"))

    def create_controls(self):
        """Create control buttons and settings."""
        # Grid size selection
        size_frame = ttk.Frame(self.control_frame)
        size_frame.pack(side=tk.LEFT, padx=5)

        ttk.Label(size_frame, text="Grid Size:").pack(side=tk.LEFT)

        self.grid_size_var = tk.StringVar(value=str(GRID_SIZE))
        size_options = ttk.Combobox(size_frame, textvariable=self.grid_size_var,
                                    values=["20", "30", "40", "50"], width=5)
        size_options.pack(side=tk.LEFT, padx=5)

        # Animation speed
        speed_frame = ttk.Frame(self.control_frame)
        speed_frame.pack(side=tk.LEFT, padx=10)

        ttk.Label(speed_frame, text="Speed:").pack(side=tk.LEFT)

        self.speed_var = tk.IntVar(value=5)
        speed_scale = ttk.Scale(speed_frame, from_=1, to=10, orient=tk.HORIZONTAL,
                                variable=self.speed_var, length=100)
        speed_scale.pack(side=tk.LEFT, padx=5)

        # Control buttons
        btn_frame = ttk.Frame(self.control_frame)
        btn_frame.pack(side=tk.RIGHT)

        self.init_btn = ttk.Button(btn_frame, text="Initialize", command=self.initialize_simulation)
        self.init_btn.pack(side=tk.LEFT, padx=5)

        self.step_btn = ttk.Button(btn_frame, text="Step", command=self.step_simulation)
        self.step_btn.pack(side=tk.LEFT, padx=5)

        self.run_btn = ttk.Button(btn_frame, text="Run", command=self.toggle_run)
        self.run_btn.pack(side=tk.LEFT, padx=5)

    def create_stats_display(self):
        """Create display for simulation statistics."""
        ttk.Label(self.stats_frame, text="Simulation Statistics", style="Header.TLabel").pack(anchor=tk.W, pady=5)

        self.step_label = ttk.Label(self.stats_frame, text="Step: 0", style="Stats.TLabel")
        self.step_label.pack(anchor=tk.W, pady=2)

        self.hunters_label = ttk.Label(self.stats_frame, text="Hunters: 0", style="Stats.TLabel")
        self.hunters_label.pack(anchor=tk.W, pady=2)

        self.treasures_label = ttk.Label(self.stats_frame, text="Treasures: 0", style="Stats.TLabel")
        self.treasures_label.pack(anchor=tk.W, pady=2)

        self.collected_label = ttk.Label(self.stats_frame, text="Collected: 0%", style="Stats.TLabel")
        self.collected_label.pack(anchor=tk.W, pady=2)

        # Add separator
        ttk.Separator(self.stats_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Entity counts
        ttk.Label(self.stats_frame, text="Entity Distribution", style="Header.TLabel").pack(anchor=tk.W, pady=5)

        self.bronze_label = ttk.Label(self.stats_frame, text="Bronze Treasures: 0", style="Stats.TLabel")
        self.bronze_label.pack(anchor=tk.W, pady=2)

        self.silver_label = ttk.Label(self.stats_frame, text="Silver Treasures: 0", style="Stats.TLabel")
        self.silver_label.pack(anchor=tk.W, pady=2)

        self.gold_label = ttk.Label(self.stats_frame, text="Gold Treasures: 0", style="Stats.TLabel")
        self.gold_label.pack(anchor=tk.W, pady=2)

        self.hideouts_label = ttk.Label(self.stats_frame, text="Hideouts: 0", style="Stats.TLabel")
        self.hideouts_label.pack(anchor=tk.W, pady=2)

        self.knights_label = ttk.Label(self.stats_frame, text="Knights: 0", style="Stats.TLabel")
        self.knights_label.pack(anchor=tk.W, pady=2)

        # Log area
        ttk.Label(self.stats_frame, text="Event Log", style="Header.TLabel").pack(anchor=tk.W, pady=5)

        self.log_text = tk.Text(self.stats_frame, height=10, width=30, wrap=tk.WORD)
        self.log_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

    def create_grid(self):
        """Create the grid visualization."""
        self.canvas.delete("all")
        self.grid_cells = {}
        self.grid_images = {}  # Add this line to track image objects

        # Calculate cell size based on window size
        window_width = self.grid_frame.winfo_width()
        window_height = self.grid_frame.winfo_height()

        # Use default values if window size is not initialized yet
        if window_width <= 1:
            window_width = 800
        if window_height <= 1:
            window_height = 600

        grid_size = self.simulation.grid_size
        self.cell_size = min(window_width // grid_size, window_height // grid_size)

        # Ensure we have a valid cell size
        if self.cell_size <= 0:
            self.cell_size = 40

        # Resize assets to fit cells
        self.asset_manager.resize_images(self.cell_size)

        # Create grid cells
        for y in range(grid_size):
            for x in range(grid_size):
                x1 = x * self.cell_size
                y1 = y * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size

                self.grid_cells[(x, y)] = self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill="forest green", outline="darkgreen"
                )

        # Update canvas size
        canvas_width = grid_size * self.cell_size
        canvas_height = grid_size * self.cell_size
        self.canvas.config(width=canvas_width, height=canvas_height)

        # Update entity visualization
        self.update_visualization()

    def update_visualization(self):
        """Update the visualization based on current simulation state."""
        # Clear previous entity images
        for img_id in list(self.grid_images.values()):
            self.canvas.delete(img_id)
        self.grid_images = {}

        # Reset all cells to "forest green" background
        for pos, cell_id in self.grid_cells.items():
            self.canvas.itemconfig(cell_id, fill="forest green")

        # Process entities in order (treasures first, then hideouts, then hunters, then knights)
        # This ensures proper layering/visibility

        # First draw treasures
        for entity in [e for e in self.simulation.entities if isinstance(e, Treasure)]:
            x, y = entity.position
            x1 = x * self.cell_size
            y1 = y * self.cell_size

            image_key = None
            if entity.entity_type == EntityType.TREASURE_BRONZE:
                image_key = EntityType.TREASURE_BRONZE
            elif entity.entity_type == EntityType.TREASURE_SILVER:
                image_key = EntityType.TREASURE_SILVER
            elif entity.entity_type == EntityType.TREASURE_GOLD:
                image_key = EntityType.TREASURE_GOLD

            # Try to use image
            if image_key in self.asset_manager.images:
                img_id = self.canvas.create_image(
                    x1, y1,
                    image=self.asset_manager.images[image_key],
                    anchor=tk.NW
                )
                self.grid_images[(x, y, entity.id)] = img_id
            else:
                # Fallback to colored rectangle
                cell_id = self.grid_cells.get((x, y))
                if cell_id:
                    if entity.entity_type == EntityType.TREASURE_BRONZE:
                        self.canvas.itemconfig(cell_id, fill="#CD7F32")  # Bronze color
                    elif entity.entity_type == EntityType.TREASURE_SILVER:
                        self.canvas.itemconfig(cell_id, fill="#C0C0C0")  # Silver color
                    elif entity.entity_type == EntityType.TREASURE_GOLD:
                        self.canvas.itemconfig(cell_id, fill="#FFD700")  # Gold color

        # Then draw hideouts and garrisons
        for entity in [e for e in self.simulation.entities if
                       isinstance(e, Hideout) or e.entity_type == EntityType.GARRISON]:
            x, y = entity.position
            x1 = x * self.cell_size
            y1 = y * self.cell_size

            image_key = None
            if entity.entity_type == EntityType.HIDEOUT:
                image_key = EntityType.HIDEOUT
            elif entity.entity_type == EntityType.GARRISON:
                image_key = EntityType.GARRISON

            # Try to use image
            if image_key in self.asset_manager.images:
                img_id = self.canvas.create_image(
                    x1, y1,
                    image=self.asset_manager.images[image_key],
                    anchor=tk.NW
                )
                self.grid_images[(x, y, entity.id)] = img_id
            else:
                # Fallback to colored rectangle
                cell_id = self.grid_cells.get((x, y))
                if cell_id:
                    if entity.entity_type == EntityType.HIDEOUT:
                        self.canvas.itemconfig(cell_id, fill="#8B4513")  # Brown
                    elif entity.entity_type == EntityType.GARRISON:
                        self.canvas.itemconfig(cell_id, fill="#800000")  # Maroon

        # Draw hunters
        for entity in [e for e in self.simulation.entities if isinstance(e, Hunter)]:
            x, y = entity.position
            x1 = x * self.cell_size
            y1 = y * self.cell_size

            # Try to use hunter image
            if EntityType.HUNTER in self.asset_manager.images:
                img_id = self.canvas.create_image(
                    x1, y1,
                    image=self.asset_manager.images[EntityType.HUNTER],
                    anchor=tk.NW
                )
                self.grid_images[(x, y, entity.id)] = img_id

                # Draw a small indicator if carrying treasure
                if entity.carried_treasure:
                    treasure_type = entity.carried_treasure.entity_type
                    indicator_x = x1 + self.cell_size * 3 / 4
                    indicator_y = y1 + self.cell_size * 1 / 4
                    radius = self.cell_size // 8

                    fill_color = "#FFD700"  # Default gold
                    if treasure_type == EntityType.TREASURE_BRONZE:
                        fill_color = "#CD7F32"
                    elif treasure_type == EntityType.TREASURE_SILVER:
                        fill_color = "#C0C0C0"

                    ind_id = self.canvas.create_oval(
                        indicator_x - radius, indicator_y - radius,
                        indicator_x + radius, indicator_y + radius,
                        fill=fill_color, outline="black"
                    )
                    self.grid_images[(x, y, f"{entity.id}_indicator")] = ind_id
            else:
                # Fallback to colored rectangle
                cell_id = self.grid_cells.get((x, y))
                if cell_id:
                    # Different colors for different skills
                    hunter = entity
                    if hunter.skill == HunterSkill.NAVIGATION:
                        color = "#87CEEB"  # Sky blue
                    elif hunter.skill == HunterSkill.ENDURANCE:
                        color = "#90EE90"  # Light green
                    else:  # Stealth
                        color = "#DDA0DD"  # Plum

                    self.canvas.itemconfig(cell_id, fill=color)

                    # Draw a black dot if carrying treasure
                    if hunter.carried_treasure:
                        center_x = x1 + self.cell_size // 2
                        center_y = y1 + self.cell_size // 2
                        radius = self.cell_size // 4
                        dot_id = self.canvas.create_oval(
                            center_x - radius, center_y - radius,
                            center_x + radius, center_y + radius,
                            fill="black"
                        )
                        self.grid_images[(x, y, f"{entity.id}_dot")] = dot_id

        # Draw knights
        for entity in [e for e in self.simulation.entities if isinstance(e, Knight)]:
            x, y = entity.position
            x1 = x * self.cell_size
            y1 = y * self.cell_size

            # Try to use knight image
            if EntityType.KNIGHT in self.asset_manager.images:
                img_id = self.canvas.create_image(
                    x1, y1,
                    image=self.asset_manager.images[EntityType.KNIGHT],
                    anchor=tk.NW
                )
                self.grid_images[(x, y, entity.id)] = img_id
            else:
                # Fallback to colored rectangle
                cell_id = self.grid_cells.get((x, y))
                if cell_id:
                    self.canvas.itemconfig(cell_id, fill="#FF0000")  # Red

        # Update statistics
        self.update_statistics()

        # Add visual indicators for knights in pursuit or challenging
        for entity in [e for e in self.simulation.entities if isinstance(e, Knight) and
                                                              (
                                                                      e.state == KnightState.PURSUING or e.state == KnightState.CHALLENGING)]:
            x, y = entity.position
            x1 = x * self.cell_size
            y1 = y * self.cell_size

            # Draw alert indicator above knight
            if entity.state == KnightState.PURSUING:
                # Exclamation mark for pursuing
                line_id = self.canvas.create_line(
                    x1 + self.cell_size / 2, y1 - self.cell_size / 4,
                    x1 + self.cell_size / 2, y1 - self.cell_size / 8,
                    width=3, fill="yellow"
                )
                dot_id = self.canvas.create_oval(
                    x1 + self.cell_size / 2 - 2, y1 - self.cell_size / 8 - 2,
                    x1 + self.cell_size / 2 + 2, y1 - self.cell_size / 8 + 2,
                    fill="yellow", outline="yellow"
                )
                self.grid_images[(x, y, f"{entity.id}_alert1")] = line_id
                self.grid_images[(x, y, f"{entity.id}_alert2")] = dot_id
            elif entity.state == KnightState.CHALLENGING:
                # Sword symbol for challenging
                sword_id = self.canvas.create_polygon(
                    x1 + self.cell_size / 4, y1 - self.cell_size / 8,
                    x1 + self.cell_size * 3 / 4, y1 - self.cell_size / 4,
                    x1 + self.cell_size * 2 / 3, y1 - self.cell_size / 6,
                    x1 + self.cell_size / 3, y1,
                    fill="red", outline="black"
                )
                self.grid_images[(x, y, f"{entity.id}_sword")] = sword_id

    def update_statistics(self):
        """Update the statistics display."""
        stats = self.simulation.get_statistics()

        self.step_label.config(text=f"Step: {stats['step']}")
        self.hunters_label.config(text=f"Hunters: {stats['hunters']}")
        self.treasures_label.config(text=f"Treasures: {stats['treasures']}")
        self.collected_label.config(text=f"Collected: {stats['collection_percentage']:.1f}%")

        self.hideouts_label.config(text=f"Hideouts: {stats['hideouts']}")
        self.knights_label.config(text=f"Knights: {stats['knights']}")

        # Count different treasure types
        bronze_count = sum(1 for e in self.simulation.entities
                           if e.entity_type == EntityType.TREASURE_BRONZE)
        silver_count = sum(1 for e in self.simulation.entities
                           if e.entity_type == EntityType.TREASURE_SILVER)
        gold_count = sum(1 for e in self.simulation.entities
                         if e.entity_type == EntityType.TREASURE_GOLD)

        self.bronze_label.config(text=f"Bronze Treasures: {bronze_count}")
        self.silver_label.config(text=f"Silver Treasures: {silver_count}")
        self.gold_label.config(text=f"Gold Treasures: {gold_count}")

        # Add log entry for step milestone
        if stats['step'] % 10 == 0:
            self.log_text.insert(tk.END, f"Step {stats['step']}: " +
                                 f"{stats['hunters']} hunters, {stats['treasures']} treasures, " +
                                 f"{stats['collection_percentage']:.1f}% collected\n")
            self.log_text.see(tk.END)

    def initialize_simulation(self):
        """Initialize or reset the simulation."""
        try:
            grid_size = int(self.grid_size_var.get())
            if grid_size < 10 or grid_size > 100:
                raise ValueError("Grid size must be between 10 and 100")
        except ValueError:
            messagebox.showerror("Error", "Invalid grid size. Please enter a number between 10 and 100.")
            return

        # Stop running if active
        self.is_running = False
        self.run_btn.config(text="Run")

        # Create new simulation
        self.simulation = EldoriaSimulation(grid_size)
        self.simulation.initialize()

        # Register event listeners for the new simulation
        self.simulation.add_event_listener('collect_treasure', lambda: self._play_sound('collect'))
        self.simulation.add_event_listener('challenge', lambda: self._play_sound('challenge'))
        self.simulation.add_event_listener('warning', lambda: self._play_sound('warning'))
        self.simulation.add_event_listener('footsteps', lambda: self._play_sound('footsteps'))

        # Update visualization
        self.create_grid()

        # Clear log
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, "Simulation initialized.\n")

        # Play initialization sound
        if self.sound_enabled.get() and PYGAME_AVAILABLE:
            # Try to play a fanfare or initialization sound if available
            pass

    def step_simulation(self):
        """Advance the simulation by one step."""
        if self.simulation.is_simulation_complete():
            messagebox.showinfo("Simulation Complete",
                                f"Simulation completed after {self.simulation.current_step} steps.\n" +
                                f"Collection percentage: {self.simulation.get_statistics()['collection_percentage']:.1f}%")
            self.is_running = False
            self.run_btn.config(text="Run")
            return

        # Perform simulation step
        self.simulation.step()

        # Update visualization
        self.update_visualization()

        # Check for significant events to log
        self._check_for_log_events()

    def _check_for_log_events(self):
        """Check for events that should be logged."""
        # This could track and log events like:
        # - Knights catching hunters
        # - Hunters collapsing
        # - New hunters being recruited
        # - Treasure collection milestones
        pass

    def toggle_run(self):
        """Toggle continuous simulation running."""
        self.is_running = not self.is_running

        if self.is_running:
            self.run_btn.config(text="Pause")
            self.run_simulation()
        else:
            self.run_btn.config(text="Run")

    def run_simulation(self):
        """Run the simulation continuously."""
        if not self.is_running:
            return

        if self.simulation.is_simulation_complete():
            messagebox.showinfo("Simulation Complete",
                                f"Simulation completed after {self.simulation.current_step} steps.\n" +
                                f"Collection percentage: {self.simulation.get_statistics()['collection_percentage']:.1f}%")
            self.is_running = False
            self.run_btn.config(text="Run")
            return

        self.step_simulation()

        # Calculate delay based on speed setting (1-10)
        delay = int(1000 / self.speed_var.get())
        self.root.after(delay, self.run_simulation)

    def start(self):
        """Start the visualization."""
        # Set window size
        self.root.geometry("1200x800")

        # Force window to update its geometry
        self.root.update_idletasks()

        # Initialize simulation on start
        self.initialize_simulation()

        # Start main loop
        self.root.mainloop()


# -----------------------------------------------------------------------------
# REINFORCEMENT LEARNING FOR HUNTER STRATEGY OPTIMIZATION
# -----------------------------------------------------------------------------
class QLearningHunterBrain:
    """Reinforcement learning for optimizing hunter behavior."""

    def __init__(self):
        # States: (has_treasure, stamina_level, knight_nearby, hideout_nearby)
        # has_treasure: 0=no, 1=yes
        # stamina_level: 0=critical, 1=low, 2=medium, 3=high
        # knight_nearby: 0=no, 1=yes
        # hideout_nearby: 0=no, 1=yes

        # Actions:
        # 0: move to nearest treasure
        # 1: move to nearest hideout
        # 2: evade nearby knights
        # 3: explore random direction

        self.q_table = {}
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.exploration_rate = 0.2

        # Initialize Q-table with zeros
        for has_treasure in [0, 1]:
            for stamina_level in [0, 1, 2, 3]:
                for knight_nearby in [0, 1]:
                    for hideout_nearby in [0, 1]:
                        state = (has_treasure, stamina_level, knight_nearby, hideout_nearby)
                        self.q_table[state] = [0.0, 0.0, 0.0, 0.0]  # Four possible actions

    def get_state(self, hunter: Hunter, simulation: EldoriaSimulation) -> tuple:
        """Convert hunter's situation to a state representation."""
        # Check if carrying treasure
        has_treasure = 1 if hunter.carried_treasure else 0

        # Determine stamina level
        if hunter.stamina <= STAMINA_CRITICAL_LEVEL:
            stamina_level = 0  # Critical
        elif hunter.stamina <= 30:
            stamina_level = 1  # Low
        elif hunter.stamina <= 70:
            stamina_level = 2  # Medium
        else:
            stamina_level = 3  # High

        # Check for nearby knights
        knight_nearby = 0
        for entity in simulation.entities:
            if (isinstance(entity, Knight) and
                    distance(hunter.position, entity.position) <= KNIGHT_DETECTION_RANGE):
                knight_nearby = 1
                break

        # Check for nearby hideouts
        hideout_nearby = 0
        for pos in hunter.known_hideouts:
            if distance(hunter.position, pos) <= 3:
                hideout_nearby = 1
                break

        return (has_treasure, stamina_level, knight_nearby, hideout_nearby)

    def choose_action(self, state, explore=True) -> int:
        """Choose an action based on the current state."""
        if explore and random.random() < self.exploration_rate:
            # Explore: choose a random action
            return random.randint(0, 3)
        else:
            # Exploit: choose the best action from Q-table
            return self.q_table[state].index(max(self.q_table[state]))

    def update_q_value(self, state, action, reward, next_state):
        """Update Q-value for a state-action pair."""
        # Calculate updated Q-value using Q-learning formula
        current_q = self.q_table[state][action]
        max_next_q = max(self.q_table[next_state])

        # Q(s,a) = Q(s,a) + α * [r + γ * max(Q(s',a')) - Q(s,a)]
        new_q = current_q + self.learning_rate * (
                reward + self.discount_factor * max_next_q - current_q
        )

        # Update Q-table
        self.q_table[state][action] = new_q

    def calculate_reward(self, hunter: Hunter, old_state, new_state,
                         simulation: EldoriaSimulation) -> float:
        """Calculate reward for the hunter's action."""
        reward = 0

        # Reward for collecting treasure
        if old_state[0] == 0 and new_state[0] == 1:  # Didn't have -> now has treasure
            reward += 10.0

        # Reward for depositing treasure
        if old_state[0] == 1 and new_state[0] == 0:  # Had -> now doesn't have treasure
            # Check if it was deposited (not stolen)
            hideout_present = False
            for entity in simulation.get_entities_at(hunter.position):
                if isinstance(entity, Hideout):
                    hideout_present = True
                    break

            if hideout_present:
                reward += 20.0  # Successfully deposited

        # Penalty for critical stamina
        if new_state[1] == 0:  # Critical stamina
            reward -= 5.0

        # Penalty for being near knights
        if new_state[2] == 1:  # Knight nearby
            reward -= 15.0

        # Reward for finding hideout when needed
        if old_state[1] <= 1 and old_state[3] == 0 and new_state[3] == 1:
            reward += 10.0  # Found hideout when stamina is low

        return reward

    def train(self, simulation: EldoriaSimulation, episodes=100):
        """Train the Q-learning model through multiple simulation episodes."""
        for episode in range(episodes):
            # Reset simulation
            simulation.initialize()

            # Track hunters and their states
            hunter_states = {}

            while not simulation.is_simulation_complete():
                # Store old states for each hunter
                old_states = {}
                actions = {}

                # Choose actions for each hunter based on current state
                for entity in simulation.entities:
                    if isinstance(entity, Hunter):
                        state = self.get_state(entity, simulation)
                        old_states[entity.id] = state
                        actions[entity.id] = self.choose_action(state)

                # Execute simulation step
                simulation.step()

                # Calculate rewards and update Q-values
                for entity in simulation.entities:
                    if isinstance(entity, Hunter) and entity.id in old_states:
                        hunter = entity
                        old_state = old_states[hunter.id]
                        action = actions[hunter.id]
                        new_state = self.get_state(hunter, simulation)

                        reward = self.calculate_reward(hunter, old_state, new_state, simulation)
                        self.update_q_value(old_state, action, reward, new_state)

            # Reduce exploration rate over time
            self.exploration_rate = max(0.05, self.exploration_rate * 0.95)

            print(f"Episode {episode + 1}/{episodes} completed. Collection percentage: "
                  f"{simulation.get_statistics()['collection_percentage']:.1f}%")

    def apply_learned_strategy(self, hunter: Hunter, simulation: EldoriaSimulation):
        """Apply the learned strategy to a hunter."""
        state = self.get_state(hunter, simulation)
        action = self.choose_action(state, explore=False)

        # Apply the chosen action
        if action == 0:  # Move to nearest treasure
            # Find nearest known treasure
            if hunter.known_treasures:
                nearest_treasure = min(hunter.known_treasures.keys(),
                                       key=lambda pos: distance(hunter.position, pos))
                hunter.target_position = nearest_treasure
                obstacles = hunter._get_obstacle_positions(simulation)
                hunter.current_path = a_star_pathfinding(hunter.position, nearest_treasure, obstacles)
                hunter.state = HunterState.COLLECTING

        elif action == 1:  # Move to nearest hideout
            # Find nearest known hideout
            if hunter.known_hideouts:
                nearest_hideout = min(hunter.known_hideouts,
                                      key=lambda pos: distance(hunter.position, pos))
                hunter.target_position = nearest_hideout
                obstacles = hunter._get_obstacle_positions(simulation)
                hunter.current_path = a_star_pathfinding(hunter.position, nearest_hideout, obstacles)

                if hunter.carried_treasure:
                    hunter.state = HunterState.RETURNING
                else:
                    hunter.state = HunterState.EXPLORING

        elif action == 2:  # Evade nearby knights
            hunter.state = HunterState.EVADING

        elif action == 3:  # Explore random direction
            hunter.state = HunterState.EXPLORING
            hunter._generate_exploration_path(simulation)


# -----------------------------------------------------------------------------
# ADVANCED HUNTER STRATEGY USING CLUSTERING
# -----------------------------------------------------------------------------
class ClusteringHunterStrategy:
    """Uses simple clustering to optimize hunter exploration and coordination."""

    def __init__(self, simulation):
        self.simulation = simulation
        self.cluster_centers = []
        self.num_clusters = 0
        self.assigned_clusters = {}  # Hunter ID to cluster index

    def analyze_environment(self):
        """Analyze the environment to identify areas of interest."""
        # Collect all treasure positions
        treasure_positions = []
        for entity in self.simulation.entities:
            if isinstance(entity, Treasure):
                treasure_positions.append([entity.position[0], entity.position[1]])

        if not treasure_positions:
            return

        # Determine optimal number of clusters
        hunters = [e for e in self.simulation.entities if isinstance(e, Hunter)]
        hideouts = [e for e in self.simulation.entities if isinstance(e, Hideout)]

        # Number of clusters should be based on available hunters and treasures
        self.num_clusters = min(len(hunters), len(hideouts) * 2,
                                max(1, len(treasure_positions) // 10))

        # Simple clustering - just divide the map into regions
        # This is a basic alternative to K-means
        self.cluster_centers = []

        # Create a grid of cluster centers
        grid_dim = int(math.sqrt(self.num_clusters)) + 1
        step_x = self.simulation.grid_size / grid_dim
        step_y = self.simulation.grid_size / grid_dim

        for i in range(grid_dim):
            for j in range(grid_dim):
                if len(self.cluster_centers) < self.num_clusters:
                    center_x = (i + 0.5) * step_x
                    center_y = (j + 0.5) * step_y
                    self.cluster_centers.append([center_x, center_y])

        # Adjust cluster centers based on treasure density
        if treasure_positions and self.cluster_centers:
            # For each cluster center, pull it toward nearby treasures
            for i, center in enumerate(self.cluster_centers):
                nearby_treasures = []
                for t_pos in treasure_positions:
                    if distance((center[0], center[1]), (t_pos[0], t_pos[1])) < step_x * 1.5:
                        nearby_treasures.append(t_pos)

                if nearby_treasures:
                    # Calculate average position of nearby treasures
                    avg_x = sum(t[0] for t in nearby_treasures) / len(nearby_treasures)
                    avg_y = sum(t[1] for t in nearby_treasures) / len(nearby_treasures)

                    # Pull cluster center toward treasures
                    self.cluster_centers[i][0] = (center[0] * 0.3 + avg_x * 0.7)
                    self.cluster_centers[i][1] = (center[1] * 0.3 + avg_y * 0.7)

    def assign_hunters_to_clusters(self):
        """Assign hunters to exploration clusters."""
        hunters = [e for e in self.simulation.entities if isinstance(e, Hunter)]

        if not hunters or self.num_clusters == 0:
            return

        # Initialize assignment with empty list
        self.assigned_clusters = {}

        # Assign hunters to minimize total distance (greedy approach)
        assigned_clusters = set()

        # First, assign one hunter to each cluster if possible
        for hunter in hunters:
            if len(assigned_clusters) >= self.num_clusters:
                break

            # Find nearest unassigned cluster
            min_dist = float('inf')
            best_cluster = -1

            for j in range(self.num_clusters):
                if j in assigned_clusters:
                    continue

                center = self.cluster_centers[j]
                dist = distance(hunter.position, (int(center[0]), int(center[1])))

                if dist < min_dist:
                    min_dist = dist
                    best_cluster = j

            if best_cluster != -1:
                self.assigned_clusters[hunter.id] = best_cluster
                assigned_clusters.add(best_cluster)

        # Assign remaining hunters to nearest clusters
        for hunter in hunters:
            if hunter.id not in self.assigned_clusters:
                # Find nearest cluster
                min_dist = float('inf')
                best_cluster = 0

                for j in range(self.num_clusters):
                    center = self.cluster_centers[j]
                    dist = distance(hunter.position, (int(center[0]), int(center[1])))

                    if dist < min_dist:
                        min_dist = dist
                        best_cluster = j

                self.assigned_clusters[hunter.id] = best_cluster

    def guide_hunter(self, hunter: Hunter):
        """Guide a hunter based on its assigned cluster."""
        if hunter.id not in self.assigned_clusters or self.num_clusters == 0:
            return

        # Get assigned cluster
        cluster_idx = self.assigned_clusters[hunter.id]
        if cluster_idx >= len(self.cluster_centers):
            return

        # Get cluster center
        center = self.cluster_centers[cluster_idx]
        target_pos = (int(center[0]), int(center[1]))

        # If hunter is already targeting its cluster center, don't change
        if hunter.target_position == target_pos:
            return

        # If hunter is carrying treasure or has critical stamina, don't override behavior
        if hunter.carried_treasure or hunter.stamina <= STAMINA_CRITICAL_LEVEL:
            return

        # If hunter is in a suitable state for exploration
        if hunter.state in [HunterState.EXPLORING, None]:
            # Set target to cluster center
            hunter.target_position = target_pos
            obstacles = hunter._get_obstacle_positions(self.simulation)
            hunter.current_path = a_star_pathfinding(hunter.position, target_pos, obstacles)


# -----------------------------------------------------------------------------
# SIMPLE K-MEANS IMPLEMENTATION
# -----------------------------------------------------------------------------
def simple_kmeans(data, k, max_iterations=100):
    """
    A simple implementation of k-means clustering without external libraries.

    Args:
        data: List of data points, each point is [x, y]
        k: Number of clusters
        max_iterations: Maximum number of iterations

    Returns:
        centers: List of cluster centers
    """
    if not data or k <= 0 or k > len(data):
        return []

    # Initialize centers randomly
    centers = random.sample(data, k)

    for _ in range(max_iterations):
        # Assign each point to nearest center
        clusters = [[] for _ in range(k)]

        for point in data:
            # Find nearest center
            nearest = 0
            min_dist = float('inf')

            for i, center in enumerate(centers):
                # Euclidean distance
                dist = ((point[0] - center[0]) ** 2 + (point[1] - center[1]) ** 2) ** 0.5

                if dist < min_dist:
                    min_dist = dist
                    nearest = i

            # Add to appropriate cluster
            clusters[nearest].append(point)

        # Compute new centers
        new_centers = []
        for i, cluster in enumerate(clusters):
            if not cluster:
                # If a cluster is empty, keep old center
                new_centers.append(centers[i])
            else:
                # Average position
                avg_x = sum(p[0] for p in cluster) / len(cluster)
                avg_y = sum(p[1] for p in cluster) / len(cluster)
                new_centers.append([avg_x, avg_y])

        # Check convergence
        converged = True
        for i in range(k):
            if ((centers[i][0] - new_centers[i][0]) ** 2 +
                (centers[i][1] - new_centers[i][1]) ** 2) > 0.0001:
                converged = False
                break

        centers = new_centers

        if converged:
            break

    return centers


# -----------------------------------------------------------------------------
# MAIN FUNCTION
# -----------------------------------------------------------------------------
def main():
    """Main function to run the simulation."""
    # Create and initialize the simulation
    simulation = EldoriaSimulation(GRID_SIZE)
    simulation.initialize()

    # Optional: Train reinforcement learning for better hunter behavior
    # Uncomment to enable (may take some time)
    # q_learning = QLearningHunterBrain()
    # q_learning.train(simulation, episodes=10)

    # Create and start the visualization
    visualization = EldoriaVisualization(simulation)
    visualization.start()


if __name__ == "__main__":
    main()