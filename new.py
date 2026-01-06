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
BG_COLOR = (135, 206, 235)  # Sky blue
GEN_AHEAD = 1400  # Pixels ahead of camera to generate platforms
GEN_BUFFER = 400  # Keep platforms behind this distance before removing
LEVEL_LENGTH = 5000  # Total level endpoint x coordinate

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 20)
big_font = pygame.font.SysFont("Arial", 56)

# ---- New: Best Time Tracking ----
best_time = float('inf')  # Global to store best time

# ---- New: Particle Effect for Landing ----
class Particle(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (200, 200, 200), (4, 4), 4)
        self.rect = self.image.get_rect(center=(x, y))
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 0)
        self.lifetime = 20  # Frames

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()

# ---- Helper Classes ----
class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h, moving=False, move_range=(0, 0), speed=0):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.image.fill(PLATFORM_COLOR)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.moving = moving
        self.speed = speed
        self.move_range = move_range
        self.direction = 1

    def update(self, camera_x):
        if self.moving:
            self.rect.x += self.direction * self.speed
            if self.rect.x < self.move_range[0] or self.rect.x > self.move_range[1]:
                self.direction *= -1
                self.rect.x += self.direction * self.speed

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

    def update(self, camera_x):
        pass

# ---- New: Hole Class for Ground Holes ----
class Hole(pygame.sprite.Sprite):
    def __init__(self, x, width, ground_y):
        super().__init__()
        self.image = pygame.Surface((width, 40))
        self.image.fill((50, 50, 50))  # Dark gray for visibility
        self.rect = self.image.get_rect(topleft=(x, ground_y))

class Chicken(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.base_w, self.base_h = 48, 48
        self.image = pygame.Surface((self.base_w, self.base_h), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.facing_right = True
        self.flap_phase = 0.0
        self.last_jump_time = -9999
        self.was_on_ground = False
        self.last_platform = None  # New: Track the platform the player is standing on
        self.jump_buffer = 0
        
    def update_physics(self, platforms, particles):
        # New: Use smaller steps for more precise collision detection
        steps = max(1, int(abs(self.vy) / 10))  # Break movement into smaller steps
        step_vy = self.vy / steps
        step_vx = self.vx / steps
        self.on_ground = False  # Reset on_ground each update
        for _ in range(steps):
            self.rect.x += int(step_vx)
            self.collide_horizontal(platforms)
            self.rect.y += int(step_vy)
            self.collide_vertical(platforms, particles)
        self.vy += GRAVITY
        # New: Move with the platform if standing on it
        if self.on_ground and self.last_platform and self.last_platform.moving:
            self.rect.x += self.last_platform.direction * self.last_platform.speed

        # New: Move with the platform if standing on it
        if self.on_ground and self.last_platform and self.last_platform.moving:
            self.rect.x += self.last_platform.direction * self.last_platform.speed

    def collide_horizontal(self, platforms):
        hits = pygame.sprite.spritecollide(self, platforms, False)
        for p in hits:
            if self.vx > 0:
                self.rect.right = p.rect.left
            elif self.vx < 0:
                self.rect.left = p.rect.right
            self.vx = 0


    def collide_vertical(self, platforms, particles):
        hits = pygame.sprite.spritecollide(self, platforms, False)
        self.last_platform = None  # Reset last platform
        
        for p in hits:
            if self.vy > 0:
                # Only spawn particles if we were NOT on ground last frame AND we are falling
                # This ensures it only triggers on the landing transition, not every frame
                if not self.was_on_ground and self.vy > 5:  # Add velocity threshold to avoid micro-bounces
                    if len(particles) < 50:
                        for _ in range(5):
                            particles.add(Particle(self.rect.centerx, self.rect.bottom))
                
                self.rect.bottom = p.rect.top
                self.on_ground = True
                self.last_platform = p  # Track the platform we landed on
            elif self.vy < 0:
                self.rect.top = p.rect.bottom
            self.vy = 0  # Reset velocity for both cases to stabilize physics
        
        self.was_on_ground = self.on_ground


    def can_jump(self):
        return self.on_ground

    def jump(self):
        if self.can_jump():
            self.vy = PLAYER_JUMP_SPEED
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

    def update(self, platforms, particles):
        speed_factor = min(1.0, abs(self.vx) / PLAYER_SPEED)
        self.flap_phase += 0.25 + 0.8 * speed_factor
        self.draw_chicken()
        self.update_physics(platforms, particles)
        if self.jump_buffer > 0:
            self.jump_buffer -= clock.get_time()
            if self.can_jump() and self.jump_buffer > 0:
                self.jump()

# ---- Level Generation ----
def initial_platforms():
    platforms = pygame.sprite.Group()
    holes = pygame.sprite.Group()
    ground_y = HEIGHT - 40
    # Change: Create segmented ground with holes
    segment_width = 400
    hole_width = 100
    for x in range(0, LEVEL_LENGTH + 400, segment_width + hole_width):
        # Add ground segment
        platforms.add(Platform(x, ground_y, segment_width, 40))
        # Add hole after segment (except at the end to ensure flag is on ground)
        if x + segment_width < LEVEL_LENGTH:
            holes.add(Hole(x + segment_width, hole_width, ground_y))
    # Ensure flag has a platform
    platforms.add(Platform(LEVEL_LENGTH - 100, ground_y, 200, 40))
    starter = [
        (120, 460, 160, 18),
        (320, 380, 130, 18),
        (520, 320, 160, 18),
        (740, 420, 130, 18),
        (200, 260, 140, 18),
        (420, 200, 180, 18),
    ]
    for x, y, w, h in starter:
        platforms.add(Platform(x, y, w, h))
    moving = Platform(600, 520, 120, 16, moving=True, move_range=(520, 760), speed=2)
    platforms.add(moving)
    checkpoints = pygame.sprite.Group()
    for x in range(1000, LEVEL_LENGTH, 1000):
        checkpoints.add(Checkpoint(x, ground_y))
    return platforms, checkpoints, holes  # Change: Return holes group


# def gen_platforms_for_range(platforms, existing_xs, start_x, end_x, player_x):
#     CHUNK_W = 700 # Increased from 500 to 700 for wider horizontal spacing
#     cx_start = start_x // CHUNK_W
#     cx_end = end_x // CHUNK_W
#     last_y = HEIGHT - 140  # Track last platform y for reachability
#     max_jump_height = abs(PLAYER_JUMP_SPEED) ** 2 / (2 * GRAVITY)  # Fix #2: Calculate max jump height
#     for cx in range(cx_start, cx_end + 1):
#         if cx in existing_xs:
#             continue
#         existing_xs.add(cx)
#         base_x = cx * CHUNK_W + 200
#         for i in range(random.randint(5,10)): 
#             # Scale difficulty based on player progress
#             progress = min(1.0, player_x / LEVEL_LENGTH)
#             w = random.randint(80 - int(20 * progress), 180 - int(40 * progress))
#             h = 16
#             x = base_x + random.randint(-200, CHUNK_W - 50) # Wider x-range 
#             # Tighter y-range based on max jump height
#             # Wider y-range for more vertical spread, still reachable
#             y = random.randint(max(120, last_y - int(max_jump_height)), min(HEIGHT - 140, last_y + int(2.0 * max_jump_height)))
#             new_rect = pygame.Rect(x, y, w, h)
#             overlap = False # Check for overlap with existing platforms
#             buffer = 200 # Minimum distance between platforms
#             for p in platforms:
#                 buffered_rect = p.rect.inflate(buffer, buffer)  # Add buffer around existing platform
#                 if new_rect.colliderect(buffered_rect):
#                     overlap = True
#                     break
#             if not overlap:
#                 last_y = y
#                 if random.random() < 0.15:
#                     move_min = max(x - 80, cx * CHUNK_W)
#                     move_max = min(x + 120, (cx + 1) * CHUNK_W + 100)
#                     speed = random.randint(1, 3 + int(2 * progress))
#                     p = Platform(x, y, w, h, moving=True, move_range=(move_min, move_max), speed=speed)
#                 else:
#                     p = Platform(x, y, w, h)
#                 platforms.add(p)

def gen_platforms_for_range(platforms, existing_xs, start_x, end_x, player_x):
    CHUNK_W = 700
    PLATFORMS_PER_CHUNK = 7  # Fixed count instead of random
    
    cx_start = start_x // CHUNK_W
    cx_end = end_x // CHUNK_W
    
    for cx in range(cx_start, cx_end + 1):
        if cx in existing_xs:
            continue
        existing_xs.add(cx)
        
        base_x = cx * CHUNK_W + 200
        last_y = HEIGHT - 140
        max_jump_height = abs(PLAYER_JUMP_SPEED) ** 2 / (2 * GRAVITY)
        
        # Scale difficulty based on player progress
        progress = min(1.0, player_x / LEVEL_LENGTH)
        
        attempts = 0
        platforms_created = 0
        max_attempts = PLATFORMS_PER_CHUNK * 5  # Allow multiple attempts
        
        # Keep trying until we create enough platforms or run out of attempts
        while platforms_created < PLATFORMS_PER_CHUNK and attempts < max_attempts:
            attempts += 1
            
            w = random.randint(80 - int(20 * progress), 180 - int(40 * progress))
            h = 16
            x = base_x + random.randint(-200, CHUNK_W - 50)
            y = random.randint(
                max(120, last_y - int(max_jump_height)), 
                min(HEIGHT - 140, last_y + int(2.0 * max_jump_height))
            )
            
            new_rect = pygame.Rect(x, y, w, h)
            overlap = False
            
            # Reduced buffer for less rejection
            buffer = 150  # Changed from 200 to 150
            
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

# ---- Main Game Loop: Modified reset and camera logic for Reset Issue (Fix #1) and Camera Jitter (Fix #3) ----
def main():
    global best_time
    pygame.display.set_caption("Chicken Platformer - Reach the Flag!")
    platforms, checkpoints, holes = initial_platforms()
    generated_chunks = set()
    player = Chicken(100, HEIGHT - 120)
    flag = Flag(LEVEL_LENGTH, HEIGHT - 40)
    particles = pygame.sprite.Group()
    all_sprites = pygame.sprite.Group()
    all_sprites.add(player)
    last_checkpoint = (100, HEIGHT - 120)
    camera_x = 0
    start_time = pygame.time.get_ticks()
    won = False

    def reset(to_checkpoint=True):
        nonlocal platforms, checkpoints, generated_chunks, player, flag, start_time, won, last_checkpoint
        platforms, checkpoints, holes = initial_platforms()
        generated_chunks = set()
        spawn_x, spawn_y = last_checkpoint if to_checkpoint else (100, HEIGHT - 120)
        player = Chicken(spawn_x, spawn_y)
        flag = Flag(LEVEL_LENGTH, HEIGHT - 40)
        start_time = pygame.time.get_ticks()
        won = False
        # Fix #1: Explicitly reset moving platforms
        moving = Platform(600, 520, 120, 16, moving=True, move_range=(520, 760), speed=2)
        platforms.add(moving)
        return player, platforms, flag

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_UP, pygame.K_SPACE):
                    if player.can_jump():
                        player.jump()
                    else:
                        player.jump_buffer = 100
                elif event.key == pygame.K_r:
                    player, platforms, flag = reset(to_checkpoint=True) # Reset to checkpoint on "R"
                elif event.key == pygame.K_RETURN and won:
                    player, platforms, flag = reset(to_checkpoint=False) # Reset to start on win

        keys = pygame.key.get_pressed()
        player.vx = 0
        if keys[pygame.K_LEFT]:
            player.vx = -PLAYER_SPEED
            player.facing_right = False
        if keys[pygame.K_RIGHT]:
            player.vx = PLAYER_SPEED
            player.facing_right = True

        target_camera_x = player.rect.centerx - WIDTH // 3
        # Fix #3: Faster smoothing and clamp camera
        camera_x += (target_camera_x - camera_x) * 0.15
        camera_x = max(0, min(camera_x, LEVEL_LENGTH - WIDTH + 200))

        gen_start = camera_x
        gen_end = camera_x + GEN_AHEAD

        for h in holes:
            screen.blit(h.image, (h.rect.x - camera_x, h.rect.y))

        gen_platforms_for_range(platforms, generated_chunks, int(gen_start), int(gen_end), player.rect.centerx)

        for p in list(platforms):
            p.update(camera_x)
            if p.rect.right < camera_x - GEN_BUFFER and p.rect.height != 40:
                platforms.remove(p)

        particles.update()
        player.update(platforms, particles)

        for cp in checkpoints:
            if not cp.activated and player.rect.centerx > cp.x: # Modified: Check if player passes checkpoint's x-coordinates instead of collision detection
                cp.activate()   
                last_checkpoint = (cp.x, HEIGHT - 120)
        # Change: Check for hole collision
        if pygame.sprite.spritecollide(player, holes, False):
            print(f"Reset triggered: Fell into hole at y={player.rect.y}, x={player.rect.centerx}")
            player, platforms, flag = reset(to_checkpoint=True)  # Reset to checkpoint on hole

        if player.rect.colliderect(flag.rect) and not won:
            won = True
            win_time = pygame.time.get_ticks()
            elapsed = (win_time - start_time) // 1000
            best_time = min(best_time, elapsed)

        # Modified: Add debug and stricter lose condition
        if player.rect.top > HEIGHT + 300 and player.vy > 0:
            print(f"Reset triggered: y={player.rect.y}, vy={player.vy}, on_ground={player.on_ground}")
            player, platforms, flag = reset(to_checkpoint=True) # Reset to checkpoint on fall

        screen.fill(BG_COLOR)
        for i in range(6):
            cx = (i * 220 - camera_x * 0.2) % (WIDTH + 200) - 100
            pygame.draw.ellipse(screen, (255, 255, 255, 180), (cx, 80 + (i % 3) * 20, 120, 40))
        for p in platforms:
            screen.blit(p.image, (p.rect.x - camera_x, p.rect.y))
        for cp in checkpoints:
            screen.blit(cp.image, (cp.rect.x - camera_x, cp.rect.y))
        screen.blit(flag.image, (flag.rect.x - camera_x, flag.rect.y))
        for p in particles:
            screen.blit(p.image, (p.rect.x - camera_x, p.rect.y))
        screen.blit(player.image, (player.rect.x - camera_x, player.rect.y))

        elapsed = (pygame.time.get_ticks() - start_time) // 1000
        info = font.render(f"Time {elapsed}s  Best {best_time if best_time != float('inf') else '-'}s  X {player.rect.centerx}  Press R to restart  Esc to quit", True, (30, 30, 30))
        screen.blit(info, (14, 14))

        if won:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            screen.blit(overlay, (0, 0))
            text = big_font.render("You reached the flag!", True, (255, 255, 255))
            sub = font.render(f"Time: {elapsed}s  Best: {best_time if best_time != float('inf') else '-'}s  Press Enter to play again", True, (230, 230, 230))
            screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 40))
            screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 2 + 30))

        pygame.display.flip()

    pygame.quit()
    sys.exit()
    
if __name__ == "__main__":
    main()