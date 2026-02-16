#!/usr/bin/env python3
"""
Fix flag to spawn in chunk with highest X coordinate
"""

def fix_flag_max_x():
    file_path = 'new.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Fixing flag to use highest X coordinate chunk...")
    
    # Fix in initial_platforms
    old_initial_flag = '''    # Create flag at the last chunk position with platform
    last_gx, last_gy = layout[-1]  # Get last grid coordinate
    flag_x = GRID_ORIGIN_X + (last_gx - 1) * CHUNK_WIDTH + CHUNK_WIDTH // 2
    # Place at top of chunk (not bottom) - chunk top is at -gy*HEIGHT
    flag_y = GRID_ORIGIN_Y - last_gy * CHUNK_HEIGHT + 50  # 50px from top of chunk
    end_platform = add_platform(flag_x - 100, flag_y, 200, 18)
    flag = Flag(flag_x, end_platform.rect.top)'''
    
    new_initial_flag = '''    # Create flag at chunk with highest X coordinate
    max_x_coord = max(layout, key=lambda coord: coord[0])  # Find chunk with max X
    flag_gx, flag_gy = max_x_coord
    flag_x = GRID_ORIGIN_X + (flag_gx - 1) * CHUNK_WIDTH + CHUNK_WIDTH // 2
    # Place at top of chunk (not bottom) - chunk top is at -gy*HEIGHT
    flag_y = GRID_ORIGIN_Y - flag_gy * CHUNK_HEIGHT + 50  # 50px from top of chunk
    end_platform = add_platform(flag_x - 100, flag_y, 200, 18)
    flag = Flag(flag_x, end_platform.rect.top)'''
    
    if old_initial_flag in content:
        content = content.replace(old_initial_flag, new_initial_flag)
        print("✓ initial_platforms flag positioning updated")
    else:
        print("✗ Could not find initial_platforms flag code")
    
    # Fix in build_fixed_level
    old_build_flag = '''    # Place end platform and flag at last chunk position
    layout = get_level_layout(level_index)
    last_gx, last_gy = layout[-1]
    flag_x = GRID_ORIGIN_X + (last_gx - 1) * CHUNK_WIDTH + CHUNK_WIDTH // 2
    flag_y = GRID_ORIGIN_Y - last_gy * CHUNK_HEIGHT + 50
    end_platform = add_platform(flag_x - 100, flag_y, 200, 18, surface_type=surface_type)'''
    
    new_build_flag = '''    # Place end platform and flag at chunk with highest X coordinate
    layout = get_level_layout(level_index)
    max_x_coord = max(layout, key=lambda coord: coord[0])  # Find chunk with max X
    flag_gx, flag_gy = max_x_coord
    flag_x = GRID_ORIGIN_X + (flag_gx - 1) * CHUNK_WIDTH + CHUNK_WIDTH // 2
    flag_y = GRID_ORIGIN_Y - flag_gy * CHUNK_HEIGHT + 50
    end_platform = add_platform(flag_x - 100, flag_y, 200, 18, surface_type=surface_type)'''
    
    if old_build_flag in content:
        content = content.replace(old_build_flag, new_build_flag)
        print("✓ build_fixed_level flag positioning updated")
    else:
        print("✗ Could not find build_fixed_level flag code")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n✅ Flag now spawns at chunk with highest X coordinate!")
    print("Flag will use the Y value of that specific chunk for appropriate height")
    return True

if __name__ == '__main__':
    try:
        fix_flag_max_x()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
