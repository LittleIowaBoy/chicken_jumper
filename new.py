# new_chicken_platformer.py
# Platformer with procedural platform generation, endpoint flag, and faster jump refresh
# Requires: pip install pygame

import pygame
import sys
import random
import math

# ---- Config ----
WIDTH, HEIGHT = 1000, 600
FPS = 60
GRAVITY = 0.8
PLAYER_SPEED = 4.5
PLAYER_JUMP_SPEED = -17.1
JUMP_COOLDOWN_MS = 150  # Jump cooldown in milliseconds
PLATFORM_COLOR = (80, 40, 20)
SLIPPERY_PLATFORM_COLOR = (80, 120, 170)
BOOST_COLOR = (240, 200, 40)
ENEMY_COLOR = (180, 40, 40)
BG_COLOR = (135, 206, 235)  # Sky blue
GEN_AHEAD = 1400  # Pixels ahead of camera to generate platforms
GEN_BUFFER = 400  # Keep platforms behind this distance before removing
SLIPPERY_ACCEL = 0.35
BOOST_JUMP_MULT = 1.5
SLIP_SHORT_MS = 200
SLIP_MEDIUM_MS = 400
SLIP_LONG_MS = 700

# Particle settings
PARTICLE_SPAWN_COUNT = 5
PARTICLE_POOL_LIMIT = 50
PARTICLE_VELOCITY_MIN = -2
PARTICLE_VELOCITY_MAX = 2
PARTICLE_LIFETIME = 20

# Checkpoint settings
CHECKPOINT_SPACING = 1000

# Platform generation
CHUNK_WIDTH = 800
CHUNK_HEIGHT = 800  # Doubled for better vertical spread
PLATFORMS_PER_CHUNK = 60 
PLATFORM_BUFFER = 150  # Increased for better spacing
LEVEL_CHUNKS_X = 20
LEVEL_CHUNKS_Y = 20  # 20x20 background grid

# Portal spawn (reuse starter platform at y=460)
PORTAL_X = 200
PORTAL_PLATFORM_Y = 460
GRID_ORIGIN_X = 200
GRID_ORIGIN_Y = PORTAL_PLATFORM_Y

# Camera
CAMERA_SMOOTHING = 0.15
CAMERA_OFFSET_X_RATIO = 3  # WIDTH // 3

# Cloud rendering
CLOUD_WIDTH = 120
CLOUD_HEIGHT = 40
CLOUD_SPACING = 220
CLOUD_Y_OFFSET = 80
CLOUD_Y_STEP = 20

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 20)
big_font = pygame.font.SysFont("Arial", 56)
menu_font = pygame.font.SysFont("Arial", 32)
small_menu_font = pygame.font.SysFont("Arial", 24)

# ---- Game States ----
MENU = "menu"
PLAYING = "playing"
WIN_MENU = "win_menu"

# ---- New: Best Time Tracking ----
best_time = float('inf')  # Global to store best time

# ---- New: Particle Effect for Landing ----
class Particle(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (200, 200, 200), (4, 4), 4)
        self.rect = self.image.get_rect(center=(x, y))
        self.vx = random.uniform(PARTICLE_VELOCITY_MIN, PARTICLE_VELOCITY_MAX)
        self.vy = random.uniform(PARTICLE_VELOCITY_MIN, 0)
        self.lifetime = PARTICLE_LIFETIME  # Frames

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()

# ---- Helper Classes ----
class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h, moving=False, move_range=(0, 0), speed=0, surface_type="normal", slip_duration_ms=None, initial_direction=1):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.surface_type = surface_type
        if self.surface_type == "slippery":
            self.image.fill(SLIPPERY_PLATFORM_COLOR)
        else:
            self.image.fill(PLATFORM_COLOR)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.pos_x = float(self.rect.x)
        self.moving = moving
        self.speed = speed
        self.move_range = move_range
        self.direction = initial_direction
        if self.surface_type == "slippery":
            if slip_duration_ms is None:
                self.slip_duration_ms = random.choice([SLIP_SHORT_MS, SLIP_MEDIUM_MS, SLIP_LONG_MS])
            else:
                self.slip_duration_ms = slip_duration_ms
        else:
            self.slip_duration_ms = 0

    def update(self, camera_x):
        if self.moving:
            self.pos_x += self.direction * self.speed
            self.rect.x = int(self.pos_x)
            if self.rect.x < self.move_range[0] or self.rect.x > self.move_range[1]:
                self.direction *= -1
                self.pos_x += self.direction * self.speed
                self.rect.x = int(self.pos_x)

class Checkpoint(pygame.sprite.Sprite):
    def __init__(self, x, ground_y):
        super().__init__()
        self.image = pygame.Surface((20, 40), pygame.SRCALPHA)
        self.rect = self.image.get_rect(midbottom=(x, ground_y))
        self.x = x
        self.y = ground_y - 24  # Store Y position for respawning (above platform)
        self.activated = False  # Track if checkpoint is triggered
        self.draw()

    def draw(self):
        color = (255, 255, 0) if self.activated else (0, 255, 0)  # Yellow when activated, green otherwise
        self.image.fill((0, 0, 0, 0))  # Clear surface
        pygame.draw.rect(self.image, color, (0, 0, 20, 40))  # Draw pole

    def activate(self):
        if not self.activated:
            self.activated = True
            self.draw()

class Flag(pygame.sprite.Sprite):
    def __init__(self, x, ground_y):
        super().__init__()
        self.x = x
        self.ground_y = ground_y
        self.image = pygame.Surface((36, 64), pygame.SRCALPHA)
        self.rect = self.image.get_rect(midbottom=(x + 18, ground_y))
        self.draw_flag()

    def draw_flag(self):
        self.image.fill((0, 0, 0, 0))
        pole_color = (80, 50, 20)
        flag_color = (220, 40, 40)
        pygame.draw.rect(self.image, pole_color, (16, 0, 4, 64))
        pygame.draw.polygon(self.image, flag_color, [(18, 8), (36, 18), (18, 28)])

class Portal(pygame.sprite.Sprite):
    def __init__(self, x, ground_y):
        super().__init__()
        self.x = x
        self.ground_y = ground_y
        self.image = pygame.Surface((36, 64), pygame.SRCALPHA)
        self.rect = self.image.get_rect(midbottom=(x, ground_y))
        self.draw_portal()

    def draw_portal(self):
        self.image.fill((0, 0, 0, 0))
        pygame.draw.ellipse(self.image, (90, 30, 160), (2, 6, 32, 56))
        pygame.draw.ellipse(self.image, (180, 120, 240), (8, 14, 20, 40))

class Enemy(pygame.sprite.Sprite):
    def __init__(self, platform, speed=2):
        super().__init__()
        self.image = pygame.Surface((28, 18), pygame.SRCALPHA)
        pygame.draw.rect(self.image, ENEMY_COLOR, (0, 0, 28, 18), border_radius=4)
        self.platform = platform
        self.rect = self.image.get_rect(midbottom=(platform.rect.centerx, platform.rect.top))
        self.direction = 1
        self.speed = speed
        self.min_x = platform.rect.left + 6
        self.max_x = platform.rect.right - 6
        self.paused = False
        self.pause_end_time = 0
        self.pause_duration = 2000  # 2 seconds in milliseconds

    def update(self):
        current_time = pygame.time.get_ticks()
        
        # If paused, check if pause time has elapsed
        if self.paused:
            if current_time >= self.pause_end_time:
                self.paused = False
                self.direction *= -1  # Change direction after pause
        else:
            # Move the enemy
            self.rect.x += self.direction * self.speed
            # Check if reached platform edge
            if self.rect.left <= self.min_x or self.rect.right >= self.max_x:
                # Clamp position to edge
                if self.rect.left <= self.min_x:
                    self.rect.left = self.min_x
                else:
                    self.rect.right = self.max_x
                # Start pause
                self.paused = True
                self.pause_end_time = current_time + self.pause_duration
        
        self.rect.bottom = self.platform.rect.top

class Orb(pygame.sprite.Sprite):
    def __init__(self, center_x, center_y, radius=80, speed=0.02):
        super().__init__()
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius
        self.speed = speed
        self.angle = random.uniform(0, 2 * math.pi)  # Random starting angle
        self.glow_phase = 0
        self.image = pygame.Surface((32, 32), pygame.SRCALPHA)
        self.draw_orb()
        self.rect = self.image.get_rect(center=(center_x, center_y))

    def draw_orb(self):
        self.image.fill((0, 0, 0, 0))
        # Outer glow
        glow_intensity = int(100 + 50 * abs(math.sin(self.glow_phase)))
        pygame.draw.circle(self.image, (255, glow_intensity, 0, 180), (16, 16), 14)
        # Inner core
        pygame.draw.circle(self.image, (255, 200, 50), (16, 16), 10)
        pygame.draw.circle(self.image, (255, 255, 150), (16, 16), 6)

    def update(self):
        # Move in circular motion
        self.angle += self.speed
        if self.angle > 2 * math.pi:
            self.angle -= 2 * math.pi
        
        # Calculate position on circle
        x = self.center_x + self.radius * math.cos(self.angle)
        y = self.center_y + self.radius * math.sin(self.angle)
        self.rect.center = (int(x), int(y))
        
        # Update glow animation
        self.glow_phase += 0.1
        self.draw_orb()

class JumpBoost(pygame.sprite.Sprite):
    def __init__(self, platform):
        super().__init__()
        self.platform = platform
        self.image = pygame.Surface((18, 18), pygame.SRCALPHA)
        pygame.draw.circle(self.image, BOOST_COLOR, (9, 9), 8)
        pygame.draw.circle(self.image, (250, 240, 180), (9, 9), 4)
        self.rect = self.image.get_rect(midbottom=(platform.rect.centerx, platform.rect.top - 2))

    def update(self):
        self.rect.midbottom = (self.platform.rect.centerx, self.platform.rect.top - 2)

class Chicken(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.base_w, self.base_h = 48, 48
        self.image = pygame.Surface((self.base_w, self.base_h), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))
        self.pos_x = float(self.rect.x)
        self.pos_y = float(self.rect.y)
        self.vx = 0
        self.vy = 0
        self.desired_vx = 0
        self.on_ground = False
        self.facing_right = True
        self.flap_phase = 0.0
        self.last_jump_time = -9999
        self.was_on_ground = False
        self.last_platform = None  # New: Track the platform the player is standing on
        self.jump_buffer = 0
        self.boost_jump_ready = False
        self.developer_mode = False
        self.slip_active = False
        self.slip_timer_ms = 0
        self.slip_total_ms = 0
        self.slip_start_vx = 0
        
    def update_physics(self, platforms, particles):
        prev_on_ground = self.on_ground
        prev_platform = self.last_platform
        self.on_ground = False  # Reset on_ground each update

        surface_type = "normal"
        if prev_on_ground and prev_platform is not None:
            surface_type = prev_platform.surface_type
        if surface_type == "slippery" and prev_on_ground:
            if self.desired_vx != 0:
                delta = self.desired_vx - self.vx
                if delta > SLIPPERY_ACCEL:
                    delta = SLIPPERY_ACCEL
                elif delta < -SLIPPERY_ACCEL:
                    delta = -SLIPPERY_ACCEL
                self.vx += delta
                if self.slip_total_ms > 0:
                    self.slip_start_vx = self.vx
                    self.slip_timer_ms = self.slip_total_ms
                    self.slip_active = True
            elif self.slip_active and self.slip_timer_ms > 0 and self.slip_total_ms > 0:
                self.slip_timer_ms = max(0, self.slip_timer_ms - clock.get_time())
                ratio = self.slip_timer_ms / self.slip_total_ms
                self.vx = self.slip_start_vx * ratio
            else:
                self.vx = 0
        else:
            self.vx = self.desired_vx
            self.slip_active = False
        
        platform_vx = 0
        if prev_on_ground and prev_platform and prev_platform.moving:
            platform_vx = prev_platform.direction * prev_platform.speed
        
        # Apply character velocity plus platform velocity if standing on it
        self.pos_x += self.vx + platform_vx
        self.rect.x = int(self.pos_x)
        self.collide_horizontal(platforms, ignore_platform=prev_platform if prev_on_ground else None)
        self.pos_y += self.vy
        self.rect.y = int(self.pos_y)
        self.collide_vertical(platforms, particles)
        self.vy += GRAVITY

        # If we just landed on a moving platform, inherit its motion immediately
        if not prev_on_ground and self.on_ground and self.last_platform and self.last_platform.moving:
            self.pos_x += self.last_platform.direction * self.last_platform.speed
            self.rect.x = int(self.pos_x)

    def collide_horizontal(self, platforms, ignore_platform=None):
        hits = pygame.sprite.spritecollide(self, platforms, False)
        for p in hits:
            if ignore_platform is not None and p is ignore_platform:
                continue
            if self.vx > 0:
                self.rect.right = p.rect.left
            elif self.vx < 0:
                self.rect.left = p.rect.right
            self.pos_x = float(self.rect.x)
            self.vx = 0


    def collide_vertical(self, platforms, particles):
        hits = pygame.sprite.spritecollide(self, platforms, False)
        self.last_platform = None  # Reset last platform
        
        for p in hits:
            if self.vy > 0:
                # Only spawn particles if we were NOT on ground last frame AND we are falling
                # This ensures it only triggers on the landing transition, not every frame
                if not self.was_on_ground and self.vy > 5:  # Add velocity threshold to avoid micro-bounces
                    if len(particles) < PARTICLE_POOL_LIMIT:
                        for _ in range(PARTICLE_SPAWN_COUNT):
                            particles.add(Particle(self.rect.centerx, self.rect.bottom))
                
                self.rect.bottom = p.rect.top
                self.on_ground = True
                self.last_platform = p  # Track the platform we landed on
                if p.surface_type == "slippery":
                    self.slip_total_ms = p.slip_duration_ms
                    self.slip_timer_ms = p.slip_duration_ms
                    self.slip_start_vx = self.vx
                    self.slip_active = True
                else:
                    self.slip_active = False
            elif self.vy < 0:
                self.rect.top = p.rect.bottom
            self.pos_y = float(self.rect.y)
            self.vy = 0  # Reset velocity for both cases to stabilize physics
        
        self.was_on_ground = self.on_ground


    def can_jump(self):
        return self.on_ground or self.developer_mode

    def jump(self):
        if self.can_jump():
            jump_speed = PLAYER_JUMP_SPEED
            if self.boost_jump_ready:
                jump_speed *= BOOST_JUMP_MULT
                self.boost_jump_ready = False
            self.vy = jump_speed
            self.on_ground = False
            self.last_platform = None  # New: Clear platform on jump
            self.last_jump_time = pygame.time.get_ticks()
            self.jump_buffer = 0
            # Uncomment if you have a jump.wav file
            # jump_sound = pygame.mixer.Sound("jump.wav")
            # jump_sound.play()

    def draw_chicken(self):
        surf = pygame.Surface((self.base_w, self.base_h), pygame.SRCALPHA)
        w, h = self.base_w, self.base_h
        cx, cy = w // 2, h // 2

        body_color = (255, 245, 200)
        pygame.draw.ellipse(surf, body_color, (6, 8, 36, 26))

        wing_color = (230, 200, 150)
        flap = int(6 * (0.6 + 0.4 * math.sin(self.flap_phase)))
        wing_rect = pygame.Rect(18, 14 - flap, 18, 12 + flap)
        pygame.draw.ellipse(surf, wing_color, wing_rect)

        pygame.draw.circle(surf, body_color, (cx + (12 if self.facing_right else -12), 10), 9)

        beak_color = (255, 165, 0)
        bx = cx + (18 if self.facing_right else -18)
        if self.facing_right:
            pygame.draw.polygon(surf, beak_color, [(bx, 10), (bx + 8, 12), (bx, 14)])
        else:
            pygame.draw.polygon(surf, beak_color, [(bx, 10), (bx - 8, 12), (bx, 14)])

        eye_x = cx + (10 if self.facing_right else -10)
        pygame.draw.circle(surf, (0, 0, 0), (eye_x, 8), 2)

        comb_color = (255, 60, 60)
        pygame.draw.polygon(surf, comb_color, [
            (cx + (14 if self.facing_right else -14), 6),
            (cx + (16 if self.facing_right else -16), 2),
            (cx + (12 if self.facing_right else -12), 4)
        ])

        foot_y = h - 6
        left_x = cx - 6
        right_x = cx + 2
        foot_color = (255, 160, 60)
        leg_phase = int(2 * math.sin(self.flap_phase * 1.6))
        pygame.draw.line(surf, foot_color, (left_x, foot_y), (left_x, foot_y + 6 + leg_phase), 3)
        pygame.draw.line(surf, foot_color, (right_x, foot_y), (right_x, foot_y + 6 - leg_phase), 3)

        outline = pygame.mask.from_surface(surf).outline()
        for ox, oy in outline:
            if 0 <= ox < w and 0 <= oy < h:
                old = surf.get_at((ox, oy))
                if old.a != 0:
                    surf.set_at((ox, oy), (0, 0, 0, 120))

        self.image = surf

    def update(self, platforms, particles, boosts):
        speed_factor = min(1.0, abs(self.vx) / PLAYER_SPEED)
        self.flap_phase += 0.25 + 0.8 * speed_factor
        self.draw_chicken()
        self.update_physics(platforms, particles)
        self.boost_jump_ready = False
        if boosts:
            for b in boosts:
                if self.on_ground and self.rect.colliderect(b.rect):
                    self.boost_jump_ready = True
                    break
        if self.jump_buffer > 0:
            self.jump_buffer -= clock.get_time()
            if self.can_jump() and self.jump_buffer > 0:
                self.jump()

# ---- Level Generation ----
BASE_GRID_LAYOUT = [
    (1, 1),
    (2, 1),
    (3, 1),
    (4, 2),
    (5, 2),
    (6, 3),
    (7, 4),
    (8, 5),
    (9, 5),
    (10, 5),
]

LEVEL_GRID_LAYOUTS = {
    0: BASE_GRID_LAYOUT,
    1: BASE_GRID_LAYOUT,
    2: BASE_GRID_LAYOUT,
    3: BASE_GRID_LAYOUT,
    4: BASE_GRID_LAYOUT,
    5: BASE_GRID_LAYOUT,
}

def grid_level_length():
    return GRID_ORIGIN_X + (LEVEL_CHUNKS_X * CHUNK_WIDTH)

def level_scale_for_index(level_index):
    return max(0.72, 0.9 - (level_index * 0.04))

def make_add_platform(platforms, level_index):
    level_scale = level_scale_for_index(level_index)

    def add_platform(x, y, w, h, moving=False, move_range=(0, 0), speed=0, surface_type="normal", initial_direction=1):
        sw = max(12, int(w * level_scale))
        sh = max(12, int(h * level_scale))
        p = Platform(x, y, sw, sh, moving=moving, move_range=move_range, speed=speed, surface_type=surface_type, initial_direction=initial_direction)
        platforms.add(p)
        return p

    return add_platform

def get_level_layout(level_index):
    return LEVEL_GRID_LAYOUTS.get(level_index, BASE_GRID_LAYOUT)

def get_next_grid_coordinates(existing_coords, num_to_generate=5):
    """
    Generate next grid coordinates following the pattern from existing coords.
    Pattern: gradually ascend with occasional flat sections.
    """
    if not existing_coords:
        return [(1, 1)]
    
    # Find the rightmost coordinates
    max_gx = max(gx for gx, gy in existing_coords)
    coords_at_max_x = [gy for gx, gy in existing_coords if gx == max_gx]
    current_gy = max(coords_at_max_x) if coords_at_max_x else 1
    
    # Analyze the pattern from BASE_GRID_LAYOUT to understand progression
    # Pattern shows: gradual climb with some plateaus
    new_coords = []
    for i in range(num_to_generate):
        new_gx = max_gx + i + 1
        
        # Every 3 cells, rise by 1 row (with some variation)
        if i % 3 == 2:
            current_gy += 1
        
        # Don't exceed reasonable height (20 rows)
        current_gy = min(current_gy, 20)
        
        new_coords.append((new_gx, current_gy))
    
    return new_coords

def check_platform_collision(x1, y1, w1, h1, moving1, move_range1, x2, y2, w2, h2, moving2, move_range2):
    """
    Check if two platforms will collide, accounting for movement ranges.
    
    Positions (x1, y1, x2, y2) are topleft coordinates to match Platform.rect positioning.
    For moving platforms, checks if their full movement ranges overlap.
    Returns True if collision detected, False otherwise.
    """
    # Calculate effective bounds for each platform (topleft-based)
    if moving1 and move_range1:
        # move_range contains min and max left edge positions
        left1 = move_range1[0]
        right1 = move_range1[1] + w1
    else:
        left1 = x1
        right1 = x1 + w1
    
    if moving2 and move_range2:
        # move_range contains min and max left edge positions
        left2 = move_range2[0]
        right2 = move_range2[1] + w2
    else:
        left2 = x2
        right2 = x2 + w2
    
    # Vertical bounds (platforms don't move vertically, topleft-based)
    top1 = y1
    bottom1 = y1 + h1
    top2 = y2
    bottom2 = y2 + h2
    
    # Check for overlap with safety margins
    horizontal_safety = PLATFORM_BUFFER  # Use full platform buffer for horizontal spacing
    vertical_safety = 80  # Player height (48px) + comfortable margin for climbing
    
    horizontal_overlap = not (right1 + horizontal_safety < left2 or right2 + horizontal_safety < left1)
    vertical_overlap = not (bottom1 + vertical_safety < top2 or bottom2 + vertical_safety < top1)
    
    return horizontal_overlap and vertical_overlap

def has_platform_collision(world_x, world_y, w, h, moving, move_range, check_against_dicts, check_against_sprites):
    """
    Helper function to check if a platform at given position collides with existing platforms.
    
    Args:
        world_x, world_y: Position of new platform (topleft)
        w, h: Dimensions of new platform
        moving: Whether new platform moves
        move_range: Movement range tuple for new platform
        check_against_dicts: List of dicts with platform data ({'x', 'y', 'w', 'h', 'moving', 'move_range'})
        check_against_sprites: List of platform sprites (with rect, moving, move_range attributes)
    
    Returns:
        True if collision detected, False otherwise
    """
    # Check against dict-based platform data
    for pdata in check_against_dicts:
        if check_platform_collision(
            world_x, world_y, w, h, moving, move_range,
            pdata['x'], pdata['y'], pdata['w'], pdata['h'],
            pdata['moving'], pdata['move_range']
        ):
            return True
    
    # Check against sprite-based platforms
    for existing_p in check_against_sprites:
        if check_platform_collision(
            world_x, world_y, w, h, moving, move_range,
            existing_p.rect.x, existing_p.rect.y,
            existing_p.rect.width, existing_p.rect.height,
            existing_p.moving, existing_p.move_range
        ):
            return True
    
    return False

def get_chunk_boundaries(gx, gy):
    """
    Calculate chunk boundaries for given grid coordinates.
    
    Args:
        gx, gy: Grid coordinates (1-indexed)
    
    Returns:
        Tuple of (chunk_left, chunk_right, chunk_top, chunk_bottom)
    """
    chunk_left = GRID_ORIGIN_X + (gx - 1) * CHUNK_WIDTH
    chunk_right = chunk_left + CHUNK_WIDTH
    chunk_top = GRID_ORIGIN_Y - gy * CHUNK_HEIGHT
    chunk_bottom = GRID_ORIGIN_Y - (gy - 1) * CHUNK_HEIGHT
    return chunk_left, chunk_right, chunk_top, chunk_bottom

def add_grid_platforms(level_index, add_platform, surface_type="normal", existing_platforms=None):
    """
    Generate grid-based platforms for a level.
    
    Args:
        level_index: Index of the level
        add_platform: Function to add platforms to sprite group
        surface_type: Type of surface ("normal" or "slippery")
        existing_platforms: Optional sprite group of platforms to check collisions against
    """
    placed = []
    layout = get_level_layout(level_index)
    move_span = int(CHUNK_WIDTH * 0.2)
    base_speed = 1 if surface_type == "slippery" else 2
    
    # Build initial collision check list from existing platforms
    initial_check_list = []
    if existing_platforms:
        for p in existing_platforms:
            initial_check_list.append({
                'platform': p,
                'x': p.rect.x,
                'y': p.rect.y,
                'w': p.rect.width,
                'h': p.rect.height,
                'moving': p.moving,
                'move_range': p.move_range
            })

    for i, (gx, gy) in enumerate(layout):
        # Chunk boundaries
        chunk_left, chunk_right, chunk_top, chunk_bottom = get_chunk_boundaries(gx, gy)
        
        is_vertical = level_index == 2 and gx % 2 == 0

        # Generate multiple platforms per chunk
        chunk_center_y = (chunk_top + chunk_bottom) / 2
        for j in range(PLATFORMS_PER_CHUNK):
            # Randomize platform position within chunk
            if is_vertical:
                w, h = 18, 160
                moving = False
                # For vertical platforms, distribute across chunk with more variation
                world_x = chunk_left + random.randint(int(PLATFORM_BUFFER * 0.3), CHUNK_WIDTH - int(PLATFORM_BUFFER * 0.7) - w)
                # Use full chunk height with random distribution
                world_y = chunk_top + random.randint(h, CHUNK_HEIGHT - h)
            else:
                w, h = 160, 18
                moving = level_index == 1 or (i + j) % 3 == 0
                # Gradient distribution: cluster around middle with diminishing density toward edges
                # Use Gaussian distribution for Y position (cluster around center)
                offset_from_center = random.gauss(0, CHUNK_HEIGHT * 0.25)
                world_y = chunk_center_y + offset_from_center
                # X position: distribute horizontally with variation
                x_base = chunk_left + (j * (CHUNK_WIDTH // PLATFORMS_PER_CHUNK))
                world_x = x_base + random.randint(-50, 50)
            
            # Allow 50% overlap beyond chunk bounds
            world_x = max(chunk_left - w//2, min(world_x, chunk_right + w//2 - w))
            world_y = max(chunk_top - h//2, min(world_y, chunk_bottom + h//2 - h))
            
            # Check for collision with existing platforms
            move_range = (world_x - move_span, world_x + move_span)
            if has_platform_collision(world_x, world_y, w, h, moving, move_range, initial_check_list, placed):
                continue
            # Randomize speed and direction for moving platforms
            random_speed = random.uniform(1.0, 3.5) if moving else base_speed
            random_direction = random.choice([-1, 1]) if moving else 1
            p = add_platform(
                world_x,
                world_y,
                w,
                h,
                moving=moving,
                move_range=move_range,
                speed=random_speed,
                surface_type=surface_type,
                initial_direction=random_direction,
            )
            placed.append(p)
        
        # Add extra platforms in top-right quarter for easier climbing
        # Top-right quarter: right half horizontally, top half vertically
        top_right_count = 12
        for k in range(top_right_count):
            w, h = 140, 18
            moving = False
            # X position: right half of chunk
            world_x = chunk_left + CHUNK_WIDTH * 0.5 + random.randint(0, int(CHUNK_WIDTH * 0.5) - w)
            # Y position: top half of chunk
            world_y = chunk_top + random.randint(20, int(CHUNK_HEIGHT * 0.5))
            
            # Allow 50% overlap beyond chunk bounds
            world_x = max(chunk_left - w//2, min(world_x, chunk_right + w//2 - w))
            world_y = max(chunk_top - h//2, min(world_y, chunk_bottom + h//2 - h))
            
            # Check for collision
            move_range = (world_x - move_span, world_x + move_span)
            if has_platform_collision(world_x, world_y, w, h, moving, move_range, initial_check_list, placed):
                continue
            
            p = add_platform(
                world_x,
                world_y,
                w,
                h,
                moving=moving,
                move_range=move_range,
                speed=base_speed,
                surface_type=surface_type,
            )
            placed.append(p)
        
        # Add extra platforms in bottom-left quarter for chunks after the first
        # Bottom-left quarter: left half horizontally, bottom half vertically
        if i > 0:  # Skip first chunk
            bottom_left_count = 10
            for k in range(bottom_left_count):
                w, h = 140, 18
                moving = False
                # X position: left half of chunk
                world_x = chunk_left + random.randint(0, int(CHUNK_WIDTH * 0.5) - w)
                # Y position: bottom half of chunk
                world_y = chunk_top + CHUNK_HEIGHT * 0.5 + random.randint(0, int(CHUNK_HEIGHT * 0.5) - h)
                
                # Allow 50% overlap beyond chunk bounds
                world_x = max(chunk_left - w//2, min(world_x, chunk_right + w//2 - w))
                world_y = max(chunk_top - h//2, min(world_y, chunk_bottom + h//2 - h))
                
                # Check for collision
                move_range = (world_x - move_span, world_x + move_span)
                if has_platform_collision(world_x, world_y, w, h, moving, move_range, initial_check_list, placed):
                    continue
                
                move_range = (world_x - move_span, world_x + move_span)
                p = add_platform(
                    world_x,
                    world_y,
                    w,
                    h,
                    moving=moving,
                    move_range=move_range,
                    speed=base_speed,
                    surface_type=surface_type,
                )
                placed.append(p)

    return placed

def initial_platforms():
    platforms = pygame.sprite.Group()
    add_platform = make_add_platform(platforms, 0)
    # Add portal platform first
    portal_platform = add_platform(PORTAL_X - 60, PORTAL_PLATFORM_Y, 120, 18)
    # Generate grid platforms, checking collision with portal platform
    grid_platforms = add_grid_platforms(0, add_platform, surface_type="normal", existing_platforms=platforms)
    # Portal for initial spawn (on starter platform)
    portal = Portal(PORTAL_X, PORTAL_PLATFORM_Y)
    level_length = grid_level_length()
    
    # Add checkpoints at grid positions (every 3 grid cells)
    checkpoints = pygame.sprite.Group()
    layout = get_level_layout(0)
    for i, (gx, gy) in enumerate(layout):
        if i > 0 and i % 3 == 0:  # Every 3rd platform
            world_x = GRID_ORIGIN_X + (gx - 1) * CHUNK_WIDTH
            world_y = GRID_ORIGIN_Y - (gy - 1) * CHUNK_HEIGHT
            
            # Check for collision before adding checkpoint platform
            checkpoint_x = world_x - 60
            checkpoint_y = world_y
            checkpoint_w = 120
            checkpoint_h = 18
            collision = False
            for p in platforms:
                if check_platform_collision(
                    checkpoint_x, checkpoint_y, checkpoint_w, checkpoint_h, False, None,
                    p.rect.x, p.rect.y, p.rect.width, p.rect.height,
                    p.moving, p.move_range
                ):
                    collision = True
                    # Adjust position upward to avoid collision
                    checkpoint_y -= 100
                    break
            
            # Add platform underneath checkpoint
            add_platform(checkpoint_x, checkpoint_y, checkpoint_w, checkpoint_h)
            checkpoints.add(Checkpoint(world_x, checkpoint_y))
    
    # Create flag at chunk with highest X coordinate
    max_x_coord = max(layout, key=lambda coord: coord[0])  # Find chunk with max X
    flag_gx, flag_gy = max_x_coord
    flag_x = GRID_ORIGIN_X + (flag_gx - 1) * CHUNK_WIDTH + CHUNK_WIDTH // 2
    # Place at top of chunk (not bottom) - chunk top is at -gy*HEIGHT
    flag_y = GRID_ORIGIN_Y - flag_gy * CHUNK_HEIGHT + 50  # 50px from top of chunk
    
    # Check for collision before adding flag platform
    flag_platform_x = flag_x - 100
    flag_platform_y = flag_y
    flag_platform_w = 200
    flag_platform_h = 18
    collision = False
    for p in platforms:
        if check_platform_collision(
            flag_platform_x, flag_platform_y, flag_platform_w, flag_platform_h, False, None,
            p.rect.x, p.rect.y, p.rect.width, p.rect.height,
            p.moving, p.move_range
        ):
            collision = True
            # Adjust position upward to avoid collision
            flag_platform_y -= 100
            break
    
    end_platform = add_platform(flag_platform_x, flag_platform_y, flag_platform_w, flag_platform_h)
    flag = Flag(flag_x, end_platform.rect.top)
    
    # Return generated grid coordinates
    generated_grid_coords = set(layout)
    return platforms, checkpoints, portal, flag, generated_grid_coords


def gen_platforms_grid_aware(platforms, generated_chunks, camera_x, camera_y, level_index=0):
    """
    Generate platforms based on grid coordinates, continuing the pattern from LEVEL_GRID_LAYOUTS.
    Generated_chunks now tracks (gx, gy) tuples instead of linear X indices.
    """
    # Determine which grid cells are in view or near the player
    view_min_gx = max(1, int((camera_x - GEN_BUFFER) / CHUNK_WIDTH))
    view_max_gx = int((camera_x + WIDTH + GEN_AHEAD) / CHUNK_WIDTH) + 1
    view_min_gy = max(1, int((camera_y - GEN_BUFFER) / CHUNK_HEIGHT))
    view_max_gy = int((camera_y + HEIGHT + GEN_AHEAD) / CHUNK_HEIGHT) + 3
    
    # Get initial layout
    layout = get_level_layout(level_index)
    
    # Get all existing grid coords
    existing_coords = set(layout)
    existing_coords.update(generated_chunks)
    
    # Generate next coordinates if we need more
    max_gx_in_view = view_max_gx
    all_coords_list = list(existing_coords)
    
    # Check if we need to generate more coordinates ahead
    existing_max_gx = max((gx for gx, gy in all_coords_list), default=0)
    if max_gx_in_view > existing_max_gx:
        # Generate more coordinates to fill the view
        num_needed = max_gx_in_view - existing_max_gx + 5
        new_coords = get_next_grid_coordinates(all_coords_list, num_needed)
        existing_coords.update(new_coords)
        all_coords_list.extend(new_coords)
    
    # Place platforms at grid coordinates that are in view and not yet generated
    add_platform = make_add_platform(platforms, level_index)
    surface_type = "slippery" if level_index == 4 else "normal"
    move_span = int(CHUNK_WIDTH * 0.2)
    base_speed = 1 if surface_type == "slippery" else 2
    
    # Sort coordinates by gx to process in order
    sorted_coords = sorted(all_coords_list, key=lambda coord: coord[0])
    
    # Track placed platforms for collision detection
    placed_platforms = [p for p in platforms]
    
    for idx, (gx, gy) in enumerate(sorted_coords):
        # Skip if outside view range
        if not (view_min_gx <= gx <= view_max_gx):
            continue
        
        # Skip if already generated
        if (gx, gy) in generated_chunks:
            continue
        
        # Mark as generated
        generated_chunks.add((gx, gy))
        
        # Chunk boundaries
        chunk_left, chunk_right, chunk_top, chunk_bottom = get_chunk_boundaries(gx, gy)
        
        # Determine platform type based on level
        is_vertical = level_index == 2 and gx % 2 == 0
        
        # Multi-chunk overlap tracking: Check collisions against ALL existing platforms
        # This includes platforms from adjacent chunks that may extend into this chunk
        # Store platform info as dict for advanced collision detection
        existing_platform_data = []
        for p in platforms:
            existing_platform_data.append({
                'x': p.rect.x,
                'y': p.rect.y,
                'w': p.rect.width,
                'h': p.rect.height,
                'moving': p.moving,
                'move_range': p.move_range
            })
        
        # Balanced per-quadrant generation (max diff of 2 between quadrants)
        top_right_count = 12
        bottom_left_count = 10 if gx > 1 else 0
        total_target = PLATFORMS_PER_CHUNK + top_right_count + bottom_left_count
        base_target = total_target // 4
        remainder = total_target % 4
        target_counts = [base_target] * 4
        for q_index in random.sample(range(4), remainder):
            target_counts[q_index] += 1

        quad_counts = [0, 0, 0, 0]
        max_diff = 2

        mid_x = (chunk_left + chunk_right) // 2
        mid_y = (chunk_top + chunk_bottom) // 2
        quadrants = [
            (chunk_left, mid_x, chunk_top, mid_y),
            (mid_x, chunk_right, chunk_top, mid_y),
            (chunk_left, mid_x, mid_y, chunk_bottom),
            (mid_x, chunk_right, mid_y, chunk_bottom),
        ]

        attempts = 0
        max_attempts = total_target * 10

        def try_spawn_in_quadrant(quad_index, slot_index):
            left, right, top, bottom = quadrants[quad_index]

            if is_vertical:
                w, h = 18, 160
                moving = False
                min_x = left + int(PLATFORM_BUFFER * 0.3)
                max_x = right - int(PLATFORM_BUFFER * 0.7) - w
                min_y = top + h
                max_y = bottom - h
                if min_x > max_x or min_y > max_y:
                    return False
                world_x = random.randint(min_x, max_x)
                world_y = random.randint(min_y, max_y)
            else:
                w, h = 160, 18
                moving = level_index == 1 or (gx + slot_index) % 3 == 0
                quad_center_y = (top + bottom) / 2
                offset_from_center = random.gauss(0, (bottom - top) * 0.25)
                world_y = quad_center_y + offset_from_center
                world_x = random.randint(left, right - w)
                world_x += random.randint(-50, 50)

            world_x = max(chunk_left - w // 2, min(world_x, chunk_right + w // 2 - w))
            world_y = max(chunk_top - h // 2, min(world_y, chunk_bottom + h // 2 - h))

            move_range = (world_x - move_span, world_x + move_span)
            if has_platform_collision(world_x, world_y, w, h, moving, move_range, existing_platform_data, []):
                return False

            random_speed = random.uniform(1.0, 3.5) if moving else base_speed
            random_direction = random.choice([-1, 1]) if moving else 1
            add_platform(
                world_x,
                world_y,
                w,
                h,
                moving=moving,
                move_range=move_range,
                speed=random_speed,
                surface_type=surface_type,
                initial_direction=random_direction,
            )
            existing_platform_data.append({
                'x': world_x,
                'y': world_y,
                'w': w,
                'h': h,
                'moving': moving,
                'move_range': move_range
            })
            quad_counts[quad_index] += 1
            return True

        # Pass 1: Fill targets per quadrant
        while sum(quad_counts) < total_target and attempts < max_attempts:
            underfilled = [i for i in range(4) if quad_counts[i] < target_counts[i]]
            if not underfilled:
                break
            min_count = min(quad_counts[i] for i in underfilled)
            candidates = [i for i in underfilled if quad_counts[i] == min_count]
            quad_index = random.choice(candidates)
            slot_index = sum(quad_counts)
            attempts += 1
            try_spawn_in_quadrant(quad_index, slot_index)

        # Pass 2: Fallback to reach total while keeping spread within max_diff
        while sum(quad_counts) < total_target and attempts < max_attempts * 2:
            min_count = min(quad_counts)
            allowed = [i for i, count in enumerate(quad_counts) if count <= min_count + max_diff - 1]
            if not allowed:
                break
            quad_index = random.choice(allowed)
            slot_index = sum(quad_counts)
            attempts += 1
            try_spawn_in_quadrant(quad_index, slot_index)


def build_fixed_level(level_index):
    platforms = pygame.sprite.Group()
    checkpoints = pygame.sprite.Group()
    enemies = pygame.sprite.Group()
    orbs = pygame.sprite.Group()
    boosts = pygame.sprite.Group()
    portal = Portal(PORTAL_X, PORTAL_PLATFORM_Y)
    level_length = grid_level_length()

    add_platform = make_add_platform(platforms, level_index)
    # Portal platform should always be normal (not slippery)
    portal_platform = add_platform(PORTAL_X - 60, PORTAL_PLATFORM_Y, 120, 18, surface_type="normal")

    surface_type = "slippery" if level_index == 4 else "normal"
    # Generate grid platforms, checking collision with portal platform
    grid_platforms = add_grid_platforms(level_index, add_platform, surface_type=surface_type, existing_platforms=platforms)
    
    # Place end platform and flag at chunk with highest X coordinate
    layout = get_level_layout(level_index)
    max_x_coord = max(layout, key=lambda coord: coord[0])  # Find chunk with max X
    flag_gx, flag_gy = max_x_coord
    flag_x = GRID_ORIGIN_X + (flag_gx - 1) * CHUNK_WIDTH + CHUNK_WIDTH // 2
    flag_y = GRID_ORIGIN_Y - flag_gy * CHUNK_HEIGHT + 50
    
    # Check for collision before adding flag platform
    flag_platform_x = flag_x - 100
    flag_platform_y = flag_y
    flag_platform_w = 200
    flag_platform_h = 18
    collision = False
    for p in platforms:
        if check_platform_collision(
            flag_platform_x, flag_platform_y, flag_platform_w, flag_platform_h, False, None,
            p.rect.x, p.rect.y, p.rect.width, p.rect.height,
            p.moving, p.move_range
        ):
            collision = True
            # Adjust position upward to avoid collision
            flag_platform_y -= 100
            break
    
    # Flag platform should always be normal (not slippery) for better control
    end_platform = add_platform(flag_platform_x, flag_platform_y, flag_platform_w, flag_platform_h, surface_type="normal")

    if level_index == 3:
        # Only spawn enemies on stationary horizontal platforms
        enemy_platforms = [p for p in grid_platforms if p.rect.width >= p.rect.height and not p.moving]
        for p in enemy_platforms[1::3][:5]:
            enemies.add(Enemy(p, speed=2))
        
        # Spawn 2 orbs per chunk in the enemy level
        layout = get_level_layout(level_index)
        for gx, gy in layout:
            # Calculate chunk center
            chunk_left = GRID_ORIGIN_X + (gx - 1) * CHUNK_WIDTH
            chunk_top = GRID_ORIGIN_Y - gy * CHUNK_HEIGHT
            chunk_center_x = chunk_left + CHUNK_WIDTH // 2
            chunk_center_y = chunk_top + CHUNK_HEIGHT // 2
            
            # Spawn 2 orbs per chunk with different radii and speeds
            orbs.add(Orb(chunk_center_x, chunk_center_y, radius=100, speed=0.025))
            orbs.add(Orb(chunk_center_x, chunk_center_y, radius=150, speed=-0.018))

    if level_index == 5:
        candidates = [p for p in grid_platforms if p.rect.width >= 140]
        for p in candidates[:4]:
            boosts.add(JumpBoost(p))

    # Add checkpoints at grid positions (every 3 grid cells)
    layout = get_level_layout(level_index)
    for i, (gx, gy) in enumerate(layout):
        if i > 0 and i % 3 == 0:  # Every 3rd platform
            world_x = GRID_ORIGIN_X + (gx - 1) * CHUNK_WIDTH
            world_y = GRID_ORIGIN_Y - (gy - 1) * CHUNK_HEIGHT
            
            # Check for collision before adding checkpoint platform
            checkpoint_x = world_x - 60
            checkpoint_y = world_y
            checkpoint_w = 120
            checkpoint_h = 18
            collision = False
            for p in platforms:
                if check_platform_collision(
                    checkpoint_x, checkpoint_y, checkpoint_w, checkpoint_h, False, None,
                    p.rect.x, p.rect.y, p.rect.width, p.rect.height,
                    p.moving, p.move_range
                ):
                    collision = True
                    # Adjust position upward to avoid collision
                    checkpoint_y -= 100
                    break
            
            # Add platform underneath checkpoint - always normal (not slippery)
            add_platform(checkpoint_x, checkpoint_y, checkpoint_w, checkpoint_h, surface_type="normal")
            checkpoints.add(Checkpoint(world_x, checkpoint_y))

    flag = Flag(flag_x, end_platform.rect.top)
    generated_grid_coords = set(layout)
    return platforms, checkpoints, portal, flag, enemies, orbs, boosts, level_length, generated_grid_coords

# ---- Menu Rendering ----
def draw_main_menu(screen, menu_selected, pulse_amount):
    screen.fill(BG_COLOR)
    title = menu_font.render("Chicken Platformer", True, (0, 0, 0))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 50))
    
    levels = ["Level 1", "Level 2", "Level 3", "Level 4", "Level 5", "Level 6"]
    y_start = 150
    y_step = 60
    
    for i, level_name in enumerate(levels):
        y = y_start + i * y_step
        if i == menu_selected:
            glow_color = (255, int(200 + 50 * pulse_amount), 0)
            glow_text = small_menu_font.render(level_name, True, glow_color)
            screen.blit(glow_text, (WIDTH // 2 - glow_text.get_width() // 2 - 60, y))
            chicken_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(chicken_surf, (255, 200, 100), (15, 15), int(12 + 3 * pulse_amount))
            screen.blit(chicken_surf, (WIDTH // 2 + glow_text.get_width() // 2 - 80, y))
        else:
            text = small_menu_font.render(level_name, True, (50, 50, 50))
            screen.blit(text, (WIDTH // 2 - text.get_width() // 2 - 60, y))

def draw_win_menu(screen, level_index, elapsed, menu_selected, pulse_amount):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))
    
    if level_index == 5:
        title = big_font.render("All Levels Complete!", True, (255, 255, 255))
    else:
        title = big_font.render("Level Complete!", True, (255, 255, 255))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))
    
    time_text = font.render(f"Time: {elapsed}s  Best: {best_time if best_time != float('inf') else '-'}s", True, (200, 200, 200))
    screen.blit(time_text, (WIDTH // 2 - time_text.get_width() // 2, 200))
    
    options = ["Next Level", "Main Menu"]
    if level_index == 5:
        options = ["Main Menu"]
    
    y_start = 300
    y_step = 80
    
    for i, option in enumerate(options):
        y = y_start + i * y_step
        if i == menu_selected:
            glow_color = (255, int(200 + 50 * pulse_amount), 0)
            text = big_font.render(option, True, glow_color)
        else:
            text = big_font.render(option, True, (255, 255, 255))
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, y))

# ---- Main Game Loop: Modified reset and camera logic for Reset Issue (Fix #1) and Camera Jitter (Fix #3) ----
def main():
    global best_time
    pygame.display.set_caption("Chicken Platformer - Reach the Flag!")
    level_index = 0
    developer_mode = False
    game_state = MENU
    menu_selected = 0
    win_menu_selected = 0
    pulse_timer = 0
    platforms, checkpoints, portal, flag, generated_chunks = initial_platforms()
    enemies = pygame.sprite.Group()
    orbs = pygame.sprite.Group()
    boosts = pygame.sprite.Group()
    use_procedural = True
    level_length = grid_level_length()
    player = Chicken(PORTAL_X, PORTAL_PLATFORM_Y - 24)
    particles = pygame.sprite.Group()
    all_sprites = pygame.sprite.Group()
    all_sprites.add(player)
    last_checkpoint = (PORTAL_X, PORTAL_PLATFORM_Y - 24)
    camera_x = 0
    camera_y = 0
    start_time = pygame.time.get_ticks()
    won = False

    def load_level(new_level_index, spawn_at_checkpoint=False):
        nonlocal level_index, platforms, checkpoints, portal, enemies, orbs, boosts, generated_chunks, player, flag
        nonlocal last_checkpoint, camera_x, camera_y, start_time, won, use_procedural, level_length

        level_index = new_level_index
        platforms, checkpoints, portal, flag, enemies, orbs, boosts, level_length, generated_chunks = build_fixed_level(level_index)
        use_procedural = True
        start_pos = (PORTAL_X, PORTAL_PLATFORM_Y - 24)

        if not spawn_at_checkpoint:
            last_checkpoint = start_pos
        spawn_x, spawn_y = last_checkpoint if spawn_at_checkpoint else start_pos
        player = Chicken(spawn_x, spawn_y)
        player.developer_mode = developer_mode
        if not spawn_at_checkpoint:
            camera_x = 0
            camera_y = 0
        else:
            camera_x = max(0, player.rect.centerx - WIDTH // CAMERA_OFFSET_X_RATIO)
            camera_y = max(0, player.rect.centery - HEIGHT // 2)
        start_time = pygame.time.get_ticks()
        won = False

    def reset(to_checkpoint=True):
        nonlocal player, platforms, flag
        load_level(level_index, spawn_at_checkpoint=to_checkpoint)
        return player, platforms, flag

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        pulse_timer += dt * 5
        pulse_amount = abs(math.sin(pulse_timer))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game_state == MENU:
                        running = False
                    elif game_state == PLAYING:
                        game_state = MENU
                        menu_selected = 0
                    elif game_state == WIN_MENU:
                        game_state = MENU
                        menu_selected = 0
                elif game_state == MENU:
                    if event.key == pygame.K_UP:
                        menu_selected = (menu_selected - 1) % 6
                    elif event.key == pygame.K_DOWN:
                        menu_selected = (menu_selected + 1) % 6
                    elif event.key == pygame.K_RETURN:
                        load_level(menu_selected)
                        game_state = PLAYING
                        menu_selected = 0
                elif game_state == WIN_MENU:
                    options_count = 1 if (level_index == 5) else 2
                    if event.key == pygame.K_UP:
                        win_menu_selected = (win_menu_selected - 1) % options_count
                    elif event.key == pygame.K_DOWN:
                        win_menu_selected = (win_menu_selected + 1) % options_count
                    elif event.key == pygame.K_RETURN:
                        if level_index == 5:
                            game_state = MENU
                            menu_selected = 0
                        elif win_menu_selected == 0:
                            load_level(level_index + 1)
                            game_state = PLAYING
                            win_menu_selected = 0
                        else:
                            game_state = MENU
                            menu_selected = 0
                elif game_state == PLAYING:
                    if event.key == pygame.K_F1:
                        developer_mode = not developer_mode
                        player.developer_mode = developer_mode
                    elif event.key in (pygame.K_UP, pygame.K_SPACE):
                        if player.can_jump():
                            if boosts and player.on_ground:
                                for b in boosts:
                                    if player.rect.colliderect(b.rect):
                                        player.boost_jump_ready = True
                                        break
                            player.jump()
                        else:
                            player.jump_buffer = 100
                    elif event.key == pygame.K_r:
                        player, platforms, flag = reset(to_checkpoint=True)

        if game_state == MENU:
            draw_main_menu(screen, menu_selected, pulse_amount)
        elif game_state == PLAYING:
            keys = pygame.key.get_pressed()
            player.desired_vx = 0
            if keys[pygame.K_LEFT]:
                player.desired_vx = -PLAYER_SPEED
                player.facing_right = False
            if keys[pygame.K_RIGHT]:
                player.desired_vx = PLAYER_SPEED
                player.facing_right = True

            target_camera_x = player.rect.centerx - WIDTH // CAMERA_OFFSET_X_RATIO
            target_camera_y = player.rect.centery - HEIGHT // 2
            # Fix #3: Faster smoothing and clamp camera
            camera_x += (target_camera_x - camera_x) * CAMERA_SMOOTHING
            camera_x = max(0, min(camera_x, level_length - WIDTH + 200))
            camera_y += (target_camera_y - camera_y) * CAMERA_SMOOTHING
            # No clamping - allow camera to follow player infinitely up and down

            # Generate platforms using grid-aware system
            if use_procedural:
                gen_platforms_grid_aware(platforms, generated_chunks, camera_x, camera_y, level_index)

            for p in list(platforms):
                p.update(camera_x)
                if use_procedural:
                    # Remove platforms outside the viewport (considering both X and Y)
                    # Account for platforms that may extend beyond chunk boundaries (50% overlap)
                    removal_buffer = GEN_BUFFER + 100  # Extra buffer for overlapping platforms
                    if (p.rect.right < camera_x - removal_buffer or 
                        p.rect.top > camera_y + HEIGHT + removal_buffer) and p.rect.height != 40:
                        platforms.remove(p)

            for e in enemies:
                e.update()

            for o in orbs:
                o.update()

            for b in boosts:
                b.update()

            particles.update()
            player.update(platforms, particles, boosts)

            for cp in checkpoints:
                if not cp.activated and player.rect.centerx > cp.x:
                    cp.activate()   
                    last_checkpoint = (cp.x, cp.y)

            if player.rect.colliderect(flag.rect) and not won:
                if level_index < 5:
                    load_level(level_index + 1, spawn_at_checkpoint=False)
                    continue
                won = True
                win_time = pygame.time.get_ticks()
                elapsed = (win_time - start_time) // 1000
                best_time = min(best_time, elapsed)
                game_state = WIN_MENU
                win_menu_selected = 0

            if pygame.sprite.spritecollide(player, enemies, False):
                player, platforms, flag = reset(to_checkpoint=True)

            if pygame.sprite.spritecollide(player, orbs, False):
                player, platforms, flag = reset(to_checkpoint=True)

            if player.rect.top > HEIGHT + 300 and player.vy > 0:
                print(f"Reset triggered: y={player.rect.y}, vy={player.vy}, on_ground={player.on_ground}")
                player, platforms, flag = reset(to_checkpoint=True)

            screen.fill(BG_COLOR)
            for i in range(6):
                cx = (i * CLOUD_SPACING - camera_x * 0.2) % (WIDTH + 200) - 100
                cy = CLOUD_Y_OFFSET + (i % 3) * CLOUD_Y_STEP - camera_y * 0.3
                pygame.draw.ellipse(screen, (255, 255, 255, 180), (cx, cy, CLOUD_WIDTH, CLOUD_HEIGHT))
            for p in platforms:
                screen.blit(p.image, (p.rect.x - camera_x, p.rect.y - camera_y))
            for cp in checkpoints:
                screen.blit(cp.image, (cp.rect.x - camera_x, cp.rect.y - camera_y))
            screen.blit(portal.image, (portal.rect.x - camera_x, portal.rect.y - camera_y))
            screen.blit(flag.image, (flag.rect.x - camera_x, flag.rect.y - camera_y))
            for e in enemies:
                screen.blit(e.image, (e.rect.x - camera_x, e.rect.y - camera_y))
            for o in orbs:
                screen.blit(o.image, (o.rect.x - camera_x, o.rect.y - camera_y))
            for b in boosts:
                screen.blit(b.image, (b.rect.x - camera_x, b.rect.y - camera_y))
            for p in particles:
                screen.blit(p.image, (p.rect.x - camera_x, p.rect.y - camera_y))
            screen.blit(player.image, (player.rect.x - camera_x, player.rect.y - camera_y))

            elapsed = (pygame.time.get_ticks() - start_time) // 1000
            level_text = f"Level {level_index + 1}/6"
            dev_text = "  DevMode" if developer_mode else ""
            info = font.render(f"{level_text}  Time {elapsed}s  Best {best_time if best_time != float('inf') else '-'}s  X {player.rect.centerx}{dev_text}  Press R to restart  Esc to quit", True, (30, 30, 30))
            screen.blit(info, (14, 14))
        elif game_state == WIN_MENU:
            elapsed = (pygame.time.get_ticks() - start_time) // 1000
            screen.fill(BG_COLOR)
            draw_win_menu(screen, level_index, elapsed, win_menu_selected, pulse_amount)

        pygame.display.flip()

    pygame.quit()
    sys.exit()
    
if __name__ == "__main__":
    main()