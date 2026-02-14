# new_chicken_platformer.py
# Platformer with procedural platform generation, endpoint flag, and faster jump refresh
# Requires: pip install pygame

import pygame
import sys
import random
import math

# ---- Config ----
WIDTH, HEIGHT = 900, 600
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
LEVEL_LENGTH = 14200  # Legacy length; use grid_level_length() for grid-based levels
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
CHUNK_WIDTH = 700
CHUNK_HEIGHT = 80
PLATFORMS_PER_CHUNK = 7
PLATFORM_BUFFER = 150
LEVEL_CHUNKS_X = 20
LEVEL_CHUNKS_Y = 5

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
    def __init__(self, x, y, w, h, moving=False, move_range=(0, 0), speed=0, surface_type="normal", slip_duration_ms=None):
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
        self.direction = 1
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

    def update(self):
        self.rect.x += self.direction * self.speed
        if self.rect.left < self.min_x or self.rect.right > self.max_x:
            self.direction *= -1
            self.rect.x += self.direction * self.speed
        self.rect.bottom = self.platform.rect.top

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
        # Use smaller steps for more precise collision detection
        steps = max(1, int(abs(self.vy) / 10))  # Break movement into smaller steps
        step_vy = self.vy / steps
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

        step_vx = self.vx / steps
        
        platform_vx = 0
        if prev_on_ground and prev_platform and prev_platform.moving:
            platform_vx = prev_platform.direction * prev_platform.speed
        
        for _ in range(steps):
            # Apply character velocity plus platform velocity if standing on it
            self.pos_x += step_vx + platform_vx
            self.rect.x = int(self.pos_x)
            self.collide_horizontal(platforms, ignore_platform=prev_platform if prev_on_ground else None)
            self.pos_y += step_vy
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
    None: BASE_GRID_LAYOUT,
    0: BASE_GRID_LAYOUT,
    1: BASE_GRID_LAYOUT,
    2: BASE_GRID_LAYOUT,
    3: BASE_GRID_LAYOUT,
    4: BASE_GRID_LAYOUT,
}

def grid_level_length():
    return GRID_ORIGIN_X + (LEVEL_CHUNKS_X * CHUNK_WIDTH)

def level_scale_for_index(level_index):
    if level_index is None:
        return 0.9
    return max(0.72, 0.9 - (level_index * 0.04))

def make_add_platform(platforms, level_index):
    level_scale = level_scale_for_index(level_index)

    def add_platform(x, y, w, h, moving=False, move_range=(0, 0), speed=0, surface_type="normal"):
        sw = max(12, int(w * level_scale))
        sh = max(12, int(h * level_scale))
        p = Platform(x, y, sw, sh, moving=moving, move_range=move_range, speed=speed, surface_type=surface_type)
        platforms.add(p)
        return p

    return add_platform

def get_level_layout(level_index):
    return LEVEL_GRID_LAYOUTS.get(level_index, BASE_GRID_LAYOUT)

def add_grid_platforms(level_index, add_platform, surface_type="normal"):
    placed = []
    layout = get_level_layout(level_index)
    move_span = int(CHUNK_WIDTH * 0.2)
    base_speed = 1 if surface_type == "slippery" else 2

    for i, (gx, gy) in enumerate(layout):
        world_x = GRID_ORIGIN_X + (gx - 1) * CHUNK_WIDTH
        world_y = GRID_ORIGIN_Y - (gy - 1) * CHUNK_HEIGHT
        is_vertical = level_index == 1 and gx % 2 == 0

        if is_vertical:
            w, h = 18, 160
            moving = False
        else:
            w, h = 160, 18
            moving = level_index == 0 or i % 3 == 0

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
    ground_y = HEIGHT - 40
    add_platform = make_add_platform(platforms, None)
    add_platform(PORTAL_X - 60, PORTAL_PLATFORM_Y, 120, 18)
    add_grid_platforms(None, add_platform, surface_type="normal")
    # Portal for initial spawn (on starter platform)
    portal = Portal(PORTAL_X, PORTAL_PLATFORM_Y)
    level_length = grid_level_length()
    # Platform for the end goal flag
    add_platform(level_length - 150, 300, 200, 18)
    # Add checkpoints with platforms underneath them
    checkpoints = pygame.sprite.Group()
    for x in range(CHECKPOINT_SPACING, level_length, CHECKPOINT_SPACING):
        checkpoints.add(Checkpoint(x, ground_y))
        # Add a platform underneath each checkpoint (20 pixels wide, so make platform slightly wider)
        add_platform(x - 15, ground_y, 50, 16)
    return platforms, checkpoints, portal


def gen_platforms_for_range(platforms, existing_xs, start_x, end_x, player_x, level_length):
    CHUNK_W = CHUNK_WIDTH
    PLATFORMS_PER_CHUNK_VAL = PLATFORMS_PER_CHUNK
    
    cx_start = start_x // CHUNK_W
    cx_end = end_x // CHUNK_W
    
    for cx in range(cx_start, cx_end + 1):
        if cx in existing_xs:
            continue
        existing_xs.add(cx)
        
        base_x = cx * CHUNK_W + 200
        # Find the highest platform in existing platforms to ensure connectivity
        max_existing_y = HEIGHT - 140
        for p in platforms:
            if cx * CHUNK_W <= p.rect.centerx <= (cx + 1) * CHUNK_W + 100:
                max_existing_y = min(max_existing_y, p.rect.top)
        
        last_y = max_existing_y
        max_jump_height = abs(PLAYER_JUMP_SPEED) ** 2 / (2 * GRAVITY)
        
        # Scale difficulty based on player progress
        progress = min(1.0, player_x / max(1, level_length))
        
        attempts = 0
        platforms_created = 0
        max_attempts = PLATFORMS_PER_CHUNK_VAL * 5
        
        # Keep trying until we create enough platforms or run out of attempts
        while platforms_created < PLATFORMS_PER_CHUNK_VAL and attempts < max_attempts:
            attempts += 1
            
            w = random.randint(80 - int(20 * progress), 180 - int(40 * progress))
            h = 16
            x = base_x + random.randint(-200, CHUNK_W - 50)
            # Ensure platform is reachable from last platform
            y = random.randint(
                max(120, last_y - int(max_jump_height)), 
                min(HEIGHT - 140, last_y + int(1.5 * max_jump_height))
            )
            
            new_rect = pygame.Rect(x, y, w, h)
            overlap = False
            buffer = PLATFORM_BUFFER
            
            for p in platforms:
                buffered_rect = p.rect.inflate(buffer, buffer)
                if new_rect.colliderect(buffered_rect):
                    overlap = True
                    break
            
            if not overlap:
                last_y = y
                platforms_created += 1

                if random.random() < 0.15:
                    move_min = max(x - 80, cx * CHUNK_W)
                    move_max = min(x + 120, (cx + 1) * CHUNK_W + 100)
                    speed = random.randint(1, 3 + int(2 * progress))
                    p = Platform(x, y, w, h, moving=True, move_range=(move_min, move_max), speed=speed)
                else:
                    p = Platform(x, y, w, h)
                platforms.add(p)

def build_fixed_level(level_index):
    platforms = pygame.sprite.Group()
    checkpoints = pygame.sprite.Group()
    enemies = pygame.sprite.Group()
    boosts = pygame.sprite.Group()
    ground_y = HEIGHT - 40
    portal = Portal(PORTAL_X, PORTAL_PLATFORM_Y)
    level_length = grid_level_length()

    add_platform = make_add_platform(platforms, level_index)
    add_platform(PORTAL_X - 60, PORTAL_PLATFORM_Y, 120, 18)

    surface_type = "slippery" if level_index == 3 else "normal"
    grid_platforms = add_grid_platforms(level_index, add_platform, surface_type=surface_type)
    end_platform = add_platform(level_length - 220, 260, 180, 18, surface_type=surface_type)

    if level_index == 2:
        enemy_platforms = [p for p in grid_platforms if p.rect.width >= p.rect.height]
        for p in enemy_platforms[1::3][:5]:
            enemies.add(Enemy(p, speed=2))

    if level_index == 4:
        candidates = [p for p in grid_platforms if p.rect.width >= 140]
        for p in candidates[:4]:
            boosts.add(JumpBoost(p))

    for x in range(800, level_length - 200, 800):
        checkpoints.add(Checkpoint(x, ground_y))
        add_platform(x - 15, ground_y, 50, 16)

    flag = Flag(level_length - 50, end_platform.rect.top)
    return platforms, checkpoints, portal, flag, enemies, boosts, level_length

# ---- Menu Rendering ----
def draw_main_menu(screen, menu_selected, pulse_amount):
    screen.fill(BG_COLOR)
    title = menu_font.render("Chicken Platformer", True, (0, 0, 0))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 50))
    
    levels = ["Warmup", "Level 1", "Level 2", "Level 3", "Level 4", "Level 5"]
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
    
    if level_index == 4:
        title = big_font.render("All Levels Complete!", True, (255, 255, 255))
    else:
        title = big_font.render("Level Complete!", True, (255, 255, 255))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))
    
    time_text = font.render(f"Time: {elapsed}s  Best: {best_time if best_time != float('inf') else '-'}s", True, (200, 200, 200))
    screen.blit(time_text, (WIDTH // 2 - time_text.get_width() // 2, 200))
    
    options = ["Next Level", "Main Menu"]
    if level_index == 4:
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
    level_index = None
    developer_mode = False
    game_state = MENU
    menu_selected = 0
    win_menu_selected = 0
    pulse_timer = 0
    platforms, checkpoints, portal = initial_platforms()
    enemies = pygame.sprite.Group()
    boosts = pygame.sprite.Group()
    generated_chunks = set()
    use_procedural = True
    level_length = grid_level_length()
    player = Chicken(PORTAL_X, PORTAL_PLATFORM_Y - 24)
    flag = Flag(level_length - 50, 300)
    particles = pygame.sprite.Group()
    all_sprites = pygame.sprite.Group()
    all_sprites.add(player)
    last_checkpoint = (PORTAL_X, PORTAL_PLATFORM_Y - 24)
    camera_x = 0
    start_time = pygame.time.get_ticks()
    won = False

    def load_level(new_level_index, spawn_at_checkpoint=False):
        nonlocal level_index, platforms, checkpoints, portal, enemies, boosts, generated_chunks, player, flag
        nonlocal last_checkpoint, camera_x, start_time, won, use_procedural, level_length

        level_index = new_level_index
        if level_index is None:
            platforms, checkpoints, portal = initial_platforms()
            enemies = pygame.sprite.Group()
            boosts = pygame.sprite.Group()
            use_procedural = True
            level_length = grid_level_length()
            flag = Flag(level_length - 50, 300)
            generated_chunks = set()
            start_pos = (PORTAL_X, PORTAL_PLATFORM_Y - 24)
        else:
            platforms, checkpoints, portal, flag, enemies, boosts, level_length = build_fixed_level(level_index)
            use_procedural = True
            generated_chunks = set()
            start_pos = (PORTAL_X, PORTAL_PLATFORM_Y - 24)

        if not spawn_at_checkpoint:
            last_checkpoint = start_pos
        spawn_x, spawn_y = last_checkpoint if spawn_at_checkpoint else start_pos
        player = Chicken(spawn_x, spawn_y)
        player.developer_mode = developer_mode
        if not spawn_at_checkpoint:
            camera_x = 0
        else:
            camera_x = max(0, player.rect.centerx - WIDTH // CAMERA_OFFSET_X_RATIO)
        start_time = pygame.time.get_ticks()
        won = False

    def ensure_portal_platform():
        portal_platform = pygame.Rect(PORTAL_X - 60, PORTAL_PLATFORM_Y, 120, 18)
        if not any(p.rect.colliderect(portal_platform) for p in platforms):
            platforms.add(Platform(PORTAL_X - 60, PORTAL_PLATFORM_Y, 120, 18))

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
                        load_level(menu_selected if menu_selected > 0 else None)
                        game_state = PLAYING
                        menu_selected = 0
                elif game_state == WIN_MENU:
                    options_count = 1 if (level_index == 4) else 2
                    if event.key == pygame.K_UP:
                        win_menu_selected = (win_menu_selected - 1) % options_count
                    elif event.key == pygame.K_DOWN:
                        win_menu_selected = (win_menu_selected + 1) % options_count
                    elif event.key == pygame.K_RETURN:
                        if level_index == 4:
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
            # Fix #3: Faster smoothing and clamp camera
            camera_x += (target_camera_x - camera_x) * CAMERA_SMOOTHING
            camera_x = max(0, min(camera_x, level_length - WIDTH + 200))

            gen_start = camera_x
            gen_end = camera_x + GEN_AHEAD

            if use_procedural:
                gen_platforms_for_range(platforms, generated_chunks, int(gen_start), int(gen_end), player.rect.centerx, level_length)

            for p in list(platforms):
                p.update(camera_x)
                if use_procedural:
                    if p.rect.right < camera_x - GEN_BUFFER and p.rect.height != 40:
                        platforms.remove(p)

            for e in enemies:
                e.update()

            for b in boosts:
                b.update()

            particles.update()
            player.update(platforms, particles, boosts)

            for cp in checkpoints:
                if not cp.activated and player.rect.centerx > cp.x:
                    cp.activate()   
                    last_checkpoint = (cp.x, HEIGHT - 120)

            if player.rect.colliderect(flag.rect) and not won:
                if level_index is None:
                    load_level(0, spawn_at_checkpoint=False)
                    continue
                if level_index < 4:
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

            if player.rect.top > HEIGHT + 300 and player.vy > 0:
                print(f"Reset triggered: y={player.rect.y}, vy={player.vy}, on_ground={player.on_ground}")
                player, platforms, flag = reset(to_checkpoint=True)

            screen.fill(BG_COLOR)
            for i in range(6):
                cx = (i * CLOUD_SPACING - camera_x * 0.2) % (WIDTH + 200) - 100
                pygame.draw.ellipse(screen, (255, 255, 255, 180), (cx, CLOUD_Y_OFFSET + (i % 3) * CLOUD_Y_STEP, CLOUD_WIDTH, CLOUD_HEIGHT))
            for p in platforms:
                screen.blit(p.image, (p.rect.x - camera_x, p.rect.y))
            for cp in checkpoints:
                screen.blit(cp.image, (cp.rect.x - camera_x, cp.rect.y))
            screen.blit(portal.image, (portal.rect.x - camera_x, portal.rect.y))
            screen.blit(flag.image, (flag.rect.x - camera_x, flag.rect.y))
            for e in enemies:
                screen.blit(e.image, (e.rect.x - camera_x, e.rect.y))
            for b in boosts:
                screen.blit(b.image, (b.rect.x - camera_x, b.rect.y))
            for p in particles:
                screen.blit(p.image, (p.rect.x - camera_x, p.rect.y))
            screen.blit(player.image, (player.rect.x - camera_x, player.rect.y))

            elapsed = (pygame.time.get_ticks() - start_time) // 1000
            if level_index is None:
                level_text = "Warmup"
            else:
                level_text = f"Level {level_index + 1}/5"
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