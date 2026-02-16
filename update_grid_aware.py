#!/usr/bin/env python3
"""
Update gen_platforms_grid_aware to generate multiple platforms per chunk
Run with: python update_grid_aware.py
"""

import random

def update_function():
    file_path = 'new.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Updating gen_platforms_grid_aware...")
    
    # Find and replace the platform generation loop inside gen_platforms_grid_aware
    old_platform_gen = '''        # Mark as generated
        generated_chunks.add((gx, gy))
        
        # Convert grid to world coordinates
        world_x = GRID_ORIGIN_X + (gx - 1) * CHUNK_WIDTH
        world_y = GRID_ORIGIN_Y - (gy - 1) * CHUNK_HEIGHT
        
        # Determine platform type based on level
        is_vertical = level_index == 1 and gx % 2 == 0
        
        if is_vertical:
            w, h = 18, 160
            moving = False
        else:
            w, h = 160, 18
            moving = level_index == 0 or gx % 3 == 0
        
        move_range = (world_x - move_span, world_x + move_span)
        add_platform(
            world_x,
            world_y,
            w,
            h,
            moving=moving,
            move_range=move_range,
            speed=base_speed,
            surface_type=surface_type,
        )'''
    
    new_platform_gen = '''        # Mark as generated
        generated_chunks.add((gx, gy))
        
        # Chunk boundaries
        chunk_left = GRID_ORIGIN_X + (gx - 1) * CHUNK_WIDTH
        chunk_right = chunk_left + CHUNK_WIDTH
        chunk_top = GRID_ORIGIN_Y - gy * CHUNK_HEIGHT
        chunk_bottom = GRID_ORIGIN_Y - (gy - 1) * CHUNK_HEIGHT
        
        # Determine platform type based on level
        is_vertical = level_index == 1 and gx % 2 == 0
        
        # Track existing platform positions for collision checking
        existing_platform_rects = [(p.rect.centerx, p.rect.centery) for p in platforms]
        
        # Generate multiple platforms per chunk
        for j in range(PLATFORMS_PER_CHUNK):
            if is_vertical:
                w, h = 18, 160
                moving = False
                # For vertical platforms, space them vertically in the chunk
                world_x = chunk_left + random.randint(int(PLATFORM_BUFFER * 0.5), CHUNK_WIDTH - PLATFORM_BUFFER - w)
                world_y = chunk_top + (j * (CHUNK_HEIGHT // PLATFORMS_PER_CHUNK)) + random.randint(0, 30)
            else:
                w, h = 160, 18
                moving = level_index == 0 or (gx + j) % 3 == 0
                # For horizontal platforms, ensure reachable jump distances
                world_x = chunk_left + (j * (CHUNK_WIDTH // PLATFORMS_PER_CHUNK)) + random.randint(-30, 30)
                world_y = chunk_bottom - random.randint(50, min(300, CHUNK_HEIGHT - 100))
            
            # Ensure within chunk bounds
            world_x = max(chunk_left + 10, min(world_x, chunk_right - w - 10))
            world_y = max(chunk_top + 10, min(world_y, chunk_bottom - 10))
            
            # Check for collision with existing platforms
            collision = False
            for px, py in existing_platform_rects:
                if (abs(px - world_x) < PLATFORM_BUFFER and
                    abs(py - world_y) < PLATFORM_BUFFER):
                    collision = True
                    break
            
            if collision:
                continue
            
            move_range = (world_x - move_span, world_x + move_span)
            add_platform(
                world_x,
                world_y,
                w,
                h,
                moving=moving,
                move_range=move_range,
                speed=base_speed,
                surface_type=surface_type,
            )
            existing_platform_rects.append((world_x, world_y))'''
    
    if old_platform_gen in content:
        content = content.replace(old_platform_gen, new_platform_gen)
        print("✓ gen_platforms_grid_aware updated successfully")
    else:
        print("✗ Could not find the exact pattern to replace")
        print("  The function may have already been modified or formatted differently")
        return False
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n✅ Update complete!")
    print("gen_platforms_grid_aware now generates multiple platforms per chunk dynamically")
    return True

if __name__ == '__main__':
    try:
        update_function()
    except Exception as e:
        print(f"Error: {e}")
