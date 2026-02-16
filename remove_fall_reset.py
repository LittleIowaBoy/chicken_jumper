#!/usr/bin/env python3
"""
Remove the player fall reset logic
"""

def remove_fall_reset():
    file_path = 'new.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Removing fall reset logic...")
    
    # Remove the fall reset check
    old_fall_reset = '''            if pygame.sprite.spritecollide(player, enemies, False):
                player, platforms, flag = reset(to_checkpoint=True)

            if player.rect.top > HEIGHT + 300 and player.vy > 0:
                print(f"Reset triggered: y={player.rect.y}, vy={player.vy}, on_ground={player.on_ground}")
                player, platforms, flag = reset(to_checkpoint=True)

            screen.fill(BG_COLOR)'''
    
    new_without_fall_reset = '''            if pygame.sprite.spritecollide(player, enemies, False):
                player, platforms, flag = reset(to_checkpoint=True)

            screen.fill(BG_COLOR)'''
    
    if old_fall_reset in content:
        content = content.replace(old_fall_reset, new_without_fall_reset)
        print("✓ Fall reset logic removed")
    else:
        print("✗ Could not find fall reset code")
        return False
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n✅ Player will no longer reset when falling!")
    print("Removed: Reset when player.rect.top > HEIGHT + 300")
    return True

if __name__ == '__main__':
    try:
        remove_fall_reset()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
