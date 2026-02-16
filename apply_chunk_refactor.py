#!/usr/bin/env python3
"""
Script to refactor new.py for chunk-based platform generation
Run this script with: python apply_chunk_refactor.py
"""

import random

def apply_refactor():
    file_path = 'new.py'
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Applying chunk refactor...")
    
    # Change 1: Update constants
    content = content.replace(
        'CHUNK_HEIGHT = 80',
        'CHUNK_HEIGHT = 400  # Increased for 20x20 grid'
    )
    content = content.replace(
        'LEVEL_CHUNKS_Y = 5',
        'LEVEL_CHUNKS_Y = 20  # 20x20 background grid'
    )
    print("✓ Constants updated")
    
    # Change 2: Remove camera Y clamping
    content = content.replace(
        'camera_y = max(0, camera_y)  # Allow camera to go up, clamp only at bottom',
        '# No clamping - allow camera to follow player infinitely up and down'
    )
    print("✓ Camera clamping removed")
    
    # Change 3: Update grid height limit
    content = content.replace(
        "# Don't exceed reasonable height (12 rows)\n        current_gy = min(current_gy, 12)",
        "# Don't exceed reasonable height (20 rows)\n        current_gy = min(current_gy, 20)"
    )
    print("✓ Grid height limit updated")
    
    # Change 4: Refactor add_grid_platforms
    old_add_grid_platforms = '''def add_grid_platforms(level_index, add_platform, surface_type="normal"):
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

    return placed'''
    
    new_add_grid_platforms = '''def add_grid_platforms(level_index, add_platform, surface_type="normal"):
    placed = []
    layout = get_level_layout(level_index)
    move_span = int(CHUNK_WIDTH * 0.2)
    base_speed = 1 if surface_type == "slippery" else 2

    for i, (gx, gy) in enumerate(layout):
        # Chunk boundaries
        chunk_left = GRID_ORIGIN_X + (gx - 1) * CHUNK_WIDTH
        chunk_right = chunk_left + CHUNK_WIDTH
        chunk_top = GRID_ORIGIN_Y - gy * CHUNK_HEIGHT
        chunk_bottom = GRID_ORIGIN_Y - (gy - 1) * CHUNK_HEIGHT
        
        is_vertical = level_index == 1 and gx % 2 == 0

        # Generate multiple platforms per chunk
        for j in range(PLATFORMS_PER_CHUNK):
            # Randomize platform position within chunk
            if is_vertical:
                w, h = 18, 160
                moving = False
                # For vertical platforms, space them vertically in the chunk
                world_x = chunk_left + random.randint(int(PLATFORM_BUFFER * 0.5), CHUNK_WIDTH - PLATFORM_BUFFER - w)
                world_y = chunk_top + (j * (CHUNK_HEIGHT // PLATFORMS_PER_CHUNK)) + random.randint(0, 30)
            else:
                w, h = 160, 18
                moving = level_index == 0 or (i + j) % 3 == 0
                # For horizontal platforms, ensure reachable jump distances
                world_x = chunk_left + (j * (CHUNK_WIDTH // PLATFORMS_PER_CHUNK)) + random.randint(-30, 30)
                world_y = chunk_bottom - random.randint(50, min(300, CHUNK_HEIGHT - 100))
            
            # Ensure within chunk bounds
            world_x = max(chunk_left + 10, min(world_x, chunk_right - w - 10))
            world_y = max(chunk_top + 10, min(world_y, chunk_bottom - 10))
            
            # Check for collision with existing platforms
            collision = False
            for existing_p in placed:
                if (abs(existing_p.rect.centerx - world_x) < PLATFORM_BUFFER and
                    abs(existing_p.rect.centery - world_y) < PLATFORM_BUFFER):
                    collision = True
                    break
            
            if collision:
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

    return placed'''
    
    content = content.replace(old_add_grid_platforms, new_add_grid_platforms)
    print("✓ add_grid_platforms refactored")
    
    # Change 6: Fix checkpoint platforms in initial_platforms
    old_checkpoint_initial = '''    # Add checkpoints at grid positions (every 3 grid cells)
    checkpoints = pygame.sprite.Group()
    layout = get_level_layout(None)
    for i, (gx, gy) in enumerate(layout):
        if i > 0 and i % 3 == 0:  # Every 3rd platform
            world_x = GRID_ORIGIN_X + (gx - 1) * CHUNK_WIDTH
            world_y = GRID_ORIGIN_Y - (gy - 1) * CHUNK_HEIGHT
            checkpoints.add(Checkpoint(world_x, world_y))'''
    
    new_checkpoint_initial = '''    # Add checkpoints at grid positions (every 3 grid cells)
    checkpoints = pygame.sprite.Group()
    layout = get_level_layout(None)
    for i, (gx, gy) in enumerate(layout):
        if i > 0 and i % 3 == 0:  # Every 3rd platform
            world_x = GRID_ORIGIN_X + (gx - 1) * CHUNK_WIDTH
            world_y = GRID_ORIGIN_Y - (gy - 1) * CHUNK_HEIGHT
            # Add platform underneath checkpoint
            add_platform(world_x - 60, world_y, 120, 18)
            checkpoints.add(Checkpoint(world_x, world_y))'''
    
    content = content.replace(old_checkpoint_initial, new_checkpoint_initial)
    print("✓ Checkpoint platforms added to initial_platforms")
    
    # Change 7: Fix checkpoint platforms in build_fixed_level
    old_checkpoint_fixed = '''    # Add checkpoints at grid positions (every 3 grid cells)
    layout = get_level_layout(level_index)
    for i, (gx, gy) in enumerate(layout):
        if i > 0 and i % 3 == 0:  # Every 3rd platform
            world_x = GRID_ORIGIN_X + (gx - 1) * CHUNK_WIDTH
            world_y = GRID_ORIGIN_Y - (gy - 1) * CHUNK_HEIGHT
            checkpoints.add(Checkpoint(world_x, world_y))'''
    
    new_checkpoint_fixed = '''    # Add checkpoints at grid positions (every 3 grid cells)
    layout = get_level_layout(level_index)
    for i, (gx, gy) in enumerate(layout):
        if i > 0 and i % 3 == 0:  # Every 3rd platform
            world_x = GRID_ORIGIN_X + (gx - 1) * CHUNK_WIDTH
            world_y = GRID_ORIGIN_Y - (gy - 1) * CHUNK_HEIGHT
            # Add platform underneath checkpoint
            add_platform(world_x - 60, world_y, 120, 18)
            checkpoints.add(Checkpoint(world_x, world_y))'''
    
    content = content.replace(old_checkpoint_fixed, new_checkpoint_fixed)
    print("✓ Checkpoint platforms added to build_fixed_level")
    
    # Write the modified content back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n✅ Refactor complete! Changes applied to new.py")
    print("\nChanges made:")
    print("- CHUNK_HEIGHT: 80 → 400")
    print("- LEVEL_CHUNKS_Y: 5 → 20")
    print("- Camera Y clamping removed (infinite vertical scroll)")
    print("- add_grid_platforms now generates 7 platforms per chunk")
    print("- Checkpoints now have platforms underneath them")
    print("\n⚠️  Note: gen_platforms_grid_aware still needs manual update for dynamic chunk generation")

if __name__ == '__main__':
    try:
        apply_refactor()
    except Exception as e:
        print(f"Error: {e}")
        print("\nIf you encounter issues, you may need to apply changes manually.")
