#!/usr/bin/env python3
"""
Fix checkpoint respawn and flag positioning
Run with: python fix_checkpoint_and_flag.py
"""

def apply_fixes():
    file_path = 'new.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Applying checkpoint and flag fixes...")
    
    # Fix 1: Update Checkpoint class to store Y position
    old_checkpoint_init = '''class Checkpoint(pygame.sprite.Sprite):
    def __init__(self, x, ground_y):
        super().__init__()
        self.image = pygame.Surface((20, 40), pygame.SRCALPHA)
        self.rect = self.image.get_rect(midbottom=(x, ground_y))
        self.x = x
        self.activated = False  # Track if checkpoint is triggered
        self.draw()'''
    
    new_checkpoint_init = '''class Checkpoint(pygame.sprite.Sprite):
    def __init__(self, x, ground_y):
        super().__init__()
        self.image = pygame.Surface((20, 40), pygame.SRCALPHA)
        self.rect = self.image.get_rect(midbottom=(x, ground_y))
        self.x = x
        self.y = ground_y - 24  # Store Y position for respawning (above platform)
        self.activated = False  # Track if checkpoint is triggered
        self.draw()'''
    
    content = content.replace(old_checkpoint_init, new_checkpoint_init)
    print("✓ Checkpoint class updated to store Y position")
    
    # Fix 2: Update checkpoint activation to use actual checkpoint Y
    old_checkpoint_activation = '''            for cp in checkpoints:
                if not cp.activated and player.rect.centerx > cp.x:
                    cp.activate()   
                    last_checkpoint = (cp.x, HEIGHT - 120)'''
    
    new_checkpoint_activation = '''            for cp in checkpoints:
                if not cp.activated and player.rect.centerx > cp.x:
                    cp.activate()   
                    last_checkpoint = (cp.x, cp.y)'''
    
    content = content.replace(old_checkpoint_activation, new_checkpoint_activation)
    print("✓ Checkpoint activation updated to use actual Y position")
    
    # Fix 3: Update initial_platforms to create flag at last chunk position
    old_initial_platforms_end = '''    level_length = grid_level_length()
    # Platform for the end goal flag
    end_platform = add_platform(level_length - 150, 300, 200, 18)
    
    # Add checkpoints at grid positions (every 3 grid cells)
    checkpoints = pygame.sprite.Group()
    layout = get_level_layout(None)
    for i, (gx, gy) in enumerate(layout):
        if i > 0 and i % 3 == 0:  # Every 3rd platform
            world_x = GRID_ORIGIN_X + (gx - 1) * CHUNK_WIDTH
            world_y = GRID_ORIGIN_Y - (gy - 1) * CHUNK_HEIGHT
            # Add platform underneath checkpoint
            add_platform(world_x - 60, world_y, 120, 18)
            checkpoints.add(Checkpoint(world_x, world_y))
    
    # Return generated grid coordinates
    generated_grid_coords = set(layout)
    return platforms, checkpoints, portal, generated_grid_coords'''
    
    new_initial_platforms_end = '''    level_length = grid_level_length()
    
    # Add checkpoints at grid positions (every 3 grid cells)
    checkpoints = pygame.sprite.Group()
    layout = get_level_layout(None)
    for i, (gx, gy) in enumerate(layout):
        if i > 0 and i % 3 == 0:  # Every 3rd platform
            world_x = GRID_ORIGIN_X + (gx - 1) * CHUNK_WIDTH
            world_y = GRID_ORIGIN_Y - (gy - 1) * CHUNK_HEIGHT
            # Add platform underneath checkpoint
            add_platform(world_x - 60, world_y, 120, 18)
            checkpoints.add(Checkpoint(world_x, world_y))
    
    # Create flag at the last chunk position with platform
    last_gx, last_gy = layout[-1]  # Get last grid coordinate
    flag_x = GRID_ORIGIN_X + (last_gx - 1) * CHUNK_WIDTH + CHUNK_WIDTH // 2
    flag_y = GRID_ORIGIN_Y - (last_gy - 1) * CHUNK_HEIGHT
    end_platform = add_platform(flag_x - 100, flag_y, 200, 18)
    flag = Flag(flag_x, end_platform.rect.top)
    
    # Return generated grid coordinates
    generated_grid_coords = set(layout)
    return platforms, checkpoints, portal, flag, generated_grid_coords'''
    
    content = content.replace(old_initial_platforms_end, new_initial_platforms_end)
    print("✓ initial_platforms updated to create flag at last chunk position")
    
    # Fix 4: Update load_level to handle flag from initial_platforms
    old_load_level_initial = '''        if level_index is None:
            platforms, checkpoints, portal, generated_chunks = initial_platforms()
            enemies = pygame.sprite.Group()
            boosts = pygame.sprite.Group()
            use_procedural = True
            level_length = grid_level_length()
            flag = Flag(level_length - 50, 300)
            start_pos = (PORTAL_X, PORTAL_PLATFORM_Y - 24)'''
    
    new_load_level_initial = '''        if level_index is None:
            platforms, checkpoints, portal, flag, generated_chunks = initial_platforms()
            enemies = pygame.sprite.Group()
            boosts = pygame.sprite.Group()
            use_procedural = True
            level_length = grid_level_length()
            start_pos = (PORTAL_X, PORTAL_PLATFORM_Y - 24)'''
    
    content = content.replace(old_load_level_initial, new_load_level_initial)
    print("✓ load_level updated to receive flag from initial_platforms")
    
    # Fix 5: Update main() initialization to receive flag
    old_main_init = '''    platforms, checkpoints, portal, generated_chunks = initial_platforms()
    enemies = pygame.sprite.Group()
    boosts = pygame.sprite.Group()
    use_procedural = True
    level_length = grid_level_length()
    player = Chicken(PORTAL_X, PORTAL_PLATFORM_Y - 24)
    flag = Flag(level_length - 50, 300)'''
    
    new_main_init = '''    platforms, checkpoints, portal, flag, generated_chunks = initial_platforms()
    enemies = pygame.sprite.Group()
    boosts = pygame.sprite.Group()
    use_procedural = True
    level_length = grid_level_length()
    player = Chicken(PORTAL_X, PORTAL_PLATFORM_Y - 24)'''
    
    content = content.replace(old_main_init, new_main_init)
    print("✓ main() initialization updated")
    
    # Write changes back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n✅ All fixes applied successfully!")
    print("\nChanges:")
    print("- Checkpoint class now stores Y position for proper respawning")
    print("- Player now spawns at checkpoint's actual position on death")
    print("- Flag now spawns at the last chunk's position with platform underneath")
    return True

if __name__ == '__main__':
    try:
        apply_fixes()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
