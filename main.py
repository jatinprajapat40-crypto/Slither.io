#!/usr/bin/env python3
"""
SLITHER ROYALE – AI SNAKE ARENA
A massive AI snake battle royale game in a single Python file.
"""

import pygame
import math
import random
import sys
import os
import json
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum, auto
from collections import deque

from skins import SkinManager
from ui import UIManager

# ============================================================
# REGION: CONFIGURATION
# ============================================================

@dataclass
class Config:
    SCREEN_WIDTH: int = 1280
    SCREEN_HEIGHT: int = 720
    FPS: int = 60
    WORLD_SIZE: int = 6000
    NUM_AI_SNAKES: int = 60
    INITIAL_SNAKE_LENGTH: int = 5
    SEGMENT_SIZE: int = 10
    SEGMENT_SPACING: int = 8
    SNAKE_SPEED: float = 2.5
    BOOST_SPEED: float = 4.5
    DASH_SPEED: float = 12.0
    TURN_SPEED: float = 0.08
    MAX_ENERGY: float = 100.0
    ENERGY_REGEN: float = 0.15
    BOOST_COST: float = 0.4
    DASH_COST: float = 25.0
    FOOD_COUNT: int = 800
    COIN_COUNT: int = 150
    POWERUP_COUNT: int = 30
    SHRINK_INTERVAL: float = 30.0
    SHRINK_AMOUNT: float = 150.0
    MIN_ZONE_RADIUS: float = 400.0
    BORDER_DAMAGE: float = 0.5
    GRID_CELL_SIZE: int = 200
    MINIMAP_SIZE: int = 180
    MINIMAP_MARGIN: int = 10
    KO_DURATION: float = 1.5
    PARTICLE_POOL_SIZE: int = 2000
    CAMERA_SMOOTHING: float = 0.08
    CAMERA_ZOOM_DEFAULT: float = 1.0
    CAMERA_ZOOM_MIN: float = 0.4
    CAMERA_ZOOM_MAX: float = 2.0

CFG = Config()

# ============================================================
# REGION: COLOR PALETTE
# ============================================================

class Colors:
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    RED = (255, 60, 60)
    GREEN = (60, 255, 60)
    BLUE = (60, 120, 255)
    YELLOW = (255, 220, 40)
    ORANGE = (255, 160, 40)
    PURPLE = (180, 60, 255)
    CYAN = (40, 220, 255)
    PINK = (255, 100, 180)
    DARK_BG = (12, 15, 25)
    DARK_PANEL = (20, 25, 40)
    DARK_PANEL2 = (30, 35, 55)
    GRID_COLOR = (25, 30, 50)
    ZONE_BORDER = (255, 40, 40)
    ZONE_WARNING = (255, 100, 40)
    GOLD = (255, 200, 40)
    DIAMOND_BLUE = (100, 200, 255)
    HEALTH_GREEN = (40, 200, 80)
    HEALTH_RED = (200, 40, 40)
    XP_PURPLE = (140, 80, 255)
    UI_ACCENT = (80, 140, 255)
    UI_HOVER = (100, 170, 255)
    TRANSPARENT_BLACK = (0, 0, 0, 128)

    SNAKE_PALETTES = [
        [(255, 80, 80),   (200, 40, 40)],
        [(80, 255, 80),   (40, 180, 40)],
        [(80, 120, 255),  (40, 80, 200)],
        [(255, 200, 40),  (200, 160, 20)],
        [(255, 100, 200), (200, 60, 160)],
        [(100, 255, 255), (60, 200, 200)],
        [(200, 100, 255), (160, 60, 200)],
        [(255, 160, 60),  (200, 120, 40)],
        [(180, 255, 100), (140, 200, 60)],
        [(255, 120, 120), (200, 80, 80)],
        [(120, 200, 255), (80, 160, 200)],
        [(255, 180, 120), (200, 140, 80)],
        [(160, 255, 160), (120, 200, 120)],
        [(255, 140, 255), (200, 100, 200)],
        [(140, 255, 200), (100, 200, 160)],
        [(255, 255, 140), (200, 200, 100)],
    ]

# ============================================================
# REGION: ENUMS
# ============================================================

class GameState(Enum):
    MAIN_MENU   = auto()
    PLAYING     = auto()
    SHOP        = auto()
    CUSTOMIZE   = auto()
    GAME_OVER   = auto()
    SPECTATING  = auto()
    MODE_SELECT = auto()
    STATS_SCREEN= auto()
    PAUSED      = auto()

class Rarity(Enum):
    COMMON    = auto()
    RARE      = auto()
    EPIC      = auto()
    MYTHIC    = auto()
    LEGENDARY = auto()

class AbilityType(Enum):
    SPEED_BOOST  = auto()
    DASH         = auto()
    SHIELD       = auto()
    MAGNET       = auto()
    GHOST        = auto()
    FREEZE_PULSE = auto()
    POISON_TRAIL = auto()
    TELEPORT     = auto()

class AIPersonality(Enum):
    AGGRESSIVE = auto()
    DEFENSIVE  = auto()
    HUNTER     = auto()
    COLLECTOR  = auto()
    AMBUSHER   = auto()
    NOMAD      = auto()
    TACTICIAN  = auto()

class GameMode(Enum):
    BATTLE_ROYALE = auto()
    ENDLESS       = auto()
    TOURNAMENT    = auto()
    HARDCORE      = auto()
    CHAOS         = auto()

class PowerUpType(Enum):
    SPEED      = auto()
    SHIELD     = auto()
    MAGNET     = auto()
    GHOST      = auto()
    GROWTH     = auto()
    SCORE_MULT = auto()

# ============================================================
# REGION: UTILITY FUNCTIONS
# ============================================================

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def lerp_color(c1: Tuple[int,...], c2: Tuple[int,...], t: float) -> Tuple[int,...]:
    t = max(0, min(1, t))
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))

def dist(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return math.sqrt(dx*dx + dy*dy)

def dist_sq(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return dx*dx + dy*dy

def angle_to(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.atan2(p2[1] - p1[1], p2[0] - p1[0])

def normalize_angle(a: float) -> float:
    while a > math.pi:  a -= 2 * math.pi
    while a < -math.pi: a += 2 * math.pi
    return a

def clamp(v: float, mn: float, mx: float) -> float:
    return max(mn, min(mx, v))

def point_in_circle(px, py, cx, cy, r):
    return (px-cx)**2 + (py-cy)**2 <= r*r

def random_position(margin=100):
    hw = CFG.WORLD_SIZE // 2 - margin
    return (random.uniform(-hw, hw), random.uniform(-hw, hw))

def ease_out_cubic(t):
    return 1 - (1 - t) ** 3

def ease_in_out_sine(t):
    return -(math.cos(math.pi * t) - 1) / 2

def pulse(t, speed=1.0):
    return (math.sin(t * speed * math.pi * 2) + 1) / 2

def draw_text(surface, text, x, y, font, color=Colors.WHITE, center=False, shadow=True):
    if shadow:
        shadow_surf = font.render(str(text), True, (0, 0, 0))
        if center:
            r = shadow_surf.get_rect(center=(x+2, y+2))
        else:
            r = shadow_surf.get_rect(topleft=(x+2, y+2))
        surface.blit(shadow_surf, r)
    text_surf = font.render(str(text), True, color)
    if center:
        r = text_surf.get_rect(center=(x, y))
    else:
        r = text_surf.get_rect(topleft=(x, y))
    surface.blit(text_surf, r)
    return r

def create_glow_surface(radius, color, alpha=80):
    size = radius * 2
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    for r in range(radius, 0, -2):
        a = int(alpha * (r / radius))
        pygame.draw.circle(s, (*color[:3], a), (radius, radius), r)
    return s

# ============================================================
# REGION: SPATIAL HASH GRID
# ============================================================

class SpatialGrid:
    def __init__(self, cell_size: int):
        self.cell_size = cell_size
        self.cells: Dict[Tuple[int,int], List] = {}

    def clear(self):
        self.cells.clear()

    def _key(self, x: float, y: float) -> Tuple[int, int]:
        return (int(x // self.cell_size), int(y // self.cell_size))

    def insert(self, obj, x: float, y: float):
        k = self._key(x, y)
        if k not in self.cells:
            self.cells[k] = []
        self.cells[k].append(obj)

    def query(self, x: float, y: float, radius: float) -> List:
        result = []
        cr = int(radius // self.cell_size) + 1
        cx, cy = self._key(x, y)
        for dx in range(-cr, cr + 1):
            for dy in range(-cr, cr + 1):
                k = (cx + dx, cy + dy)
                if k in self.cells:
                    result.extend(self.cells[k])
        return result

# ============================================================
# REGION: PARTICLE SYSTEM
# ============================================================

@dataclass
class Particle:
    x: float = 0
    y: float = 0
    vx: float = 0
    vy: float = 0
    life: float = 0
    max_life: float = 1.0
    color: Tuple[int,...] = (255, 255, 255)
    size: float = 3
    active: bool = False
    fade: bool = True
    gravity: float = 0
    shrink: bool = True

class ParticleSystem:
    def __init__(self, pool_size: int = 2000):
        self.particles: List[Particle] = [Particle() for _ in range(pool_size)]
        self.active_count = 0

    def emit(self, x, y, vx=0, vy=0, color=(255,255,255), life=1.0,
             size=3, count=1, spread=50, gravity=0, shrink=True):
        emitted = 0
        for p in self.particles:
            if not p.active and emitted < count:
                p.x = x + random.uniform(-3, 3)
                p.y = y + random.uniform(-3, 3)
                p.vx = vx + random.uniform(-spread, spread)
                p.vy = vy + random.uniform(-spread, spread)
                p.life = life
                p.max_life = life
                p.color = color
                p.size = size + random.uniform(-1, 1)
                p.active = True
                p.fade = True
                p.gravity = gravity
                p.shrink = shrink
                emitted += 1
            if emitted >= count:
                break

    def update(self, dt: float):
        self.active_count = 0
        for p in self.particles:
            if p.active:
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.vy += p.gravity * dt
                p.life -= dt
                if p.life <= 0:
                    p.active = False
                else:
                    self.active_count += 1

    def draw(self, surface, camera):
        for p in self.particles:
            if p.active:
                sx, sy = camera.world_to_screen(p.x, p.y)
                if -20 < sx < CFG.SCREEN_WIDTH + 20 and -20 < sy < CFG.SCREEN_HEIGHT + 20:
                    t = p.life / p.max_life
                    sz = max(1, int(p.size * t)) if p.shrink else max(1, int(p.size))
                    sz = int(sz * camera.zoom)
                    if sz > 0:
                        pygame.draw.circle(surface, p.color[:3], (int(sx), int(sy)), sz)

# ============================================================
# REGION: CAMERA SYSTEM
# ============================================================

class Camera:
    def __init__(self):
        self.x: float = 0
        self.y: float = 0
        self.target_x: float = 0
        self.target_y: float = 0
        self.zoom: float = CFG.CAMERA_ZOOM_DEFAULT
        self.target_zoom: float = CFG.CAMERA_ZOOM_DEFAULT
        self.shake_intensity: float = 0
        self.shake_timer: float = 0
        self.shake_offset_x: float = 0
        self.shake_offset_y: float = 0

    def set_target(self, x: float, y: float):
        self.target_x = x
        self.target_y = y

    def shake(self, intensity: float = 10, duration: float = 0.3):
        self.shake_intensity = intensity
        self.shake_timer = duration

    def update(self, dt: float):
        self.x = lerp(self.x, self.target_x, CFG.CAMERA_SMOOTHING)
        self.y = lerp(self.y, self.target_y, CFG.CAMERA_SMOOTHING)
        self.zoom = lerp(self.zoom, self.target_zoom, 0.05)
        self.zoom = clamp(self.zoom, CFG.CAMERA_ZOOM_MIN, CFG.CAMERA_ZOOM_MAX)
        if self.shake_timer > 0:
            self.shake_timer -= dt
            t = self.shake_timer / 0.3
            self.shake_offset_x = random.uniform(-1, 1) * self.shake_intensity * t
            self.shake_offset_y = random.uniform(-1, 1) * self.shake_intensity * t
        else:
            self.shake_offset_x = 0
            self.shake_offset_y = 0

    def world_to_screen(self, wx: float, wy: float) -> Tuple[int, int]:
        sx = (wx - self.x) * self.zoom + CFG.SCREEN_WIDTH  / 2 + self.shake_offset_x
        sy = (wy - self.y) * self.zoom + CFG.SCREEN_HEIGHT / 2 + self.shake_offset_y
        return (int(sx), int(sy))

    def screen_to_world(self, sx: int, sy: int) -> Tuple[float, float]:
        wx = (sx - CFG.SCREEN_WIDTH  / 2 - self.shake_offset_x) / self.zoom + self.x
        wy = (sy - CFG.SCREEN_HEIGHT / 2 - self.shake_offset_y) / self.zoom + self.y
        return (wx, wy)

    def is_visible(self, wx: float, wy: float, margin: float = 100) -> bool:
        sx, sy = self.world_to_screen(wx, wy)
        return (-margin < sx < CFG.SCREEN_WIDTH  + margin and
                -margin < sy < CFG.SCREEN_HEIGHT + margin)

# ============================================================
# REGION: FOOD / COLLECTIBLES
# ============================================================

@dataclass
class Food:
    x: float
    y: float
    size: float = 4
    color: Tuple[int,...] = (255, 255, 255)
    value: int = 1
    active: bool = True
    pulse_offset: float = 0

@dataclass
class Coin:
    x: float
    y: float
    value: int = 1
    active: bool = True
    pulse_offset: float = 0
    sparkle_timer: float = 0

@dataclass
class PowerUp:
    x: float
    y: float
    type: PowerUpType = PowerUpType.SPEED
    active: bool = True
    duration: float = 8.0
    pulse_offset: float = 0

# ============================================================
# REGION: ABILITY SYSTEM
# ============================================================

@dataclass
class Ability:
    type: AbilityType
    cooldown: float
    max_cooldown: float
    energy_cost: float
    duration: float
    active: bool = False
    timer: float = 0

    def can_use(self, energy: float) -> bool:
        return self.cooldown <= 0 and energy >= self.energy_cost and not self.active

    def use(self):
        self.active = True
        self.timer = self.duration
        self.cooldown = self.max_cooldown

    def update(self, dt: float):
        if self.cooldown > 0:
            self.cooldown -= dt
        if self.active:
            self.timer -= dt
            if self.timer <= 0:
                self.active = False

# ============================================================
# REGION: SNAKE
# ============================================================

class Snake:
    _id_counter = 0

    def __init__(self, x: float, y: float, is_player: bool = False, name: str = ""):
        Snake._id_counter += 1
        self.id   = Snake._id_counter
        self.name = name or f"Snake_{self.id}"
        self.is_player = is_player
        self.alive = True
        self.x = x
        self.y = y
        self.angle: float = random.uniform(-math.pi, math.pi)
        self.target_angle: float = self.angle
        self.speed: float = CFG.SNAKE_SPEED
        self.base_speed: float = CFG.SNAKE_SPEED
        self.segments: List[Tuple[float, float]] = []
        self.segment_count: int = CFG.INITIAL_SNAKE_LENGTH
        self.energy: float = CFG.MAX_ENERGY
        self.max_energy: float = CFG.MAX_ENERGY
        self.health: float = 100.0
        self.max_health: float = 100.0
        self.score: int = 0
        self.kills: int = 0
        self.coins_collected: int = 0
        self.boosting: bool = False
        self.dashing: bool = False
        self.dash_timer: float = 0
        palette = random.choice(Colors.SNAKE_PALETTES)
        self.color1 = palette[0]
        self.color2 = palette[1]
        self.head_size: float = CFG.SEGMENT_SIZE
        # AI
        self.personality: AIPersonality = random.choice(list(AIPersonality))
        self.aggression: float = random.uniform(0.2, 1.0)
        self.fear: float = random.uniform(0.2, 1.0)
        self.intelligence: float = random.uniform(0.3, 1.0)
        self.ai_timer: float = 0
        self.ai_target: Optional[Tuple[float, float]] = None
        self.ai_state: str = "wander"
        # Abilities
        self.abilities: Dict[AbilityType, Ability] = {}
        self._init_abilities()
        # Power-ups
        self.shield_active: bool = False
        self.shield_timer: float = 0
        self.ghost_active: bool = False
        self.ghost_timer: float = 0
        self.magnet_active: bool = False
        self.magnet_timer: float = 0
        self.speed_boost_timer: float = 0
        self.score_multiplier: float = 1.0
        self.score_mult_timer: float = 0
        self.invincible_timer: float = 2.0   # spawn protection
        # Visual
        self.glow_alpha: float = 0
        self.death_particles_spawned: bool = False
        # Evolution
        self.level: int = 1
        self.xp: int = 0
        self.xp_to_next: int = 50
        # Poison trail
        self.poison_trail: List[Tuple[float, float, float]] = []
        # Init segments
        for i in range(self.segment_count):
            self.segments.append((
                x - i * CFG.SEGMENT_SPACING * math.cos(self.angle),
                y - i * CFG.SEGMENT_SPACING * math.sin(self.angle)
            ))

    def _init_abilities(self):
        self.abilities[AbilityType.DASH]         = Ability(AbilityType.DASH,         0, 3.0,  25, 0.2)
        self.abilities[AbilityType.SHIELD]        = Ability(AbilityType.SHIELD,        0, 15.0, 30, 5.0)
        self.abilities[AbilityType.MAGNET]        = Ability(AbilityType.MAGNET,        0, 12.0, 20, 6.0)
        self.abilities[AbilityType.GHOST]         = Ability(AbilityType.GHOST,         0, 20.0, 40, 4.0)
        self.abilities[AbilityType.FREEZE_PULSE]  = Ability(AbilityType.FREEZE_PULSE,  0, 18.0, 35, 0.1)
        self.abilities[AbilityType.POISON_TRAIL]  = Ability(AbilityType.POISON_TRAIL,  0, 15.0, 30, 5.0)
        self.abilities[AbilityType.TELEPORT]      = Ability(AbilityType.TELEPORT,      0, 25.0, 50, 0.1)

    @property
    def head(self) -> Tuple[float, float]:
        return (self.x, self.y)

    @property
    def length(self) -> int:
        return len(self.segments)

    def grow(self, amount: int = 1):
        for _ in range(amount):
            if self.segments:
                self.segments.append(self.segments[-1])
            self.segment_count += 1
        self.head_size = CFG.SEGMENT_SIZE + min(self.segment_count * 0.05, 8)

    def add_xp(self, amount: int):
        self.xp += amount
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(self.xp_to_next * 1.5)
            self.max_health += 10
            self.health = min(self.health + 20, self.max_health)
            self.max_energy += 5

    def update(self, dt: float, zone_center, zone_radius):
        if not self.alive:
            return

        for ab in self.abilities.values():
            ab.update(dt)

        if self.invincible_timer > 0:
            self.invincible_timer -= dt
        if self.shield_timer > 0:
            self.shield_timer -= dt
            if self.shield_timer <= 0:
                self.shield_active = False
        if self.ghost_timer > 0:
            self.ghost_timer -= dt
            if self.ghost_timer <= 0:
                self.ghost_active = False
        if self.magnet_timer > 0:
            self.magnet_timer -= dt
            if self.magnet_timer <= 0:
                self.magnet_active = False
        if self.speed_boost_timer > 0:
            self.speed_boost_timer -= dt
        if self.score_mult_timer > 0:
            self.score_mult_timer -= dt
            if self.score_mult_timer <= 0:
                self.score_multiplier = 1.0

        if self.dashing:
            self.dash_timer -= dt
            if self.dash_timer <= 0:
                self.dashing = False
                self.speed = self.base_speed

        angle_diff = normalize_angle(self.target_angle - self.angle)
        turn_speed = CFG.TURN_SPEED
        if self.dashing:
            turn_speed *= 0.3
        self.angle += angle_diff * turn_speed * 60 * dt

        actual_speed = self.speed
        if self.boosting and self.energy > 0:
            actual_speed = CFG.BOOST_SPEED
            self.energy -= CFG.BOOST_COST * 60 * dt
            if self.energy <= 0:
                self.energy = 0
                self.boosting = False
        elif self.dashing:
            actual_speed = CFG.DASH_SPEED
        elif self.speed_boost_timer > 0:
            actual_speed = self.base_speed * 1.5

        if not self.boosting and not self.dashing:
            self.energy = min(self.energy + CFG.ENERGY_REGEN * 60 * dt, self.max_energy)

        self.x += math.cos(self.angle) * actual_speed * 60 * dt
        self.y += math.sin(self.angle) * actual_speed * 60 * dt

        half = CFG.WORLD_SIZE // 2
        self.x = clamp(self.x, -half, half)
        self.y = clamp(self.y, -half, half)

        self.segments[0] = (self.x, self.y)
        for i in range(1, len(self.segments)):
            px, py = self.segments[i-1]
            cx, cy = self.segments[i]
            dx = px - cx
            dy = py - cy
            d = math.sqrt(dx*dx + dy*dy)
            if d > CFG.SEGMENT_SPACING:
                ratio = CFG.SEGMENT_SPACING / d
                self.segments[i] = (px - dx * ratio, py - dy * ratio)

        d_center = dist(self.head, zone_center)
        if d_center > zone_radius:
            if self.invincible_timer <= 0 and not self.shield_active:
                excess = (d_center - zone_radius) / 100
                self.health -= CFG.BORDER_DAMAGE * (1 + excess) * 60 * dt
                if self.health <= 0:
                    self.alive = False

        if self.abilities[AbilityType.POISON_TRAIL].active:
            self.poison_trail.append((self.x, self.y, 5.0))
        new_trail = []
        for tx, ty, tt in self.poison_trail:
            nt = tt - dt
            if nt > 0:
                new_trail.append((tx, ty, nt))
        self.poison_trail = new_trail

    def take_damage(self, amount: float):
        if self.invincible_timer > 0 or self.shield_active:
            return
        self.health -= amount
        if self.health <= 0:
            self.alive = False

    def use_ability(self, ability_type: AbilityType):
        if ability_type not in self.abilities:
            return False
        ab = self.abilities[ability_type]
        if ab.can_use(self.energy):
            self.energy -= ab.energy_cost
            ab.use()
            if ability_type == AbilityType.DASH:
                self.dashing = True
                self.dash_timer = ab.duration
            elif ability_type == AbilityType.SHIELD:
                self.shield_active = True
                self.shield_timer = ab.duration
            elif ability_type == AbilityType.GHOST:
                self.ghost_active = True
                self.ghost_timer = ab.duration
            elif ability_type == AbilityType.MAGNET:
                self.magnet_active = True
                self.magnet_timer = ab.duration
            elif ability_type == AbilityType.TELEPORT:
                self.x += math.cos(self.angle) * 200
                self.y += math.sin(self.angle) * 200
            return True
        return False

    def get_radius(self) -> float:
        return self.head_size

# ============================================================
# REGION: AI CONTROLLER
# ============================================================

class AIController:
    def __init__(self):
        self.update_interval = 0.15

    def update(self, snake: Snake, all_snakes: List[Snake], foods: List[Food],
               coins: List[Coin], powerups: List[PowerUp],
               zone_center, zone_radius, dt: float):
        if not snake.alive or snake.is_player:
            return
        snake.ai_timer -= dt
        if snake.ai_timer > 0:
            return
        snake.ai_timer = self.update_interval + random.uniform(-0.05, 0.05)

        head    = snake.head
        d_zone  = dist(head, zone_center)

        if d_zone > zone_radius - 150:
            snake.target_angle = angle_to(head, zone_center) + random.uniform(-0.3, 0.3)
            snake.boosting = d_zone > zone_radius - 50
            snake.ai_state = "flee_zone"
            return

        nearest_threat = None
        nearest_threat_dist = 999999
        for other in all_snakes:
            if other.id == snake.id or not other.alive:
                continue
            d = dist(head, other.head)
            if d < 200 and other.length > snake.length * 0.8:
                if d < nearest_threat_dist:
                    nearest_threat_dist = d
                    nearest_threat = other

        if nearest_threat and nearest_threat_dist < 150:
            if snake.personality in (AIPersonality.DEFENSIVE, AIPersonality.NOMAD) or \
               (snake.fear > 0.6 and nearest_threat.length > snake.length):
                flee_angle = angle_to(nearest_threat.head, head)
                snake.target_angle = flee_angle + random.uniform(-0.4, 0.4)
                snake.boosting = True
                snake.ai_state = "flee"
                if random.random() < 0.1 * snake.intelligence:
                    if snake.abilities[AbilityType.DASH].can_use(snake.energy):
                        snake.use_ability(AbilityType.DASH)
                    elif snake.abilities[AbilityType.GHOST].can_use(snake.energy):
                        snake.use_ability(AbilityType.GHOST)
                return
            elif snake.personality in (AIPersonality.AGGRESSIVE, AIPersonality.HUNTER) and \
                 snake.length > nearest_threat.length * 1.2:
                snake.target_angle = angle_to(head, nearest_threat.head) + random.uniform(-0.2, 0.2)
                snake.boosting = True
                snake.ai_state = "attack"
                if random.random() < 0.05:
                    snake.use_ability(AbilityType.DASH)
                return

        if snake.personality == AIPersonality.AMBUSHER and random.random() < 0.3:
            snake.boosting = False
            snake.ai_state = "ambush"
            if random.random() < 0.1:
                snake.target_angle += random.uniform(-0.5, 0.5)
            if nearest_threat and nearest_threat_dist < 80:
                snake.target_angle = angle_to(head, nearest_threat.head)
                snake.boosting = True
                snake.use_ability(AbilityType.DASH)
            return

        best_food      = None
        best_food_dist = 999999
        search_radius  = 400 if snake.personality == AIPersonality.COLLECTOR else 250
        for food in foods:
            if not food.active:
                continue
            d = dist(head, (food.x, food.y))
            if d < search_radius and d < best_food_dist:
                best_food_dist = d
                best_food = food

        best_coin      = None
        best_coin_dist = 999999
        for coin in coins:
            if not coin.active:
                continue
            d = dist(head, (coin.x, coin.y))
            if d < 300 and d < best_coin_dist:
                best_coin_dist = d
                best_coin = coin

        best_pu      = None
        best_pu_dist = 999999
        for pu in powerups:
            if not pu.active:
                continue
            d = dist(head, (pu.x, pu.y))
            if d < 350 and d < best_pu_dist:
                best_pu_dist = d
                best_pu = pu

        if best_pu and best_pu_dist < 200:
            snake.target_angle = angle_to(head, (best_pu.x, best_pu.y))
            snake.boosting = best_pu_dist < 100
            snake.ai_state = "powerup"
        elif best_coin and best_coin_dist < 150:
            snake.target_angle = angle_to(head, (best_coin.x, best_coin.y))
            snake.boosting = False
            snake.ai_state = "coin"
        elif best_food:
            snake.target_angle = angle_to(head, (best_food.x, best_food.y))
            snake.boosting = False
            snake.ai_state = "food"
        else:
            if random.random() < 0.3:
                snake.target_angle = angle_to(head, zone_center) + random.uniform(-1.5, 1.5)
            else:
                snake.target_angle += random.uniform(-0.8, 0.8)
            snake.boosting = False
            snake.ai_state = "wander"

        if not snake.magnet_active and best_food and best_food_dist < 150:
            if random.random() < 0.02 * snake.intelligence:
                snake.use_ability(AbilityType.MAGNET)

        if nearest_threat and nearest_threat_dist < 100 and not snake.shield_active:
            if random.random() < 0.05 * snake.intelligence:
                snake.use_ability(AbilityType.SHIELD)

# ============================================================
# REGION: K.O. EFFECT
# ============================================================

class KOEffect:
    def __init__(self, x: float, y: float, killer_name: str, victim_name: str):
        self.x = x
        self.y = y
        self.killer_name = killer_name
        self.victim_name = victim_name
        self.timer: float = CFG.KO_DURATION
        self.max_timer: float = CFG.KO_DURATION
        self.scale: float = 0
        self.rotation: float = random.uniform(-30, 30)
        self.active: bool = True

    def update(self, dt: float):
        self.timer -= dt
        if self.timer <= 0:
            self.active = False
            return
        t = 1.0 - (self.timer / self.max_timer)
        if t < 0.2:
            self.scale = ease_out_cubic(t / 0.2) * 2.0
        elif t < 0.7:
            self.scale = 2.0
        else:
            self.scale = 2.0 * (1.0 - ease_out_cubic((t - 0.7) / 0.3))
        self.rotation *= 0.95

    def draw(self, surface, camera, fonts):
        if not self.active:
            return
        sx, sy = camera.world_to_screen(self.x, self.y)
        if not (-200 < sx < CFG.SCREEN_WIDTH + 200 and -200 < sy < CFG.SCREEN_HEIGHT + 200):
            return
        font = fonts.get('ko', None)
        if font is None:
            return
        ko_surf  = font.render("K.O.!", True, Colors.RED)
        scaled_w = int(ko_surf.get_width()  * self.scale)
        scaled_h = int(ko_surf.get_height() * self.scale)
        if scaled_w > 0 and scaled_h > 0:
            scaled  = pygame.transform.scale(ko_surf, (scaled_w, scaled_h))
            rotated = pygame.transform.rotate(scaled, self.rotation)
            rect    = rotated.get_rect(center=(sx, sy - 30))
            alpha   = int(200 * min(1, self.scale))
            glow    = pygame.Surface((rotated.get_width() + 20, rotated.get_height() + 20), pygame.SRCALPHA)
            pygame.draw.rect(glow, (255, 0, 0, alpha // 3),
                             (0, 0, glow.get_width(), glow.get_height()), border_radius=10)
            surface.blit(glow, (rect.x - 10, rect.y - 10))
            surface.blit(rotated, rect)

# ============================================================
# REGION: ZONE SYSTEM
# ============================================================

class ZoneSystem:
    def __init__(self):
        self.center: Tuple[float, float] = (0, 0)
        self.radius: float = CFG.WORLD_SIZE / 2 - 100
        self.target_radius: float = self.radius
        self.shrink_timer: float = CFG.SHRINK_INTERVAL
        self.phase: int = 0
        self.warning: bool = False
        self.warning_timer: float = 0
        self.shrink_speed: float = 50.0

    def update(self, dt: float, alive_count: int):
        self.shrink_timer -= dt
        if self.shrink_timer <= 0 and self.radius > CFG.MIN_ZONE_RADIUS:
            self.phase += 1
            shrink = CFG.SHRINK_AMOUNT + self.phase * 50
            self.target_radius = max(CFG.MIN_ZONE_RADIUS, self.radius - shrink)
            self.shrink_timer  = max(10, CFG.SHRINK_INTERVAL - self.phase * 3)
            self.warning       = True
            self.warning_timer = 3.0
            shift = min(100, self.phase * 20)
            self.center = (
                self.center[0] + random.uniform(-shift, shift),
                self.center[1] + random.uniform(-shift, shift)
            )
        if self.warning_timer > 0:
            self.warning_timer -= dt
            if self.warning_timer <= 0:
                self.warning = False
        if self.radius > self.target_radius:
            self.radius -= self.shrink_speed * dt
            self.radius = max(self.target_radius, self.radius)

    def draw(self, surface, camera):
        sx, sy = camera.world_to_screen(*self.center)
        r = int(self.radius * camera.zoom)
        if r > 2:
            t = time.time()
            pulse_r = r + int(math.sin(t * 3) * 5)
            pygame.draw.circle(surface, Colors.ZONE_BORDER, (sx, sy),
                               pulse_r, max(2, int(3 * camera.zoom)))
            if self.warning:
                warn_surf = pygame.Surface((CFG.SCREEN_WIDTH, CFG.SCREEN_HEIGHT), pygame.SRCALPHA)
                pygame.draw.circle(warn_surf, (*Colors.ZONE_WARNING[:3], 30),
                                   (sx, sy), pulse_r + 20, max(10, int(20 * camera.zoom)))
                surface.blit(warn_surf, (0, 0))

# ============================================================
# REGION: SHOP & COSMETICS
# ============================================================

@dataclass
class CosmeticItem:
    name: str
    category: str
    rarity: Rarity
    cost_coins: int = 0
    cost_diamonds: int = 0
    unlocked: bool = False
    equipped: bool = False
    color: Tuple[int,...] = (255, 255, 255)
    description: str = ""

class ShopSystem:
    def __init__(self):
        self.items: List[CosmeticItem] = []
        self.categories = ["Skins", "Hats", "Trails", "Eyes", "Auras", "Abilities"]
        self.selected_category: int = 0
        self.scroll_offset: float = 0
        self.selected_item: int = 0
        self._generate_items()

    def _generate_items(self):
        skin_names  = ["Crimson Viper","Ocean Blue","Forest Dweller","Solar Flare",
                       "Void Walker","Crystal Ice","Neon Pink","Golden King",
                       "Shadow Assassin","Electric Storm","Lava Flow","Arctic Frost"]
        hat_names   = ["Crown","Top Hat","Viking Helm","Wizard Hat",
                       "Pirate Hat","Ninja Band","Angel Halo","Devil Horns"]
        trail_names = ["Fire Trail","Ice Trail","Rainbow Trail","Star Trail",
                       "Smoke Trail","Lightning Trail","Pixel Trail","Galaxy Trail"]
        eye_names   = ["Laser Eyes","Heart Eyes","Star Eyes","Diamond Eyes",
                       "Flame Eyes","Ice Eyes","Robot Eyes","Cat Eyes"]
        aura_names  = ["Fire Aura","Ice Aura","Dark Aura","Light Aura",
                       "Electric Aura","Nature Aura","Void Aura","Crystal Aura"]
        rarities    = [Rarity.COMMON, Rarity.RARE, Rarity.EPIC, Rarity.MYTHIC, Rarity.LEGENDARY]
        rarity_costs = {
            Rarity.COMMON:    (50, 0),
            Rarity.RARE:     (200, 0),
            Rarity.EPIC:     (500, 5),
            Rarity.MYTHIC:   (0, 20),
            Rarity.LEGENDARY:(0, 50),
        }
        for i, name in enumerate(skin_names):
            r = rarities[min(i // 3, 4)]
            cc, cd = rarity_costs[r]
            self.items.append(CosmeticItem(name, "Skins", r, cc, cd,
                color=Colors.SNAKE_PALETTES[i % len(Colors.SNAKE_PALETTES)][0],
                description=f"A {r.name.lower()} snake skin"))
        for lst, cat in [(hat_names,"Hats"),(trail_names,"Trails"),
                         (eye_names,"Eyes"),(aura_names,"Auras")]:
            for i, name in enumerate(lst):
                r = rarities[min(i // 2, 4)]
                cc, cd = rarity_costs[r]
                self.items.append(CosmeticItem(name, cat, r, cc, cd,
                    description=f"A {r.name.lower()} {cat[:-1].lower()}"))

    def get_items_in_category(self, cat: str) -> List[CosmeticItem]:
        return [i for i in self.items if i.category == cat]

    def rarity_color(self, rarity: Rarity) -> Tuple[int,...]:
        return {
            Rarity.COMMON:   (180, 180, 180),
            Rarity.RARE:     (80, 140, 255),
            Rarity.EPIC:     (180, 60, 255),
            Rarity.MYTHIC:   (255, 60, 120),
            Rarity.LEGENDARY:(255, 200, 40),
        }.get(rarity, Colors.WHITE)

# ============================================================
# REGION: STATS TRACKER
# ============================================================

class StatsTracker:
    def __init__(self):
        self.total_wins: int = 0
        self.total_kills: int = 0
        self.total_coins: int = 0
        self.total_diamonds: int = 0
        self.total_damage: float = 0
        self.longest_survival: float = 0
        self.games_played: int = 0
        self.abilities_used: int = 0
        self.current_survival: float = 0
        self.best_kill_streak: int = 0

    def to_dict(self):
        return {
            'wins':     self.total_wins,
            'kills':    self.total_kills,
            'coins':    self.total_coins,
            'diamonds': self.total_diamonds,
            'games':    self.games_played,
            'survival': self.longest_survival,
        }

# ============================================================
# REGION: KILL FEED
# ============================================================

@dataclass
class KillFeedEntry:
    killer: str
    victim: str
    timer: float = 5.0
    color: Tuple[int,...] = Colors.WHITE

class KillFeed:
    def __init__(self, max_entries: int = 6):
        self.entries: List[KillFeedEntry] = []
        self.max_entries = max_entries

    def add(self, killer: str, victim: str, color=Colors.WHITE):
        self.entries.append(KillFeedEntry(killer, victim, 5.0, color))
        if len(self.entries) > self.max_entries:
            self.entries.pop(0)

    def update(self, dt: float):
        for e in self.entries:
            e.timer -= dt
        self.entries = [e for e in self.entries if e.timer > 0]

    def draw(self, surface, fonts):
        x    = CFG.SCREEN_WIDTH - 10
        y    = 80
        font = fonts.get('small', None)
        if not font:
            return
        for e in self.entries:
            text      = f"{e.killer} eliminated {e.victim}"
            text_surf = font.render(text, True, e.color[:3])
            tw        = text_surf.get_width()
            surface.blit(text_surf, (x - tw, y))
            y += 22

# ============================================================
# REGION: FLOATING TEXT
# ============================================================

@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: Tuple[int,...] = Colors.WHITE
    timer: float = 1.5
    max_timer: float = 1.5
    vy: float = -40
    size: int = 20

class FloatingTextManager:
    def __init__(self):
        self.texts: List[FloatingText] = []

    def add(self, x, y, text, color=Colors.WHITE, duration=1.5, size=20):
        self.texts.append(FloatingText(x, y, text, color, duration, duration, -40, size))

    def update(self, dt):
        for t in self.texts:
            t.timer -= dt
            t.y     += t.vy * dt
            t.vy    *= 0.98
        self.texts = [t for t in self.texts if t.timer > 0]

    def draw(self, surface, camera, fonts):
        font = fonts.get('small', None)
        if not font:
            return
        for t in self.texts:
            sx, sy = camera.world_to_screen(t.x, t.y)
            if -50 < sx < CFG.SCREEN_WIDTH + 50 and -50 < sy < CFG.SCREEN_HEIGHT + 50:
                draw_text(surface, t.text, int(sx), int(sy), font, t.color, center=True)

# ============================================================
# REGION: GAME WORLD
# ============================================================

class GameWorld:
    def __init__(self, game_mode: GameMode = GameMode.BATTLE_ROYALE):
        self.game_mode = game_mode
        self.foods: List[Food] = []
        self.coins: List[Coin] = []
        self.powerups: List[PowerUp] = []
        self.snakes: List[Snake] = []
        self.player: Optional[Snake] = None
        self.zone = ZoneSystem()
        self.spatial_grid = SpatialGrid(CFG.GRID_CELL_SIZE)
        self.food_grid    = SpatialGrid(CFG.GRID_CELL_SIZE)
        self.ai_controller = AIController()
        self.particles = ParticleSystem(CFG.PARTICLE_POOL_SIZE)
        self.ko_effects: List[KOEffect] = []
        self.kill_feed = KillFeed()
        self.floating_texts = FloatingTextManager()
        self.match_timer: float = 0
        self.alive_count: int = 0
        self.game_over: bool = False
        self.winner: Optional[Snake] = None
        self.spectating_index: int = 0
        self.leaderboard: List[Snake] = []
        self.events: List[str] = []
        self.event_timer: float = 0

    def init_match(self):
        Snake._id_counter = 0
        self.snakes.clear()
        self.foods.clear()
        self.coins.clear()
        self.powerups.clear()
        self.ko_effects.clear()
        self.kill_feed      = KillFeed()
        self.floating_texts = FloatingTextManager()
        self.match_timer    = 0
        self.game_over      = False
        self.winner         = None
        self.zone           = ZoneSystem()

        px, py = random_position(500)
        self.player = Snake(px, py, is_player=True, name="YOU")
        self.player.color1 = (80, 200, 255)
        self.player.color2 = (40, 140, 200)
        self.snakes.append(self.player)

        names = ["Viper","Cobra","Python","Mamba","Anaconda","Rattler","Boa","Adder",
                 "Sidewinder","Copperhead","Taipan","Krait","Bushmaster","Fer-de-lance",
                 "Asp","Racer","Kingsnake","Milksnake","Cottonmouth","Boomslang",
                 "Stiletto","Bandit","Shadow","Blaze","Frost","Storm","Thunder",
                 "Ghost","Phantom","Specter","Wraith","Ninja","Samurai","Viking",
                 "Knight","Wizard","Rogue","Titan","Atlas","Zeus","Apollo","Athena",
                 "Hydra","Dragon","Phoenix","Griffin","Cerberus","Kraken","Leviathan",
                 "Cyclops","Minotaur","Sphinx","Chimera","Medusa","Pegasus","Fenrir",
                 "Odin","Thor","Loki","Freya"]

        for i in range(CFG.NUM_AI_SNAKES):
            while True:
                ax, ay = random_position(500)
                if dist((ax, ay), (px, py)) > 300:
                    break
            name  = names[i % len(names)] if i < len(names) else f"Bot_{i+1}"
            snake = Snake(ax, ay, is_player=False, name=name)
            for _ in range(random.randint(0, 8)):
                snake.grow()
            self.snakes.append(snake)

        self._spawn_foods(CFG.FOOD_COUNT)
        self._spawn_coins(CFG.COIN_COUNT)
        self._spawn_powerups(CFG.POWERUP_COUNT)
        self.alive_count = len(self.snakes)

    def _spawn_foods(self, count: int):
        for _ in range(count):
            x, y  = random_position(200)
            color = random.choice([Colors.RED, Colors.GREEN, Colors.BLUE,
                                   Colors.YELLOW, Colors.ORANGE, Colors.CYAN,
                                   Colors.PINK, Colors.PURPLE])
            size  = random.uniform(3, 6)
            value = int(size / 2)
            self.foods.append(Food(x, y, size, color, max(1, value), True, random.uniform(0, 6.28)))

    def _spawn_coins(self, count: int):
        for _ in range(count):
            x, y = random_position(300)
            self.coins.append(Coin(x, y, random.choice([1,1,1,2,5]), True, random.uniform(0, 6.28)))

    def _spawn_powerups(self, count: int):
        types = list(PowerUpType)
        for _ in range(count):
            x, y = random_position(400)
            self.powerups.append(PowerUp(x, y, random.choice(types), True,
                                         random.uniform(6, 12), random.uniform(0, 6.28)))

    def update(self, dt: float, player_input: dict):
        if self.game_over:
            return

        self.match_timer += dt
        self.event_timer -= dt

        self.zone.update(dt, self.alive_count)

        if self.player and self.player.alive:
            if player_input.get('mouse_angle') is not None:
                self.player.target_angle = player_input['mouse_angle']
            self.player.boosting = player_input.get('boost', False)
            if player_input.get('dash'):     self.player.use_ability(AbilityType.DASH)
            if player_input.get('shield'):   self.player.use_ability(AbilityType.SHIELD)
            if player_input.get('ghost'):    self.player.use_ability(AbilityType.GHOST)
            if player_input.get('magnet'):   self.player.use_ability(AbilityType.MAGNET)
            if player_input.get('teleport'): self.player.use_ability(AbilityType.TELEPORT)
            if player_input.get('freeze'):   self.player.use_ability(AbilityType.FREEZE_PULSE)
            if player_input.get('poison'):   self.player.use_ability(AbilityType.POISON_TRAIL)

        self.spatial_grid.clear()
        self.food_grid.clear()
        for snake in self.snakes:
            if snake.alive:
                self.spatial_grid.insert(snake, snake.x, snake.y)
                for i, seg in enumerate(snake.segments):
                    if i > 2 and i % 3 == 0:
                        self.spatial_grid.insert(('seg', snake, i), seg[0], seg[1])
        for food in self.foods:
            if food.active:
                self.food_grid.insert(food, food.x, food.y)

        alive_snakes = [s for s in self.snakes if s.alive]
        for snake in self.snakes:
            if not snake.is_player and snake.alive:
                self.ai_controller.update(snake, alive_snakes, self.foods, self.coins,
                                          self.powerups, self.zone.center, self.zone.radius, dt)

        for snake in self.snakes:
            snake.update(dt, self.zone.center, self.zone.radius)

        self._check_collisions(dt)
        self._check_food_collection()
        self._check_coin_collection()
        self._check_powerup_collection()
        self._handle_magnet_effect(dt)
        self._respawn_collectibles()

        self.particles.update(dt)
        self.kill_feed.update(dt)
        self.floating_texts.update(dt)
        for ko in self.ko_effects:
            ko.update(dt)
        self.ko_effects = [ko for ko in self.ko_effects if ko.active]

        self.alive_count = sum(1 for s in self.snakes if s.alive)
        self.leaderboard = sorted([s for s in self.snakes if s.alive],
                                  key=lambda s: s.score + s.length * 10, reverse=True)

        if self.alive_count <= 1:
            self.game_over = True
            alive = [s for s in self.snakes if s.alive]
            if alive:
                self.winner = alive[0]

        for snake in self.snakes:
            if not snake.alive and not snake.death_particles_spawned:
                snake.death_particles_spawned = True
                for seg in snake.segments[:20]:
                    self.particles.emit(seg[0], seg[1], 0, 0, snake.color1,
                                        life=1.5, size=5, count=3, spread=80)
                for seg in snake.segments[::3]:
                    if len(self.foods) < 2000:
                        self.foods.append(Food(
                            seg[0] + random.uniform(-10, 10),
                            seg[1] + random.uniform(-10, 10),
                            random.uniform(4, 8), snake.color1, 2, True))

        if self.game_mode == GameMode.CHAOS and self.event_timer <= 0:
            self._trigger_random_event()
            self.event_timer = random.uniform(10, 30)

    def _check_collisions(self, dt: float):
        alive_snakes = [s for s in self.snakes if s.alive]
        for snake in alive_snakes:
            if snake.ghost_active:
                continue
            head   = snake.head
            nearby = self.spatial_grid.query(head[0], head[1], 50)
            for obj in nearby:
                if isinstance(obj, Snake):
                    if obj.id == snake.id or not obj.alive or obj.ghost_active:
                        continue
                    if dist(head, obj.head) < snake.get_radius() + obj.get_radius():
                        if snake.length > obj.length:
                            if not obj.shield_active:
                                self._kill_snake(obj, snake)
                        elif obj.length > snake.length:
                            if not snake.shield_active:
                                self._kill_snake(snake, obj)
                        else:
                            if not snake.shield_active:
                                self._kill_snake(snake, obj)
                            if not obj.shield_active:
                                self._kill_snake(obj, snake)
                elif isinstance(obj, tuple) and obj[0] == 'seg':
                    _, seg_snake, seg_idx = obj
                    if seg_snake.id == snake.id or not seg_snake.alive or seg_snake.ghost_active:
                        continue
                    seg_pos = seg_snake.segments[seg_idx]
                    if dist(head, seg_pos) < snake.get_radius() + CFG.SEGMENT_SIZE * 0.6:
                        if not snake.shield_active:
                            self._kill_snake(snake, seg_snake)

            for other in alive_snakes:
                if other.id == snake.id:
                    continue
                for tx, ty, tt in other.poison_trail:
                    if dist(head, (tx, ty)) < 15:
                        snake.take_damage(0.5 * 60 * dt)

    def _kill_snake(self, victim: Snake, killer: Snake):
        if not victim.alive:
            return
        victim.alive = False
        killer.kills += 1
        killer.score += 50 + victim.length * 5
        killer.add_xp(30 + victim.length * 2)
        killer.grow(max(1, victim.length // 5))
        self.ko_effects.append(KOEffect(victim.x, victim.y, killer.name, victim.name))
        self.kill_feed.add(killer.name, victim.name,
                           Colors.GOLD if killer.is_player else Colors.WHITE)
        self.floating_texts.add(victim.x, victim.y - 20, f"-{victim.name}", Colors.RED, 2.0)
        self.floating_texts.add(killer.x, killer.y - 30,
                                f"+{50 + victim.length * 5}", Colors.GOLD, 1.5)
        self.particles.emit(victim.x, victim.y, 0, 0, Colors.RED,
                            life=1.0, size=6, count=30, spread=150)

    def _check_food_collection(self):
        for snake in [s for s in self.snakes if s.alive]:
            cr = 20 + (10 if snake.magnet_active else 0)
            for food in self.foods:
                if not food.active:
                    continue
                if dist_sq(snake.head, (food.x, food.y)) < cr * cr:
                    food.active = False
                    snake.score += food.value * int(snake.score_multiplier)
                    snake.add_xp(food.value)
                    if random.random() < 0.3:
                        snake.grow()
                    if snake.is_player:
                        self.particles.emit(food.x, food.y, 0, -20, food.color,
                                            life=0.5, size=3, count=5, spread=30)

    def _check_coin_collection(self):
        for snake in [s for s in self.snakes if s.alive]:
            for coin in self.coins:
                if not coin.active:
                    continue
                if dist_sq(snake.head, (coin.x, coin.y)) < 25 * 25:
                    coin.active = False
                    snake.coins_collected += coin.value
                    snake.score += coin.value * 5
                    if snake.is_player:
                        self.floating_texts.add(coin.x, coin.y - 15,
                                                f"+{coin.value} Coin", Colors.GOLD, 1.0)
                        self.particles.emit(coin.x, coin.y, 0, -30, Colors.GOLD,
                                            life=0.8, size=4, count=8, spread=40)

    def _check_powerup_collection(self):
        for snake in [s for s in self.snakes if s.alive]:
            for pu in self.powerups:
                if not pu.active:
                    continue
                if dist_sq(snake.head, (pu.x, pu.y)) < 30 * 30:
                    pu.active = False
                    self._apply_powerup(snake, pu)

    def _apply_powerup(self, snake: Snake, pu: PowerUp):
        if pu.type == PowerUpType.SPEED:
            snake.speed_boost_timer = pu.duration;  txt = "SPEED UP!"
        elif pu.type == PowerUpType.SHIELD:
            snake.shield_active = True;  snake.shield_timer = pu.duration;  txt = "SHIELD!"
        elif pu.type == PowerUpType.MAGNET:
            snake.magnet_active = True;  snake.magnet_timer = pu.duration;  txt = "MAGNET!"
        elif pu.type == PowerUpType.GHOST:
            snake.ghost_active  = True;  snake.ghost_timer  = pu.duration;  txt = "GHOST!"
        elif pu.type == PowerUpType.GROWTH:
            snake.grow(5);  txt = "GROWTH!"
        elif pu.type == PowerUpType.SCORE_MULT:
            snake.score_multiplier = 2.0;  snake.score_mult_timer = pu.duration;  txt = "2X SCORE!"
        else:
            txt = "POWER UP!"
        if snake.is_player:
            self.floating_texts.add(snake.x, snake.y - 30, txt, Colors.CYAN, 1.5, 24)
        self.particles.emit(pu.x, pu.y, 0, 0, Colors.CYAN, life=1.0, size=5, count=15, spread=60)

    def _handle_magnet_effect(self, dt: float):
        for snake in self.snakes:
            if not snake.alive or not snake.magnet_active:
                continue
            for food in self.foods:
                if not food.active:
                    continue
                d = dist(snake.head, (food.x, food.y))
                if 5 < d < 150:
                    a    = angle_to((food.x, food.y), snake.head)
                    pull = 200 * dt
                    food.x += math.cos(a) * pull
                    food.y += math.sin(a) * pull

    def _respawn_collectibles(self):
        if sum(1 for f in self.foods if f.active) < CFG.FOOD_COUNT * 0.5:
            for _ in range(50):
                x, y = random_position(300)
                if dist((x, y), self.zone.center) < self.zone.radius - 50:
                    color = random.choice([Colors.RED, Colors.GREEN, Colors.BLUE,
                                           Colors.YELLOW, Colors.ORANGE])
                    self.foods.append(Food(x, y, random.uniform(3, 6), color,
                                           random.randint(1, 3), True))
        if sum(1 for c in self.coins if c.active) < CFG.COIN_COUNT * 0.3:
            for _ in range(10):
                x, y = random_position(300)
                if dist((x, y), self.zone.center) < self.zone.radius - 50:
                    self.coins.append(Coin(x, y, random.choice([1, 1, 2]), True))
        if sum(1 for p in self.powerups if p.active) < 10:
            for _ in range(5):
                x, y = random_position(400)
                if dist((x, y), self.zone.center) < self.zone.radius - 50:
                    self.powerups.append(PowerUp(x, y, random.choice(list(PowerUpType)), True))

    def _trigger_random_event(self):
        event = random.choice(["meteor", "food_rain", "speed_all", "shrink_fast"])
        if event == "meteor":
            x, y = random_position(500)
            for snake in self.snakes:
                if snake.alive and dist(snake.head, (x, y)) < 200:
                    snake.take_damage(30)
            self.particles.emit(x, y, 0, 0, Colors.ORANGE, life=2.0, size=8, count=50, spread=200)
        elif event == "food_rain":
            for _ in range(100):
                x, y = random_position(300)
                self.foods.append(Food(x, y, random.uniform(4, 8), Colors.GOLD, 3, True))
        elif event == "speed_all":
            for snake in self.snakes:
                if snake.alive:
                    snake.speed_boost_timer = 5.0
        elif event == "shrink_fast":
            self.zone.target_radius = max(CFG.MIN_ZONE_RADIUS, self.zone.radius - 200)

# ============================================================
# REGION: RENDERER
# ============================================================

class Renderer:
    def __init__(self, screen: pygame.Surface, fonts: dict, skin_mgr: SkinManager):
        self.screen   = screen
        self.fonts    = fonts
        self.skin_mgr = skin_mgr
        self.t        = 0

    def render_game(self, world: GameWorld, camera: Camera,
                    game_state: GameState, player_skin_id: int = 0):
        self.t = time.time()
        self.screen.fill(Colors.DARK_BG)
        self._draw_grid(camera)
        world.zone.draw(self.screen, camera)
        self._draw_foods(world.foods, camera)
        self._draw_coins(world.coins, camera)
        self._draw_powerups(world.powerups, camera)
        for snake in world.snakes:
            if snake.alive:
                self._draw_poison_trail(snake, camera)
        for snake in world.snakes:
            if snake.alive:
                self._draw_snake(snake, camera, player_skin_id)
        # Draw cosmic sparkles on top of all snakes
        if player_skin_id == 3:
            self.skin_mgr.draw_sparkles(self.screen)
        world.particles.draw(self.screen, camera)
        for ko in world.ko_effects:
            ko.draw(self.screen, camera, self.fonts)
        world.floating_texts.draw(self.screen, camera, self.fonts)
        self._draw_hud(world, camera, game_state)

    # ------------------------------------------------------------------
    def _draw_grid(self, camera: Camera):
        grid_spacing = 100
        tl = camera.screen_to_world(0, 0)
        br = camera.screen_to_world(CFG.SCREEN_WIDTH, CFG.SCREEN_HEIGHT)
        start_x = int(tl[0] // grid_spacing) * grid_spacing
        end_x   = int(br[0] // grid_spacing + 1) * grid_spacing
        start_y = int(tl[1] // grid_spacing) * grid_spacing
        end_y   = int(br[1] // grid_spacing + 1) * grid_spacing
        half    = CFG.WORLD_SIZE // 2
        for x in range(start_x, end_x + grid_spacing, grid_spacing):
            if -half <= x <= half:
                sx1, sy1 = camera.world_to_screen(x, max(-half, tl[1]))
                sx2, sy2 = camera.world_to_screen(x, min(half, br[1]))
                pygame.draw.line(self.screen, Colors.GRID_COLOR, (sx1, sy1), (sx2, sy2), 1)
        for y in range(start_y, end_y + grid_spacing, grid_spacing):
            if -half <= y <= half:
                sx1, sy1 = camera.world_to_screen(max(-half, tl[0]), y)
                sx2, sy2 = camera.world_to_screen(min(half, br[0]), y)
                pygame.draw.line(self.screen, Colors.GRID_COLOR, (sx1, sy1), (sx2, sy2), 1)
        corners = [(-half,-half),(half,-half),(half,half),(-half,half)]
        pygame.draw.lines(self.screen, (60,60,80), True,
                          [camera.world_to_screen(*c) for c in corners], 2)

    def _draw_foods(self, foods: List[Food], camera: Camera):
        for food in foods:
            if not food.active or not camera.is_visible(food.x, food.y, 20):
                continue
            sx, sy = camera.world_to_screen(food.x, food.y)
            p      = pulse(self.t + food.pulse_offset, 1.5)
            size   = max(1, int((food.size + p * 2) * camera.zoom))
            pygame.draw.circle(self.screen, food.color, (sx, sy), size)
            if camera.zoom > 0.6:
                pygame.draw.circle(self.screen, food.color[:3], (sx, sy), size + 2, 1)

    def _draw_coins(self, coins: List[Coin], camera: Camera):
        for coin in coins:
            if not coin.active or not camera.is_visible(coin.x, coin.y, 30):
                continue
            sx, sy = camera.world_to_screen(coin.x, coin.y)
            p      = pulse(self.t + coin.pulse_offset, 2.0)
            size   = max(2, int((8 + p * 3) * camera.zoom))
            pygame.draw.circle(self.screen, Colors.GOLD,   (sx, sy), size)
            pygame.draw.circle(self.screen, Colors.YELLOW, (sx, sy), max(1, size - 2))
            if camera.zoom > 0.5 and size > 4:
                tiny = self.fonts.get('tiny')
                if tiny:
                    draw_text(self.screen, "$", sx, sy, tiny, Colors.ORANGE,
                              center=True, shadow=False)

    def _draw_powerups(self, powerups: List[PowerUp], camera: Camera):
        pu_colors  = {
            PowerUpType.SPEED:      Colors.YELLOW,
            PowerUpType.SHIELD:     Colors.CYAN,
            PowerUpType.MAGNET:     Colors.PURPLE,
            PowerUpType.GHOST:      (200,200,200),
            PowerUpType.GROWTH:     Colors.GREEN,
            PowerUpType.SCORE_MULT: Colors.GOLD,
        }
        pu_symbols = {
            PowerUpType.SPEED:      ">>",
            PowerUpType.SHIELD:     "O",
            PowerUpType.MAGNET:     "M",
            PowerUpType.GHOST:      "G",
            PowerUpType.GROWTH:     "+",
            PowerUpType.SCORE_MULT: "x2",
        }
        for pu in powerups:
            if not pu.active or not camera.is_visible(pu.x, pu.y, 40):
                continue
            sx, sy = camera.world_to_screen(pu.x, pu.y)
            color  = pu_colors.get(pu.type, Colors.WHITE)
            p      = pulse(self.t + pu.pulse_offset, 1.0)
            size   = max(3, int((12 + p * 4) * camera.zoom))
            points = [(sx, sy-size),(sx+size, sy),(sx, sy+size),(sx-size, sy)]
            pygame.draw.polygon(self.screen, color,        points)
            pygame.draw.polygon(self.screen, Colors.WHITE, points, max(1, int(2*camera.zoom)))
            if camera.zoom > 0.5:
                tiny = self.fonts.get('tiny')
                if tiny:
                    draw_text(self.screen, pu_symbols.get(pu.type,"?"),
                              sx, sy, tiny, Colors.WHITE, center=True, shadow=False)

    def _draw_poison_trail(self, snake: Snake, camera: Camera):
        for tx, ty, tt in snake.poison_trail:
            if camera.is_visible(tx, ty, 20):
                sx, sy = camera.world_to_screen(tx, ty)
                alpha  = min(1.0, tt / 2.0)
                size   = max(1, int(6 * alpha * camera.zoom))
                color  = lerp_color((40,200,40), (0,80,0), 1.0 - alpha)
                pygame.draw.circle(self.screen, color, (sx, sy), size)

    def _draw_snake(self, snake: Snake, camera: Camera, player_skin_id: int = 0):
        if not snake.alive:
            return
        if not camera.is_visible(snake.x, snake.y, 200 + len(snake.segments) * 2):
            any_vis = any(
                camera.is_visible(snake.segments[i][0], snake.segments[i][1], 50)
                for i in range(0, len(snake.segments), max(1, len(snake.segments)//5))
            )
            if not any_vis:
                return

        use_skin   = snake.is_player
        skin_id    = player_skin_id if use_skin else -1
        seg_count  = len(snake.segments)

        for i in range(seg_count - 1, -1, -1):
            sx, sy = camera.world_to_screen(snake.segments[i][0], snake.segments[i][1])
            if not (-30 < sx < CFG.SCREEN_WIDTH + 30 and -30 < sy < CFG.SCREEN_HEIGHT + 30):
                continue

            radius = max(2, int((snake.head_size - (i / max(1, seg_count-1)) * 3) * camera.zoom))

            if use_skin:
                # Use premium skin renderer for the player
                self.skin_mgr.draw_segment(self.screen, (sx, sy), radius, i, skin_id)
            else:
                # Standard renderer for AI snakes
                t     = i / max(1, seg_count - 1)
                color = lerp_color(snake.color2, snake.color1, 1.0 - t)
                if i % 4 < 2:
                    color = lerp_color(color, Colors.WHITE, 0.15)
                if snake.ghost_active:
                    color = lerp_color(color, Colors.WHITE, 0.5)
                    if i % 2 == 0:
                        continue
                pygame.draw.circle(self.screen, color, (sx, sy), radius)
                if camera.zoom > 0.5:
                    darker = tuple(max(0, c - 40) for c in color)
                    pygame.draw.circle(self.screen, darker, (sx, sy), radius,
                                       max(1, int(camera.zoom)))

        # Head
        hx, hy = camera.world_to_screen(snake.x, snake.y)
        head_r  = max(3, int(snake.head_size * camera.zoom * 1.2))

        if use_skin:
            self.skin_mgr.draw_head(self.screen, (hx, hy), head_r, snake.angle, skin_id)
        else:
            pygame.draw.circle(self.screen, snake.color1, (hx, hy), head_r)
            pygame.draw.circle(self.screen, Colors.WHITE,  (hx, hy), head_r,
                               max(1, int(1.5 * camera.zoom)))
            if camera.zoom > 0.4:
                eye_dist  = head_r * 0.4
                eye_size  = max(1, int(head_r * 0.35))
                pupil_size= max(1, int(eye_size * 0.5))
                for side in [-1, 1]:
                    perp = snake.angle + math.pi / 2 * side
                    ex   = int(hx + math.cos(perp)*eye_dist + math.cos(snake.angle)*eye_dist*0.5)
                    ey   = int(hy + math.sin(perp)*eye_dist + math.sin(snake.angle)*eye_dist*0.5)
                    pygame.draw.circle(self.screen, Colors.WHITE, (ex, ey), eye_size)
                    px = ex + int(math.cos(snake.angle) * pupil_size * 0.5)
                    py = ey + int(math.sin(snake.angle) * pupil_size * 0.5)
                    pygame.draw.circle(self.screen, Colors.BLACK, (px, py), pupil_size)

        # Shield ring
        if snake.shield_active:
            p        = pulse(self.t, 3.0)
            shield_r = head_r + 8 + int(p * 4)
            pygame.draw.circle(self.screen, Colors.CYAN, (hx, hy),
                               int(shield_r * camera.zoom), 2)

        # Name tag
        if camera.zoom > 0.3:
            small_font = self.fonts.get('small')
            if small_font:
                name_color = Colors.GOLD if snake.is_player else Colors.WHITE
                draw_text(self.screen, snake.name, hx, hy - head_r - 15,
                          small_font, name_color, center=True)
                if camera.zoom > 0.5:
                    draw_text(self.screen, f"Lv.{snake.level}", hx, hy - head_r - 28,
                              self.fonts.get('tiny', small_font), Colors.XP_PURPLE, center=True)

    # ------------------------------------------------------------------
    def _draw_hud(self, world: GameWorld, camera: Camera, game_state: GameState):
        if game_state == GameState.SPECTATING and world.player and not world.player.alive:
            alive = [s for s in world.snakes if s.alive]
            if alive and world.spectating_index < len(alive):
                target = alive[world.spectating_index]
                draw_text(self.screen, f"Spectating: {target.name}",
                          CFG.SCREEN_WIDTH//2, 30, self.fonts['medium'], Colors.YELLOW, center=True)
                draw_text(self.screen, "← → to switch | ESC to quit",
                          CFG.SCREEN_WIDTH//2, 55, self.fonts['small'], Colors.WHITE, center=True)

        player = world.player
        if player:
            y = 10
            draw_text(self.screen, f"Score: {player.score}", 10, y, self.fonts['medium'], Colors.WHITE)
            y += 28
            draw_text(self.screen, f"Kills: {player.kills}", 10, y, self.fonts['small'], Colors.RED)
            y += 22
            draw_text(self.screen, f"Length: {player.length}", 10, y, self.fonts['small'], Colors.GREEN)
            y += 22
            draw_text(self.screen, f"Level: {player.level}", 10, y, self.fonts['small'], Colors.XP_PURPLE)
            y += 22
            xp_w  = 150; xp_h = 8
            xp_pct = player.xp / max(1, player.xp_to_next)
            pygame.draw.rect(self.screen, Colors.DARK_PANEL2, (10, y, xp_w, xp_h), border_radius=4)
            pygame.draw.rect(self.screen, Colors.XP_PURPLE,
                             (10, y, int(xp_w * xp_pct), xp_h), border_radius=4)
            y += 14
            ep = player.energy / player.max_energy
            pygame.draw.rect(self.screen, Colors.DARK_PANEL2, (10, y, xp_w, xp_h), border_radius=4)
            pygame.draw.rect(self.screen, Colors.YELLOW if ep > 0.3 else Colors.RED,
                             (10, y, int(xp_w * ep), xp_h), border_radius=4)
            y += 14
            hp = player.health / player.max_health
            pygame.draw.rect(self.screen, Colors.DARK_PANEL2, (10, y, xp_w, xp_h), border_radius=4)
            pygame.draw.rect(self.screen, Colors.HEALTH_GREEN if hp > 0.5 else Colors.HEALTH_RED,
                             (10, y, int(xp_w * hp), xp_h), border_radius=4)
            y += 20
            draw_text(self.screen, f"Coins: {player.coins_collected}", 10, y,
                      self.fonts['small'], Colors.GOLD)

        minutes = int(world.match_timer // 60)
        seconds = int(world.match_timer % 60)
        draw_text(self.screen, f"Alive: {world.alive_count}/{len(world.snakes)}",
                  CFG.SCREEN_WIDTH//2, 10, self.fonts['medium'], Colors.WHITE, center=True)
        draw_text(self.screen, f"{minutes:02d}:{seconds:02d}",
                  CFG.SCREEN_WIDTH//2, 35, self.fonts['small'], Colors.YELLOW, center=True)
        if world.zone.warning:
            p = pulse(self.t, 4.0)
            draw_text(self.screen, "⚠ ZONE SHRINKING ⚠",
                      CFG.SCREEN_WIDTH//2, 60, self.fonts['medium'],
                      lerp_color(Colors.RED, Colors.ORANGE, p), center=True)

        self._draw_leaderboard(world)
        self._draw_minimap(world, camera)
        world.kill_feed.draw(self.screen, self.fonts)
        if player and player.alive:
            self._draw_ability_bar(player)
            self._draw_active_effects(player)

    def _draw_leaderboard(self, world: GameWorld):
        x = CFG.SCREEN_WIDTH - 200
        y = 10
        panel = pygame.Surface((190, 220), pygame.SRCALPHA)
        panel.fill((0,0,0,120))
        self.screen.blit(panel, (x-5, y-5))
        draw_text(self.screen, "LEADERBOARD", x+85, y, self.fonts['small'], Colors.GOLD, center=True)
        y += 22
        for i, snake in enumerate(world.leaderboard[:8]):
            if not snake.alive:
                continue
            color      = Colors.GOLD if snake.is_player else Colors.WHITE
            rank_color = [Colors.GOLD,(192,192,192),(205,127,50)][i] if i < 3 else Colors.WHITE
            score      = snake.score + snake.length * 10
            draw_text(self.screen, f"{i+1}. {snake.name[:12]}", x, y, self.fonts['tiny'], rank_color)
            draw_text(self.screen, str(score), x+160, y, self.fonts['tiny'], color)
            y += 20
            if i >= 7:
                break
        if world.player and world.player.alive:
            player_rank = next((i+1 for i, s in enumerate(world.leaderboard)
                                if s.id == world.player.id), 0)
            if player_rank > 8:
                y += 5
                draw_text(self.screen, f"You: #{player_rank}", x, y,
                          self.fonts['tiny'], Colors.GOLD)

    def _draw_minimap(self, world: GameWorld, camera: Camera):
        mm_size = CFG.MINIMAP_SIZE
        mm_x    = CFG.SCREEN_WIDTH  - mm_size - CFG.MINIMAP_MARGIN
        mm_y    = CFG.SCREEN_HEIGHT - mm_size - CFG.MINIMAP_MARGIN
        mm_surf = pygame.Surface((mm_size, mm_size), pygame.SRCALPHA)
        mm_surf.fill((0,0,0,150))
        half  = CFG.WORLD_SIZE / 2
        scale = mm_size / CFG.WORLD_SIZE
        zx    = int((world.zone.center[0] + half) * scale)
        zy    = int((world.zone.center[1] + half) * scale)
        zr    = max(1, int(world.zone.radius * scale))
        pygame.draw.circle(mm_surf, (255,60,60,80), (zx, zy), zr, 1)
        for snake in world.snakes:
            if not snake.alive:
                continue
            sx = int(clamp((snake.x + half) * scale, 0, mm_size-1))
            sy = int(clamp((snake.y + half) * scale, 0, mm_size-1))
            pygame.draw.circle(mm_surf, Colors.CYAN if snake.is_player else snake.color1,
                               (sx, sy), 3 if snake.is_player else 2)
        tl = camera.screen_to_world(0, 0)
        br = camera.screen_to_world(CFG.SCREEN_WIDTH, CFG.SCREEN_HEIGHT)
        rx = int((tl[0] + half) * scale); ry = int((tl[1] + half) * scale)
        rw = int((br[0]-tl[0]) * scale);  rh = int((br[1]-tl[1]) * scale)
        pygame.draw.rect(mm_surf, Colors.WHITE, (rx, ry, rw, rh), 1)
        pygame.draw.rect(mm_surf, Colors.WHITE, (0, 0, mm_size, mm_size), 1)
        self.screen.blit(mm_surf, (mm_x, mm_y))

    def _draw_ability_bar(self, player: Snake):
        abilities_to_show = [
            (AbilityType.DASH,         "Dash",   "Q", Colors.YELLOW),
            (AbilityType.SHIELD,       "Shield", "E", Colors.CYAN),
            (AbilityType.GHOST,        "Ghost",  "R", (200,200,200)),
            (AbilityType.MAGNET,       "Magnet", "F", Colors.PURPLE),
            (AbilityType.TELEPORT,     "Tele",   "T", Colors.BLUE),
            (AbilityType.FREEZE_PULSE, "Freeze", "G", (100,200,255)),
            (AbilityType.POISON_TRAIL, "Poison", "V", Colors.GREEN),
        ]
        bar_y = CFG.SCREEN_HEIGHT - 60
        bar_x = CFG.SCREEN_WIDTH // 2 - len(abilities_to_show) * 30
        tiny  = self.fonts.get('tiny')
        if not tiny:
            return
        for i, (atype, name, key, color) in enumerate(abilities_to_show):
            x  = bar_x + i * 60
            ab = player.abilities.get(atype)
            if not ab:
                continue
            bg_color = Colors.DARK_PANEL if ab.cooldown <= 0 else (40,20,20)
            pygame.draw.rect(self.screen, bg_color, (x, bar_y, 50, 50), border_radius=8)
            if ab.cooldown > 0:
                h = int(50 * ab.cooldown / ab.max_cooldown)
                pygame.draw.rect(self.screen, (60,30,30), (x, bar_y+50-h, 50, h), border_radius=4)
            if ab.active:
                pygame.draw.rect(self.screen, color, (x, bar_y, 50, 50), 2, border_radius=8)
            border_color = color if ab.cooldown <= 0 else (80,80,80)
            pygame.draw.rect(self.screen, border_color, (x, bar_y, 50, 50), 1, border_radius=8)
            draw_text(self.screen, key,  x+25, bar_y+8,  tiny, color,        center=True, shadow=False)
            draw_text(self.screen, name, x+25, bar_y+28, tiny, Colors.WHITE, center=True, shadow=False)
            if ab.cooldown > 0:
                draw_text(self.screen, f"{ab.cooldown:.1f}", x+25, bar_y+42,
                          tiny, Colors.RED, center=True, shadow=False)

    def _draw_active_effects(self, player: Snake):
        effects = []
        if player.shield_active:       effects.append(("SHIELD",   Colors.CYAN,   player.shield_timer))
        if player.ghost_active:        effects.append(("GHOST",    (200,200,200), player.ghost_timer))
        if player.magnet_active:       effects.append(("MAGNET",   Colors.PURPLE, player.magnet_timer))
        if player.speed_boost_timer>0: effects.append(("SPEED",    Colors.YELLOW, player.speed_boost_timer))
        if player.score_multiplier>1:  effects.append(("x2 SCORE", Colors.GOLD,   player.score_mult_timer))
        y = CFG.SCREEN_HEIGHT - 120
        for name, color, timer in effects:
            draw_text(self.screen, f"{name} {timer:.1f}s",
                      CFG.SCREEN_WIDTH//2, y, self.fonts['small'], color, center=True)
            y -= 22

# ============================================================
# REGION: MENU SYSTEM  (unchanged from original)
# ============================================================

class MenuSystem:
    def __init__(self, screen: pygame.Surface, fonts: dict):
        self.screen = screen
        self.fonts  = fonts
        self.menu_bg_particles = []
        self._init_bg_particles()
        self.selected_mode: int = 0
        self.hover_button: int  = -1
        self.t = 0
        self.title_offset = 0

    def _init_bg_particles(self):
        for _ in range(80):
            self.menu_bg_particles.append({
                'x':     random.uniform(0, CFG.SCREEN_WIDTH),
                'y':     random.uniform(0, CFG.SCREEN_HEIGHT),
                'vx':    random.uniform(-20, 20),
                'vy':    random.uniform(-20, 20),
                'size':  random.uniform(1, 4),
                'color': random.choice([Colors.CYAN, Colors.PURPLE, Colors.BLUE,
                                        Colors.GREEN, Colors.YELLOW]),
                'alpha': random.uniform(50, 200),
            })

    def _update_bg_particles(self, dt):
        for p in self.menu_bg_particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            if p['x'] < 0:               p['x'] = CFG.SCREEN_WIDTH
            if p['x'] > CFG.SCREEN_WIDTH: p['x'] = 0
            if p['y'] < 0:                p['y'] = CFG.SCREEN_HEIGHT
            if p['y'] > CFG.SCREEN_HEIGHT:p['y'] = 0

    def _draw_bg(self):
        self.screen.fill(Colors.DARK_BG)
        for p in self.menu_bg_particles:
            pygame.draw.circle(self.screen, p['color'],
                               (int(p['x']), int(p['y'])), max(1, int(p['size'])))
        for i, p1 in enumerate(self.menu_bg_particles):
            for p2 in self.menu_bg_particles[i+1:i+5]:
                d = math.sqrt((p1['x']-p2['x'])**2 + (p1['y']-p2['y'])**2)
                if d < 120:
                    color = lerp_color(p1['color'], p2['color'], 0.5)
                    pygame.draw.line(self.screen, color,
                                     (int(p1['x']),int(p1['y'])),
                                     (int(p2['x']),int(p2['y'])), 1)

    def draw_main_menu(self, dt):
        self.t += dt
        self._update_bg_particles(dt)
        self._draw_bg()
        title_y = 120 + math.sin(self.t * 2) * 10
        draw_text(self.screen, "SLITHER ROYALE", CFG.SCREEN_WIDTH//2, int(title_y),
                  self.fonts['title'], Colors.CYAN, center=True)
        draw_text(self.screen, "AI SNAKE ARENA", CFG.SCREEN_WIDTH//2, int(title_y)+60,
                  self.fonts['large'], Colors.GOLD, center=True)
        draw_text(self.screen, "100 Snakes. 1 Winner. Total Chaos.",
                  CFG.SCREEN_WIDTH//2, int(title_y)+100, self.fonts['small'], Colors.WHITE, center=True)
        buttons = [("PLAY",Colors.GREEN),("GAME MODES",Colors.BLUE),("SHOP",Colors.GOLD),
                   ("CUSTOMIZE",Colors.PURPLE),("STATS",Colors.CYAN),("QUIT",Colors.RED)]
        mx, my = pygame.mouse.get_pos()
        self.hover_button = -1
        button_rects = []
        for i, (text, color) in enumerate(buttons):
            bx = CFG.SCREEN_WIDTH//2 - 120
            by = 320 + i * 55
            bw, bh = 240, 45
            rect = pygame.Rect(bx, by, bw, bh)
            button_rects.append(rect)
            hover = rect.collidepoint(mx, my)
            if hover: self.hover_button = i
            bg_color     = lerp_color(Colors.DARK_PANEL, color, 0.3 if hover else 0.1)
            border_color = color if hover else lerp_color(color, Colors.DARK_PANEL, 0.5)
            if hover:
                pygame.draw.rect(self.screen, bg_color, rect.inflate(4,4), border_radius=12)
            pygame.draw.rect(self.screen, bg_color,     rect, border_radius=10)
            pygame.draw.rect(self.screen, border_color, rect, 2, border_radius=10)
            draw_text(self.screen, text, bx+bw//2, by+bh//2, self.fonts['medium'],
                      Colors.WHITE if hover else color, center=True)
        draw_text(self.screen, "Mouse to aim | SPACE to boost | Q/E/R/F/T/G/V abilities",
                  CFG.SCREEN_WIDTH//2, CFG.SCREEN_HEIGHT-40,
                  self.fonts['tiny'], (120,120,140), center=True)
        return button_rects

    def draw_mode_select(self, dt):
        self.t += dt
        self._update_bg_particles(dt)
        self._draw_bg()
        draw_text(self.screen, "SELECT GAME MODE", CFG.SCREEN_WIDTH//2, 60,
                  self.fonts['large'], Colors.GOLD, center=True)
        modes = [
            ("BATTLE ROYALE",    "100 snakes, last one standing wins!", Colors.RED,    GameMode.BATTLE_ROYALE),
            ("ENDLESS SURVIVAL", "Survive as long as possible!",        Colors.GREEN,  GameMode.ENDLESS),
            ("AI TOURNAMENT",    "Watch AI battle it out!",              Colors.BLUE,   GameMode.TOURNAMENT),
            ("HARDCORE",         "One hit kill, no powerups!",           Colors.ORANGE, GameMode.HARDCORE),
            ("CHAOS MODE",       "Random events, total mayhem!",         Colors.PURPLE, GameMode.CHAOS),
        ]
        mx, my = pygame.mouse.get_pos()
        button_rects = []
        for i, (name, desc, color, mode) in enumerate(modes):
            bx = CFG.SCREEN_WIDTH//2 - 200
            by = 140 + i * 90
            bw, bh = 400, 75
            rect  = pygame.Rect(bx, by, bw, bh)
            button_rects.append((rect, mode))
            hover = rect.collidepoint(mx, my)
            pygame.draw.rect(self.screen, lerp_color(Colors.DARK_PANEL, color, 0.2 if hover else 0.05),
                             rect, border_radius=12)
            pygame.draw.rect(self.screen, color if hover else lerp_color(color, Colors.DARK_PANEL, 0.6),
                             rect, 2, border_radius=12)
            draw_text(self.screen, name, bx+bw//2, by+22, self.fonts['medium'],
                      Colors.WHITE if hover else color, center=True)
            draw_text(self.screen, desc, bx+bw//2, by+50, self.fonts['tiny'],
                      (160,160,180), center=True)
        back_rect = pygame.Rect(20, CFG.SCREEN_HEIGHT-60, 100, 40)
        button_rects.append((back_rect, None))
        hover = back_rect.collidepoint(mx, my)
        pygame.draw.rect(self.screen, Colors.DARK_PANEL if not hover else Colors.RED,
                         back_rect, border_radius=8)
        pygame.draw.rect(self.screen, Colors.RED, back_rect, 1, border_radius=8)
        draw_text(self.screen, "BACK", 70, CFG.SCREEN_HEIGHT-40,
                  self.fonts['small'], Colors.WHITE, center=True)
        return button_rects

    def draw_shop(self, shop: ShopSystem, player_coins: int, player_diamonds: int, dt):
        self.t += dt
        self.screen.fill(Colors.DARK_BG)
        draw_text(self.screen, "SHOP", CFG.SCREEN_WIDTH//2, 30, self.fonts['large'], Colors.GOLD, center=True)
        draw_text(self.screen, f"Coins: {player_coins}",    20, 15, self.fonts['small'], Colors.GOLD)
        draw_text(self.screen, f"Diamonds: {player_diamonds}", 20, 40, self.fonts['small'], Colors.DIAMOND_BLUE)
        tab_x = 40
        tab_rects = []
        mx, my = pygame.mouse.get_pos()
        for i, cat in enumerate(shop.categories):
            tw   = 100
            rect = pygame.Rect(tab_x + i*(tw+10), 70, tw, 35)
            tab_rects.append(rect)
            selected = i == shop.selected_category
            hover    = rect.collidepoint(mx, my)
            color    = Colors.UI_ACCENT if selected else (Colors.UI_HOVER if hover else Colors.DARK_PANEL2)
            pygame.draw.rect(self.screen, color, rect, border_radius=6)
            if not selected:
                pygame.draw.rect(self.screen, Colors.UI_ACCENT, rect, 1, border_radius=6)
            draw_text(self.screen, cat, rect.centerx, rect.centery,
                      self.fonts['tiny'], Colors.WHITE, center=True, shadow=False)
        items = shop.get_items_in_category(shop.categories[shop.selected_category])
        item_rects   = []
        items_per_row = 4
        item_w, item_h = 200, 120
        for i, item in enumerate(items):
            col = i % items_per_row;  row = i // items_per_row
            ix  = 40 + col * (item_w+15)
            iy  = 130 + row * (item_h+15)
            rect = pygame.Rect(ix, iy, item_w, item_h)
            item_rects.append((rect, item))
            hover        = rect.collidepoint(mx, my)
            rarity_color = shop.rarity_color(item.rarity)
            bg           = lerp_color(Colors.DARK_PANEL, rarity_color, 0.15 if hover else 0.05)
            pygame.draw.rect(self.screen, bg,    rect, border_radius=10)
            pygame.draw.rect(self.screen,
                             rarity_color if hover else lerp_color(rarity_color, Colors.DARK_PANEL, 0.5),
                             rect, 2, border_radius=10)
            draw_text(self.screen, item.name, ix+item_w//2, iy+20,
                      self.fonts['small'], Colors.WHITE, center=True, shadow=False)
            draw_text(self.screen, item.rarity.name, ix+item_w//2, iy+42,
                      self.fonts['tiny'], rarity_color, center=True, shadow=False)
            if hasattr(item,'color') and item.color:
                pygame.draw.circle(self.screen, item.color, (ix+item_w//2, iy+65), 12)
            if item.unlocked:
                draw_text(self.screen, "EQUIPPED" if item.equipped else "OWNED",
                          ix+item_w//2, iy+item_h-18, self.fonts['tiny'],
                          Colors.GREEN if item.equipped else (100,100,100), center=True, shadow=False)
            elif item.cost_coins > 0:
                draw_text(self.screen, f"{item.cost_coins} Coins",
                          ix+item_w//2, iy+item_h-18, self.fonts['tiny'], Colors.GOLD, center=True, shadow=False)
            elif item.cost_diamonds > 0:
                draw_text(self.screen, f"{item.cost_diamonds} Diamonds",
                          ix+item_w//2, iy+item_h-18, self.fonts['tiny'], Colors.DIAMOND_BLUE, center=True, shadow=False)
        back_rect = pygame.Rect(20, CFG.SCREEN_HEIGHT-60, 100, 40)
        hover = back_rect.collidepoint(mx, my)
        pygame.draw.rect(self.screen, Colors.DARK_PANEL if not hover else Colors.RED,
                         back_rect, border_radius=8)
        pygame.draw.rect(self.screen, Colors.RED, back_rect, 1, border_radius=8)
        draw_text(self.screen, "BACK", 70, CFG.SCREEN_HEIGHT-40,
                  self.fonts['small'], Colors.WHITE, center=True)
        return tab_rects, item_rects, back_rect

    def draw_customize(self, player_snake_colors, dt):
        self.t += dt
        self.screen.fill(Colors.DARK_BG)
        draw_text(self.screen, "CUSTOMIZE YOUR SNAKE", CFG.SCREEN_WIDTH//2, 40,
                  self.fonts['large'], Colors.PURPLE, center=True)
        draw_text(self.screen, "Select Color Palette:", 60, 100, self.fonts['medium'], Colors.WHITE)
        palette_rects = []
        mx, my = pygame.mouse.get_pos()
        for i, palette in enumerate(Colors.SNAKE_PALETTES):
            col = i % 8; row = i // 8
            px  = 60 + col * 80; py = 140 + row * 80
            rect = pygame.Rect(px, py, 60, 60)
            palette_rects.append((rect, palette))
            hover = rect.collidepoint(mx, my)
            pygame.draw.rect(self.screen, palette[0], (px,    py, 30, 60), border_radius=5)
            pygame.draw.rect(self.screen, palette[1], (px+30, py, 30, 60), border_radius=5)
            if hover or palette == player_snake_colors:
                pygame.draw.rect(self.screen, Colors.WHITE, rect, 3, border_radius=5)
        preview_x = CFG.SCREEN_WIDTH//2; preview_y = 450
        draw_text(self.screen, "Preview", preview_x, 380, self.fonts['medium'], Colors.WHITE, center=True)
        for i in range(15):
            t     = i / 14
            color = lerp_color(player_snake_colors[1], player_snake_colors[0], 1.0-t)
            sx    = preview_x - 150 + i * 20
            size  = max(4, 14 - int(t*5))
            pygame.draw.circle(self.screen, color, (sx, preview_y), size)
            darker = tuple(max(0,c-40) for c in color)
            pygame.draw.circle(self.screen, darker, (sx, preview_y), size, 1)
        hx = preview_x - 150
        pygame.draw.circle(self.screen, Colors.WHITE, (hx-4, preview_y-5), 4)
        pygame.draw.circle(self.screen, Colors.WHITE, (hx-4, preview_y+5), 4)
        pygame.draw.circle(self.screen, Colors.BLACK, (hx-6, preview_y-5), 2)
        pygame.draw.circle(self.screen, Colors.BLACK, (hx-6, preview_y+5), 2)
        rand_rect = pygame.Rect(CFG.SCREEN_WIDTH//2-80, 520, 160, 40)
        hover     = rand_rect.collidepoint(mx, my)
        pygame.draw.rect(self.screen, Colors.PURPLE if hover else Colors.DARK_PANEL2,
                         rand_rect, border_radius=8)
        pygame.draw.rect(self.screen, Colors.PURPLE, rand_rect, 1, border_radius=8)
        draw_text(self.screen, "RANDOMIZE", rand_rect.centerx, rand_rect.centery,
                  self.fonts['small'], Colors.WHITE, center=True)
        back_rect = pygame.Rect(20, CFG.SCREEN_HEIGHT-60, 100, 40)
        hover     = back_rect.collidepoint(mx, my)
        pygame.draw.rect(self.screen, Colors.DARK_PANEL if not hover else Colors.RED,
                         back_rect, border_radius=8)
        pygame.draw.rect(self.screen, Colors.RED, back_rect, 1, border_radius=8)
        draw_text(self.screen, "BACK", 70, CFG.SCREEN_HEIGHT-40,
                  self.fonts['small'], Colors.WHITE, center=True)
        return palette_rects, rand_rect, back_rect

    def draw_stats(self, stats: StatsTracker, dt):
        self.t += dt
        self._update_bg_particles(dt)
        self._draw_bg()
        draw_text(self.screen, "STATISTICS", CFG.SCREEN_WIDTH//2, 50,
                  self.fonts['large'], Colors.CYAN, center=True)
        stats_data = [
            ("Games Played",     stats.games_played,                    Colors.WHITE),
            ("Total Wins",       stats.total_wins,                      Colors.GOLD),
            ("Total Kills",      stats.total_kills,                     Colors.RED),
            ("Total Coins",      stats.total_coins,                     Colors.GOLD),
            ("Total Diamonds",   stats.total_diamonds,                  Colors.DIAMOND_BLUE),
            ("Longest Survival", f"{stats.longest_survival:.1f}s",     Colors.GREEN),
            ("Best Kill Streak", stats.best_kill_streak,                Colors.ORANGE),
            ("Abilities Used",   stats.abilities_used,                  Colors.PURPLE),
        ]
        for i, (label, value, color) in enumerate(stats_data):
            y   = 120 + i * 50
            x   = CFG.SCREEN_WIDTH // 2
            pw  = 400
            rect = pygame.Rect(x - pw//2, y-5, pw, 40)
            pygame.draw.rect(self.screen, Colors.DARK_PANEL, rect, border_radius=8)
            pygame.draw.rect(self.screen, color,             rect, 1, border_radius=8)
            draw_text(self.screen, label,     x - pw//2 + 15, y+10, self.fonts['small'], Colors.WHITE)
            draw_text(self.screen, str(value),x + pw//2 - 15, y+10, self.fonts['medium'], color)
        mx, my    = pygame.mouse.get_pos()
        back_rect = pygame.Rect(20, CFG.SCREEN_HEIGHT-60, 100, 40)
        hover     = back_rect.collidepoint(mx, my)
        pygame.draw.rect(self.screen, Colors.DARK_PANEL if not hover else Colors.RED,
                         back_rect, border_radius=8)
        pygame.draw.rect(self.screen, Colors.RED, back_rect, 1, border_radius=8)
        draw_text(self.screen, "BACK", 70, CFG.SCREEN_HEIGHT-40,
                  self.fonts['small'], Colors.WHITE, center=True)
        return back_rect

    def draw_game_over(self, winner, player, stats, dt):
        self.t += dt
        overlay = pygame.Surface((CFG.SCREEN_WIDTH, CFG.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,180))
        self.screen.blit(overlay, (0,0))
        won         = winner and winner.is_player
        title_color = Colors.GOLD if won else Colors.RED
        title_text  = "VICTORY!" if won else "ELIMINATED"
        draw_text(self.screen, title_text, CFG.SCREEN_WIDTH//2, 150,
                  self.fonts['title'], title_color, center=True)
        if winner:
            draw_text(self.screen, f"Winner: {winner.name}", CFG.SCREEN_WIDTH//2, 230,
                      self.fonts['large'], Colors.WHITE, center=True)
        if player:
            y = 290
            draw_text(self.screen, f"Your Score: {player.score}", CFG.SCREEN_WIDTH//2, y,
                      self.fonts['medium'], Colors.WHITE, center=True);  y += 35
            draw_text(self.screen, f"Kills: {player.kills}", CFG.SCREEN_WIDTH//2, y,
                      self.fonts['medium'], Colors.RED, center=True);    y += 35
            draw_text(self.screen, f"Length: {player.length}", CFG.SCREEN_WIDTH//2, y,
                      self.fonts['medium'], Colors.GREEN, center=True);  y += 35
            draw_text(self.screen,
                      f"+{player.coins_collected} Coins  +{5 if won else 1} Diamonds",
                      CFG.SCREEN_WIDTH//2, y, self.fonts['medium'], Colors.GOLD, center=True)
        mx, my       = pygame.mouse.get_pos()
        button_rects = []
        for label, action, color, by in [
            ("PLAY AGAIN", 'play', Colors.GREEN, 500),
            ("MAIN MENU",  'menu', Colors.BLUE,  565),
        ]:
            rect  = pygame.Rect(CFG.SCREEN_WIDTH//2-120, by, 240, 50)
            hover = rect.collidepoint(mx, my)
            pygame.draw.rect(self.screen, color if hover else Colors.DARK_PANEL,
                             rect, border_radius=10)
            pygame.draw.rect(self.screen, color, rect, 2, border_radius=10)
            draw_text(self.screen, label, rect.centerx, rect.centery,
                      self.fonts['medium'], Colors.WHITE, center=True)
            button_rects.append((action, rect))
        return button_rects

    def draw_pause(self, dt):
        overlay = pygame.Surface((CFG.SCREEN_WIDTH, CFG.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,160))
        self.screen.blit(overlay, (0,0))
        draw_text(self.screen, "PAUSED", CFG.SCREEN_WIDTH//2, CFG.SCREEN_HEIGHT//2-60,
                  self.fonts['title'], Colors.WHITE, center=True)
        mx, my  = pygame.mouse.get_pos()
        buttons = []
        for label, action, color, by_off in [
            ("RESUME",       'resume', Colors.GREEN, 10),
            ("QUIT TO MENU", 'quit',   Colors.RED,   70),
        ]:
            rect  = pygame.Rect(CFG.SCREEN_WIDTH//2-100, CFG.SCREEN_HEIGHT//2+by_off, 200, 45)
            hover = rect.collidepoint(mx, my)
            pygame.draw.rect(self.screen, color if hover else Colors.DARK_PANEL,
                             rect, border_radius=10)
            pygame.draw.rect(self.screen, color, rect, 2, border_radius=10)
            draw_text(self.screen, label, rect.centerx, rect.centery,
                      self.fonts['medium'], Colors.WHITE, center=True)
            buttons.append((action, rect))
        return buttons

# ============================================================
# REGION: SOUND SYSTEM (Procedural)
# ============================================================

class SoundSystem:
    def __init__(self):
        self.enabled = True
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        try:
            pygame.mixer.init(44100, -16, 1, 512)
            self._generate_sounds()
        except Exception:
            self.enabled = False

    def _generate_sounds(self):
        try:
            import array
            sample_rate = 44100
            def make_sound(freq, duration, volume=0.3, wave='sine'):
                n_samples = int(sample_rate * duration)
                buf = array.array('h', [0] * n_samples)
                for i in range(n_samples):
                    t   = i / sample_rate
                    env = min(1.0, (n_samples - i) / (n_samples * 0.3))
                    env *= min(1.0, i / (sample_rate * 0.01))
                    val = math.sin(2*math.pi*freq*t) if wave == 'sine' else \
                          (1.0 if math.sin(2*math.pi*freq*t) > 0 else -1.0)
                    buf[i] = int(val * volume * 32767 * env)
                return pygame.mixer.Sound(buffer=buf)
            self.sounds['coin']    = make_sound(880,  0.15, 0.2)
            self.sounds['ko']      = make_sound(200,  0.4,  0.3, 'square')
            self.sounds['powerup'] = make_sound(660,  0.2,  0.2)
            self.sounds['boost']   = make_sound(440,  0.1,  0.1)
            self.sounds['click']   = make_sound(550,  0.08, 0.15)
            self.sounds['death']   = make_sound(150,  0.5,  0.25, 'square')
            self.sounds['win']     = make_sound(1000, 0.5,  0.2)
        except Exception:
            self.enabled = False

    def play(self, name: str):
        if self.enabled and name in self.sounds:
            try:
                self.sounds[name].play()
            except Exception:
                pass

# ============================================================
# REGION: MAIN GAME CLASS
# ============================================================

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("SLITHER ROYALE – AI SNAKE ARENA")
        self.screen = pygame.display.set_mode((CFG.SCREEN_WIDTH, CFG.SCREEN_HEIGHT))
        self.clock  = pygame.time.Clock()
        self.running = True
        self.state   = GameState.MAIN_MENU
        self.prev_state = GameState.MAIN_MENU

        # Fonts first – needed by all systems
        self.fonts = self._init_fonts()

        # --- Skin & UI managers (MUST be inside __init__, after pygame.init) ---
        self.skin_mgr      = SkinManager()
        self.ui_mgr        = UIManager(self.screen, self.fonts, self.skin_mgr)
        self.player_skin_id: int = 0   # 0-4  (changed in skin customiser)

        # Other systems
        self.camera   = Camera()
        self.world: Optional[GameWorld] = None
        self.renderer = Renderer(self.screen, self.fonts, self.skin_mgr)
        self.menu     = MenuSystem(self.screen, self.fonts)
        self.shop     = ShopSystem()
        self.stats    = StatsTracker()
        self.sound    = SoundSystem()

        # Player persistent data
        self.player_coins:  int = 100
        self.player_diamonds: int = 10
        self.player_snake_colors = [Colors.SNAKE_PALETTES[0][0], Colors.SNAKE_PALETTES[0][1]]
        self.selected_game_mode  = GameMode.BATTLE_ROYALE

        # Input state
        self.player_input = {
            'mouse_angle': None,
            'boost':    False,
            'dash':     False,
            'shield':   False,
            'ghost':    False,
            'magnet':   False,
            'teleport': False,
            'freeze':   False,
            'poison':   False,
        }

        # Collect events for ui_mgr (passed each frame)
        self._frame_events: list = []

    # ------------------------------------------------------------------
    def _init_fonts(self) -> dict:
        fonts = {}
        try:
            available = pygame.font.get_fonts()
            font_name = next((f for f in ['arial','helvetica','segoeui','verdana','tahoma','calibri']
                              if f in available), None)
            if not font_name:
                raise Exception("no preferred font")
            fonts['title']  = pygame.font.SysFont(font_name, 64, bold=True)
            fonts['large']  = pygame.font.SysFont(font_name, 40, bold=True)
            fonts['medium'] = pygame.font.SysFont(font_name, 24, bold=True)
            fonts['small']  = pygame.font.SysFont(font_name, 18)
            fonts['tiny']   = pygame.font.SysFont(font_name, 14)
            fonts['ko']     = pygame.font.SysFont(font_name, 72, bold=True)
        except Exception:
            fonts['title']  = pygame.font.Font(None, 64)
            fonts['large']  = pygame.font.Font(None, 40)
            fonts['medium'] = pygame.font.Font(None, 28)
            fonts['small']  = pygame.font.Font(None, 22)
            fonts['tiny']   = pygame.font.Font(None, 16)
            fonts['ko']     = pygame.font.Font(None, 72)
        return fonts

    # ------------------------------------------------------------------
    def start_match(self, mode: GameMode = GameMode.BATTLE_ROYALE):
        self.world = GameWorld(mode)
        self.world.init_match()
        if self.world.player:
            self.world.player.color1 = self.player_snake_colors[0]
            self.world.player.color2 = self.player_snake_colors[1]
        self.camera.x           = self.world.player.x
        self.camera.y           = self.world.player.y
        self.camera.zoom        = CFG.CAMERA_ZOOM_DEFAULT
        self.camera.target_zoom = CFG.CAMERA_ZOOM_DEFAULT
        self.state              = GameState.PLAYING
        self.stats.games_played += 1

    # ------------------------------------------------------------------
    def run(self):
        while self.running:
            dt = self.clock.tick(CFG.FPS) / 1000.0
            dt = min(dt, 0.05)

            self._frame_events = pygame.event.get()
            self._handle_events()
            self._update(dt)
            self._render(dt)
            pygame.display.flip()

        pygame.quit()
        sys.exit()

    # ------------------------------------------------------------------
    def _handle_events(self):
        # Reset one-shot inputs
        for key in ('dash','shield','ghost','magnet','teleport','freeze','poison'):
            self.player_input[key] = False

        for event in self._frame_events:
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)

            elif event.type == pygame.MOUSEWHEEL:
                if self.state in (GameState.PLAYING, GameState.SPECTATING):
                    self.camera.target_zoom = clamp(
                        self.camera.target_zoom + event.y * 0.1,
                        CFG.CAMERA_ZOOM_MIN, CFG.CAMERA_ZOOM_MAX)

            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event.key)

            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    self.player_input['boost'] = False

        keys = pygame.key.get_pressed()
        self.player_input['boost'] = keys[pygame.K_SPACE]

        if self.state in (GameState.PLAYING, GameState.SPECTATING):
            mx, my = pygame.mouse.get_pos()
            if self.world and self.world.player and self.world.player.alive:
                self.player_input['mouse_angle'] = math.atan2(
                    my - CFG.SCREEN_HEIGHT / 2,
                    mx - CFG.SCREEN_WIDTH  / 2)

    # ------------------------------------------------------------------
    def _handle_keydown(self, key):
        if self.state == GameState.PLAYING:
            k = {pygame.K_ESCAPE:'esc', pygame.K_q:'dash', pygame.K_e:'shield',
                 pygame.K_r:'ghost', pygame.K_f:'magnet', pygame.K_t:'teleport',
                 pygame.K_g:'freeze', pygame.K_v:'poison'}.get(key)
            if k == 'esc':
                self.state = GameState.PAUSED
            elif k:
                self.player_input[k] = True

        elif self.state == GameState.PAUSED:
            if key == pygame.K_ESCAPE:
                self.state = GameState.PLAYING

        elif self.state == GameState.SPECTATING:
            if key == pygame.K_ESCAPE:
                self._end_match()
            elif key == pygame.K_LEFT and self.world:
                alive = [s for s in self.world.snakes if s.alive]
                if alive:
                    self.world.spectating_index = (self.world.spectating_index - 1) % len(alive)
            elif key == pygame.K_RIGHT and self.world:
                alive = [s for s in self.world.snakes if s.alive]
                if alive:
                    self.world.spectating_index = (self.world.spectating_index + 1) % len(alive)

        elif self.state == GameState.MAIN_MENU:
            if key == pygame.K_ESCAPE:
                self.running = False

        elif self.state in (GameState.SHOP, GameState.CUSTOMIZE,
                            GameState.MODE_SELECT, GameState.STATS_SCREEN,
                            GameState.GAME_OVER):
            if key == pygame.K_ESCAPE:
                self.state = GameState.MAIN_MENU

    # ------------------------------------------------------------------
    def _handle_click(self, pos):
        self.sound.play('click')

        if self.state == GameState.MAIN_MENU:
            for i, rect in enumerate(self.menu.draw_main_menu(0)):
                if rect.collidepoint(pos):
                    [self.start_match, lambda:setattr(self,'state',GameState.MODE_SELECT),
                     lambda:setattr(self,'state',GameState.SHOP),
                     lambda:setattr(self,'state',GameState.CUSTOMIZE),
                     lambda:setattr(self,'state',GameState.STATS_SCREEN),
                     lambda:setattr(self,'running',False)][i]()
                    break

        elif self.state == GameState.MODE_SELECT:
            for rect, mode in self.menu.draw_mode_select(0):
                if rect.collidepoint(pos):
                    if mode is None:
                        self.state = GameState.MAIN_MENU
                    else:
                        self.selected_game_mode = mode
                        self.start_match(mode)
                    break

        elif self.state == GameState.SHOP:
            tab_rects, item_rects, back_rect = self.menu.draw_shop(
                self.shop, self.player_coins, self.player_diamonds, 0)
            for i, rect in enumerate(tab_rects):
                if rect.collidepoint(pos):
                    self.shop.selected_category = i;  break
            for rect, item in item_rects:
                if rect.collidepoint(pos):
                    self._try_purchase(item);  break
            if back_rect.collidepoint(pos):
                self.state = GameState.MAIN_MENU

        elif self.state == GameState.CUSTOMIZE:
            palette_rects, rand_rect, back_rect = self.menu.draw_customize(
                self.player_snake_colors, 0)
            for rect, palette in palette_rects:
                if rect.collidepoint(pos):
                    self.player_snake_colors = list(palette);  break
            if rand_rect.collidepoint(pos):
                self.player_snake_colors = list(random.choice(Colors.SNAKE_PALETTES))
            if back_rect.collidepoint(pos):
                self.state = GameState.MAIN_MENU

        elif self.state == GameState.STATS_SCREEN:
            if self.menu.draw_stats(self.stats, 0).collidepoint(pos):
                self.state = GameState.MAIN_MENU

        elif self.state == GameState.GAME_OVER:
            for name, rect in self.menu.draw_game_over(
                    self.world.winner if self.world else None,
                    self.world.player if self.world else None,
                    self.stats, 0):
                if rect.collidepoint(pos):
                    if name == 'play':  self.start_match(self.selected_game_mode)
                    elif name == 'menu': self.state = GameState.MAIN_MENU
                    break

        elif self.state == GameState.PAUSED:
            for name, rect in self.menu.draw_pause(0):
                if rect.collidepoint(pos):
                    if name == 'resume': self.state = GameState.PLAYING
                    elif name == 'quit': self._end_match()
                    break

    # ------------------------------------------------------------------
    def _try_purchase(self, item: CosmeticItem):
        if item.unlocked:
            for other in self.shop.items:
                if other.category == item.category:
                    other.equipped = False
            item.equipped = True
            self.sound.play('click')
            return
        if item.cost_coins > 0 and self.player_coins >= item.cost_coins:
            self.player_coins -= item.cost_coins
            item.unlocked = item.equipped = True
            for other in self.shop.items:
                if other.category == item.category and other != item:
                    other.equipped = False
            self.sound.play('powerup')
        elif item.cost_diamonds > 0 and self.player_diamonds >= item.cost_diamonds:
            self.player_diamonds -= item.cost_diamonds
            item.unlocked = item.equipped = True
            for other in self.shop.items:
                if other.category == item.category and other != item:
                    other.equipped = False
            self.sound.play('powerup')

    # ------------------------------------------------------------------
    def _end_match(self):
        if self.world and self.world.player:
            self.stats.total_kills += self.world.player.kills
            self.stats.total_coins += self.world.player.coins_collected
            self.player_coins      += self.world.player.coins_collected
            self.stats.current_survival = self.world.match_timer
            if self.world.match_timer > self.stats.longest_survival:
                self.stats.longest_survival = self.world.match_timer
            if self.world.winner and self.world.winner.is_player:
                self.stats.total_wins    += 1
                self.player_diamonds     += 5
                self.stats.total_diamonds+= 5
            else:
                self.player_diamonds     += 1
                self.stats.total_diamonds+= 1
        self.state = GameState.MAIN_MENU

    # ------------------------------------------------------------------
    def _update(self, dt: float):
        # Advance skin & UI animations every frame
        self.skin_mgr.update(dt)
        self.ui_mgr.update(dt)

        if self.state == GameState.PLAYING:
            if self.world:
                self.world.update(dt, self.player_input)

                if self.world.player and self.world.player.alive:
                    self.camera.set_target(self.world.player.x, self.world.player.y)
                else:
                    self.state = GameState.SPECTATING

                for ko in self.world.ko_effects:
                    if ko.timer >= ko.max_timer - 0.05:
                        d = dist(self.camera.world_to_screen(ko.x, ko.y),
                                 (CFG.SCREEN_WIDTH/2, CFG.SCREEN_HEIGHT/2))
                        if d < 400:
                            self.camera.shake(8, 0.3)
                            self.sound.play('ko')

                if self.world.game_over:
                    self.state = GameState.GAME_OVER
                    self.sound.play('win' if self.world.winner and
                                    self.world.winner.is_player else 'death')
                    if self.world.player:
                        self.stats.total_kills += self.world.player.kills
                        self.stats.total_coins += self.world.player.coins_collected
                        self.player_coins      += self.world.player.coins_collected
                        if self.world.player.kills > self.stats.best_kill_streak:
                            self.stats.best_kill_streak = self.world.player.kills
                        self.stats.current_survival = self.world.match_timer
                        if self.world.match_timer > self.stats.longest_survival:
                            self.stats.longest_survival = self.world.match_timer
                        if self.world.winner and self.world.winner.is_player:
                            self.stats.total_wins    += 1
                            self.player_diamonds     += 5
                            self.stats.total_diamonds+= 5
                        else:
                            self.player_diamonds     += 1
                            self.stats.total_diamonds+= 1

                self.camera.update(dt)

                if (self.world.player and self.world.player.alive and
                        self.world.player.boosting and len(self.world.player.segments) > 1):
                    tail = self.world.player.segments[-1]
                    self.world.particles.emit(tail[0], tail[1], 0, 0,
                                              self.world.player.color2,
                                              life=0.3, size=4, count=2, spread=20)

        elif self.state == GameState.SPECTATING:
            if self.world:
                self.world.update(dt, {k: False for k in self.player_input})
                alive = [s for s in self.world.snakes if s.alive]
                if alive:
                    target = alive[self.world.spectating_index % len(alive)]
                    self.camera.set_target(target.x, target.y)
                self.camera.update(dt)
                if self.world.game_over:
                    self.state = GameState.GAME_OVER
                    if self.world.player:
                        self.player_coins += self.world.player.coins_collected

    # ------------------------------------------------------------------
    def _render(self, dt: float):
        if self.state == GameState.MAIN_MENU:
            self.menu.draw_main_menu(dt)

        elif self.state == GameState.MODE_SELECT:
            self.menu.draw_mode_select(dt)

        elif self.state == GameState.SHOP:
            self.menu.draw_shop(self.shop, self.player_coins, self.player_diamonds, dt)

        elif self.state == GameState.CUSTOMIZE:
            self.menu.draw_customize(self.player_snake_colors, dt)

        elif self.state == GameState.STATS_SCREEN:
            self.menu.draw_stats(self.stats, dt)

        elif self.state in (GameState.PLAYING, GameState.SPECTATING):
            if self.world:
                self.renderer.render_game(self.world, self.camera,
                                          self.state, self.player_skin_id)

        elif self.state == GameState.GAME_OVER:
            if self.world:
                self.renderer.render_game(self.world, self.camera,
                                          self.state, self.player_skin_id)
            self.menu.draw_game_over(
                self.world.winner if self.world else None,
                self.world.player if self.world else None,
                self.stats, dt)

        elif self.state == GameState.PAUSED:
            if self.world:
                self.renderer.render_game(self.world, self.camera,
                                          self.state, self.player_skin_id)
            self.menu.draw_pause(dt)

        # FPS counter
        draw_text(self.screen, f"FPS: {int(self.clock.get_fps())}",
                  CFG.SCREEN_WIDTH - 80, CFG.SCREEN_HEIGHT - 20,
                  self.fonts['tiny'], (80, 80, 80))

# ============================================================
# REGION: ENTRY POINT
# ============================================================

def main():
    game = Game()
    game.run()

if __name__ == "__main__":
    main()
