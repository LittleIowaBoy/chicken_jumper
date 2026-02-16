#!/usr/bin/env python3
"""
Fix flag Y position to be at top of chunk instead of bottom
"""

def fix_flag_position():
    file_path = 'new.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Fixing flag Y position...")
    
    # Update flag positioning to be at top of chunk
    old_flag_code = '''    # Create flag at the last chunk position with platform
    last_gx, last_gy = layout[-1]  # Get last grid coordinate
    flag_x = GRID_ORIGIN_X + (last_gx - 1) * CHUNK_WIDTH + CHUNK_WIDTH // 2
    flag_y = GRID_ORIGIN_Y - (last_gy - 1) * CHUNK_HEIGHT
    end_platform = add_platform(flag_x - 100, flag_y, 200, 18)
    flag = Flag(flag_x, end_platform.rect.top)'''
    
    new_flag_code = '''    # Create flag at the last chunk position with platform
    last_gx, last_gy = layout[-1]  # Get last grid coordinate
    flag_x = GRID_ORIGIN_X + (last_gx - 1) * CHUNK_WIDTH + CHUNK_WIDTH // 2
    # Place at top of chunk (not bottom) - chunk top is at -gy*HEIGHT
    flag_y = GRID_ORIGIN_Y - last_gy * CHUNK_HEIGHT + 50  # 50px from top of chunk
    end_platform = add_platform(flag_x - 100, flag_y, 200, 18)
    flag = Flag(flag_x, end_platform.rect.top)'''
    
    if old_flag_code in content:
        content = content.replace(old_flag_code, new_flag_code)
        print("✓ Flag Y position updated to top of chunk")
    else:
        print("✗ Could not find flag positioning code")
        return False
    
    # Also fix in build_fixed_level if it exists
    old_build_flag = '''    flag = Flag(level_length - 50, end_platform.rect.top)'''
    
    # Check if we need to update build_fixed_level similarly
    new_build_flag = '''    # Place flag at top of last chunk
    layout = get_level_layout(level_index)
    last_gx, last_gy = layout[-1]
    flag_x = GRID_ORIGIN_X + (last_gx - 1) * CHUNK_WIDTH + CHUNK_WIDTH // 2
    flag_y = GRID_ORIGIN_Y - last_gy * CHUNK_HEIGHT + 50
    # Update end_platform position
    end_platform = add_platform(flag_x - 100, flag_y, 200, 18, surface_type=surface_type)
    flag = Flag(flag_x, end_platform.rect.top)'''
    
    # Find and replace the end_platform line in build_fixed_level
    old_build_end = '''    surface_type = "slippery" if level_index == 3 else "normal"
    grid_platforms = add_grid_platforms(level_index, add_platform, surface_type=surface_type)
    end_platform = add_platform(level_length - 220, 260, 180, 18, surface_type=surface_type)'''
    
    new_build_end = '''    surface_type = "slippery" if level_index == 3 else "normal"
    grid_platforms = add_grid_platforms(level_index, add_platform, surface_type=surface_type)
    
    # Place end platform and flag at last chunk position
    layout = get_level_layout(level_index)
    last_gx, last_gy = layout[-1]
    flag_x = GRID_ORIGIN_X + (last_gx - 1) * CHUNK_WIDTH + CHUNK_WIDTH // 2
    flag_y = GRID_ORIGIN_Y - last_gy * CHUNK_HEIGHT + 50
    end_platform = add_platform(flag_x - 100, flag_y, 200, 18, surface_type=surface_type)'''
    
    if old_build_end in content:
        content = content.replace(old_build_end, new_build_end)
        print("✓ build_fixed_level flag position updated")
    
    # Update the flag creation in build_fixed_level
    old_flag_line = '''    flag = Flag(level_length - 50, end_platform.rect.top)
    generated_grid_coords = set(layout)'''
    
    new_flag_line = '''    flag = Flag(flag_x, end_platform.rect.top)
    generated_grid_coords = set(layout)'''
    
    if old_flag_line in content:
        content = content.replace(old_flag_line, new_flag_line)
        print("✓ build_fixed_level flag creation updated")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n✅ Flag position fixed!")
    print("Flag now spawns at the TOP of the last chunk (50px from chunk top)")
    print("This ensures it's visible above all platforms in that chunk")
    return True

if __name__ == '__main__':
    try:
        fix_flag_position()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
