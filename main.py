import enum
import math
import os
import numpy as np
import backend_game
import backend_helper
from backend_helper import Tile, Direction
import socket
import threading
import time
import random
from helper import send_obj, recv_obj
import random
import pygame
from Config import *
from fontTools.ttLib import TTFont

# Pygame setup
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()
pygame.display.set_caption("Moving Blocks")

# --- CONFIGURATION ---
WINNINGSCORE = 3
SIDEBAR_WIDTH = 200      # Left side (Tools)
SCOREBOARD_WIDTH = 200   # Right side (Scores)
TILES_PER_TURN = 1       # Limit how many tiles a player can place

FONTNAME = "GothicByte"
# Fallback font handling if custom font is missing
try:
    font_path = os.path.join("Assets", f"{FONTNAME}.ttf")
    if not os.path.exists(font_path):
        raise FileNotFoundError
    GAME_FONT = pygame.font.Font(font_path, 24)
    TITLE_FONT = pygame.font.Font(font_path, 55)
    SUB_FONT = pygame.font.Font(font_path, 35)
except:
    print("Custom font not found, using system default.")
    GAME_FONT = pygame.font.SysFont("Arial", 24)
    TITLE_FONT = pygame.font.SysFont("Arial", 55)
    SUB_FONT = pygame.font.SysFont("Arial", 35)

class GameState(enum.Enum):
    LOBBY = 1
    SIMULATION = 2
    GAME_OVER = 3

class GamePhase(enum.Enum):
    PLACING_TILES = 1
    MOVING_BOXES = 2
    NOT_SIMULATING = 3

game_state = GameState.LOBBY
game_phase = GamePhase.NOT_SIMULATING
selected_direction = Direction.NORTH

# Track local placement limit
tiles_placed_count = 0 

XS = []
YS = []
def precompute_distortion(width = SCREEN_WIDTH, height = SCREEN_HEIGHT, k=0.15):
    """Returns lookup arrays mapping dest->src pixels."""
    cx, cy = width / 2, height / 2
    xs = np.zeros((width, height), np.int16)
    ys = np.zeros((width, height), np.int16)
    for y in range(height):
        for x in range(width):
            nx = (x - cx) / cx
            ny = (y - cy) / cy
            r = math.sqrt(nx * nx + ny * ny)
            nr = r * (1 + k * (r ** 2))
            if r != 0:
                tx = int(cx + nx / r * nr * cx)
                ty = int(cy + ny / r * nr * cy)
            else:
                tx, ty = x, y
            tx = max(0, min(width - 1, tx))
            ty = max(0, min(height - 1, ty))
            xs[x, y] = tx
            ys[x, y] = ty
    global XS
    XS = xs
    global YS
    YS = ys

precompute_distortion()

# --- UI RECTS ---
# Define buttons for sidebar selection (Positions recalculated in update_sidebar_buttons)
sidebar_buttons = {
    Direction.NORTH: pygame.Rect(0, 0, 1, 1),
    Direction.EAST:  pygame.Rect(0, 0, 1, 1),
    Direction.SOUTH: pygame.Rect(0, 0, 1, 1),
    Direction.WEST:  pygame.Rect(0, 0, 1, 1)
}

SERVER_IP = "192.168.137.135"  # <-- Change to host's Wi-Fi IP
PORT = 6000

received = []         # incoming packets land here
send = []
running = True

def recv_loop(sock):
    """Listens for packets from the host and pushes them into received."""
    while running:
        try:
            packet = recv_obj(sock)
            if packet is None:
                print("[CLIENT] Disconnected from host")
                break
            received.append(packet)
        except:
            break

# Setup
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(5)
try:
    sock.connect((SERVER_IP, PORT))
    sock.settimeout(None)
    print(f"[CLIENT] Connected to {SERVER_IP}:{PORT}")
    threading.Thread(target=recv_loop, args=(sock,), daemon=True).start()
    send.append({"type": "INIT_CONNECTION"})
except:
    print("[CLIENT] Could not connect to server.")

# Main loop
client_data = {"name": "Client", "x": 300, "y": 400}

playing = False
started = False
game = None
victory = False
player_number = -1

def get_list_of_tiles():
    return game.game

def get_layout_metrics():
    """Helper to calculate grid position and scale uniformly between sidebars"""
    tile_grid = get_list_of_tiles()
    grid_size = len(tile_grid)

    # Available width is Screen minus BOTH sidebars
    available_width = SCREEN_WIDTH - SIDEBAR_WIDTH - SCOREBOARD_WIDTH
    available_height = SCREEN_HEIGHT * 0.8 # Leave space for top text

    # Calculate tile size to fit smallest dimension
    tile_size = min(available_width, available_height) // grid_size

    # Center the grid
    grid_w_px = grid_size * tile_size
    grid_h_px = grid_size * tile_size

    # Start X is after the Left Sidebar + half the remaining space
    start_x = SIDEBAR_WIDTH + (available_width - grid_w_px) // 2
    start_y = (SCREEN_HEIGHT - grid_h_px) // 2 + (SCREEN_HEIGHT * 0.05)

    return start_x, start_y, tile_size

def update_sidebar_buttons():
    """Recalculate button positions based on current screen size"""
    global sidebar_buttons
    btn_size = int(SIDEBAR_WIDTH * 0.6)
    start_x = (SIDEBAR_WIDTH - btn_size) // 2
    start_y = int(SCREEN_HEIGHT * 0.25)
    gap = int(btn_size * 1.2)

    sidebar_buttons = {
        Direction.NORTH: pygame.Rect(start_x, start_y, btn_size, btn_size),
        Direction.EAST:  pygame.Rect(start_x, start_y + gap, btn_size, btn_size),
        Direction.SOUTH: pygame.Rect(start_x, start_y + gap*2, btn_size, btn_size),
        Direction.WEST:  pygame.Rect(start_x, start_y + gap*3, btn_size, btn_size)
    }

def place_tile(direction, coords):
    """
    Validates placement and updates the game state.
    coords: (grid_col, grid_row)
    """
    global tiles_placed_count

    # 1. Check Placement Limit
    if tiles_placed_count >= TILES_PER_TURN:
        print(f"Limit Reached! You can only place {TILES_PER_TURN} tile(s) per turn.")
        return

    col, row = coords
    
    # 2. Check bounds
    if row < 0 or row >= len(game.game) or col < 0 or col >= len(game.game):
        return

    tile_obj = game.game[row][col]

    # 3. Must be a standard Tile (not Spawner/Goal)
    if not isinstance(tile_obj, Tile):
        print("Cannot place on Special Object")
        return

    # 4. Must be empty (Direction.STILL) - Prevent overlapping
    if tile_obj.direction != Direction.STILL:
        print("Tile already occupied!")
        return

    # 5. Cannot place under a Box
    for box in game.boxes:
        if box.coords == [col, row]:
            print("Cannot place under a Box")
            return

    # Send to Server
    try:
        send.append({
            "type": "TILE_PLACE", 
            "data": {"direction": direction, "coords": coords}
        })
        # Optimistic local update
        tile_obj.direction = direction
        
        # Increment Counter
        tiles_placed_count += 1
        print(f"Placed {direction.name} at {coords} ({tiles_placed_count}/{TILES_PER_TURN})")
        
    except Exception as e:
        print(f"Error placing tile: {e}")

def handle_events():
    global running, selected_direction

    # Ensure button rects are up to date
    update_sidebar_buttons()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if game_state == GameState.SIMULATION and game_phase == GamePhase.PLACING_TILES:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                raw_mx, raw_my = pygame.mouse.get_pos()
                mx, my = int(XS[raw_mx, raw_my]), int(YS[raw_mx, raw_my])

                # A. Check Sidebar Clicks
                for direction, rect in sidebar_buttons.items():
                    if rect.collidepoint(mx, my):
                        selected_direction = direction
                        print(f"Selected Tool: {direction.name}")
                        return

                # B. Check Grid Clicks
                start_x, start_y, tile_size = get_layout_metrics()
                grid_size_px = len(get_list_of_tiles()) * tile_size
                
                board_rect = pygame.Rect(start_x, start_y, grid_size_px, grid_size_px)

                if board_rect.collidepoint(mx, my):
                    rel_x = mx - start_x
                    rel_y = my - start_y
                    col = int(rel_x // tile_size)
                    row = int(rel_y // tile_size)
                    place_tile(selected_direction, (col, row))

def update():
    global game_phase, animation_frame

    if game_phase == GamePhase.MOVING_BOXES:
        #if animation_frame < TOTAL_ANIMATION_FRAMES:
        #    animation_frame += 1
        #else:
        game_phase = GamePhase.PLACING_TILES
            # Animation finished
        #    print("Animation Complete")

def apply_crt_effect(screen, intensity=6, pixelation=8):
    width, height = screen.get_size()
    glitch_surface = screen.copy()

    scanline_surface = pygame.Surface((width, height), pygame.SRCALPHA)

    for y in range(0, height, max(1, 8-intensity)):
        pygame.draw.line(scanline_surface, (0, 0, 0, 60), (0, y), (width, y))

    screen.blit(scanline_surface, (0, 0))

    small_surf = pygame.transform.scale(screen, (width // pixelation, height // pixelation))
    screen.blit(pygame.transform.scale(small_surf, (width, height)), (0, 0))

    if random.randint(0, 15) == 0:
        flicker_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        flicker_surface.fill((255, 255, 255, 5))
        screen.blit(flicker_surface, (0, 0))

    glow_surf = pygame.transform.smoothscale(screen, (width // 2, height // 2))
    glow_surf = pygame.transform.smoothscale(glow_surf, (width, height))
    glow_surf.set_alpha(100)
    screen.blit(glow_surf, (0, 0))

    shift_amount = intensity*10
    if random.random() < 0.2:
        y_start = random.randint(0, height - 20)
        slice_height = random.randint(5, 20)
        offset = random.randint(-shift_amount, shift_amount)

        slice_area = pygame.Rect(0, y_start, width, slice_height)
        slice_copy = glitch_surface.subsurface(slice_area).copy()
        glitch_surface.blit(slice_copy, (offset, y_start))

    color_shift = intensity*2
    if random.random() < 0.1:
        for i in range(3):
            x_offset = random.randint(-color_shift, color_shift)
            y_offset = random.randint(-color_shift, color_shift)

            shifted = glitch_surface.copy()
            screen.blit(shifted, (x_offset, y_offset), special_flags=pygame.BLEND_ADD)

    static_chance = intensity/8
    static_surface = pygame.Surface((width, height), pygame.SRCALPHA)

    for y in range(0, height, 8):
        if random.random() < static_chance:
            pygame.draw.line(static_surface, (255, 255, 255, random.randint(30, 80)), (0, y), (width, y))
    glitch_surface_arr = pygame.surfarray.pixels3d(glitch_surface).copy()
    distorted = glitch_surface_arr[XS, YS]
    glitch_surface = pygame.surfarray.make_surface(distorted)
    screen.blit(glitch_surface, (0, 0))
    pygame.display.flip()

def handle_box_animation(k, n, x_pos, y_pos, direction, tile_size):
    """
    Calculates the stretch/move parameters for a box based on its direction.
    k: current animation step (1 to n)
    n: total animation steps
    """
    # Normalized progress (0.0 to 1.0)
    progress = k / n
    
    # Sine wave for "squash/stretch" effect (0 -> 1 -> 0)
    # or just linear movement depending on style. 
    # Using your original "sin/cos" logic for a stretch effect:
    stretch_factor = math.sin(progress * math.pi) 
    
    # Movement offset (0 to 1 tile)
    offset = progress * tile_size

    # Default values (No movement)
    draw_x = x_pos
    draw_y = y_pos
    width = tile_size - 4
    height = tile_size - 4
    
    if direction == Direction.STILL:
        pass # No change

    elif direction == Direction.EAST:
        # Move Right
        draw_x = x_pos + offset
        # Optional: Stretch width slightly during move
        width += stretch_factor * 10 
        
    elif direction == Direction.WEST:
        # Move Left
        draw_x = x_pos - offset
        width += stretch_factor * 10

    elif direction == Direction.SOUTH:
        # Move Down
        draw_y = y_pos + offset
        height += stretch_factor * 10

    elif direction == Direction.NORTH:
        # Move Up
        draw_y = y_pos - offset
        height += stretch_factor * 10

    return draw_x, draw_y, width, height

def draw_box_handled(start_x, start_y, tile_size):
    """
    Draws the boxes from game.animation_boxes.
    Assumes 'game.animation_boxes' contains [[col, row], direction]
    """
    # 1. Prepare Box Image (Load once)
    try:
        box_raw = pygame.image.load(os.path.join("Assets", "Box.png"))
    except:
        box_raw = pygame.Surface((32, 32))
        box_raw.fill((0, 255, 255))

    # 2. Iterate and Draw
    # We assume 'animation_step' is a global or passed variable tracking frame 1..10
    # For this static function, I'll hardcode a "middle" frame or rely on an external loop.
    # If you want this function to handle the loop itself (blocking), see below.
    # If you want it to just draw the CURRENT state, you need an external counter.
    
    # Assuming this function is called inside the main loop and you want to see the animation:
    # We will simulate the loop here for demonstration as requested "call handler n times".
    
    steps = 1
    for k in range(1, steps + 1):
        # Clear screen or redraw background here if you want smooth animation 
        # (Otherwise it trails). For this snippet, we just blit on top.
        
        for box in game.animation_boxes:
            coords = box[0]      # [col, row]
            direction = box[1]   # Direction Enum
            
            # Base position
            base_x = start_x + coords[0] * tile_size + 2
            base_y = start_y + coords[1] * tile_size + 2
            
            # Get animated transformation
            dx, dy, w, h = handle_box_animation(k, steps, base_x, base_y, direction, tile_size)
            
            # Scale and Draw
            scaled_box = pygame.transform.scale(box_raw, (int(w), int(h)))
            screen.blit(scaled_box, (dx, dy))
        
        pygame.time.delay(1) # Small delay to see the animation

def draw_lobby():
    font = pygame.font.SysFont(FONTNAME, 55)
    text = font.render("Lobby - Waiting for everyone to join...", True, WHITE)
    screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - text.get_height() // 2))
    apply_crt_effect(screen)

def draw_tools_sidebar():
    """Draws the selection tool on the LEFT"""
    # Background
    pygame.draw.rect(screen, (40, 40, 40), (0, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT))
    
    # Title
    lbl = SUB_FONT.render("Tiles:", True, WHITE)
    screen.blit(lbl, (int(SIDEBAR_WIDTH * 0.1), int(SCREEN_HEIGHT * 0.15)))

    # Limit Indicator
    limit_txt = GAME_FONT.render(f"Moves: {tiles_placed_count}/{TILES_PER_TURN}", True, (255, 100, 100))
    screen.blit(limit_txt, (int(SIDEBAR_WIDTH * 0.1), int(SCREEN_HEIGHT * 0.20)))

    update_sidebar_buttons()

    for direction, rect in sidebar_buttons.items():
        # Highlight selected
        if selected_direction == direction:
            pygame.draw.rect(screen, (255, 215, 0), rect.inflate(6, 6), 3)
        
        # Draw Button Box
        pygame.draw.rect(screen, (70, 70, 70), rect)
        pygame.draw.rect(screen, (200, 200, 200), rect, 2)

        # Draw Arrow Icon
        try:
            arrow_img = pygame.image.load(os.path.join("Assets", "Tile_Arrow.png"))
            angle = (direction.value - 1) * -90 
            scaled_icon = pygame.transform.scale(arrow_img, (int(rect.width * 0.8), int(rect.height * 0.8)))
            icon = pygame.transform.rotate(scaled_icon, angle)
            icon_rect = icon.get_rect(center=rect.center)
            screen.blit(icon, icon_rect)
        except:
            txt = GAME_FONT.render(direction.name[0], True, WHITE)
            txt_rect = txt.get_rect(center=rect.center)
            screen.blit(txt, txt_rect)

def draw_scoreboard():
    """Draws player scores on the RIGHT"""
    start_x = SCREEN_WIDTH - SCOREBOARD_WIDTH
    
    # Background
    pygame.draw.rect(screen, (30, 30, 45), (start_x, 0, SCOREBOARD_WIDTH, SCREEN_HEIGHT))
    pygame.draw.line(screen, (100, 100, 100), (start_x, 0), (start_x, SCREEN_HEIGHT), 2)
    
    # Title
    title = SUB_FONT.render("Scores", True, (255, 215, 0))
    screen.blit(title, (start_x + 40, 200))
    
    # Draw Scores from game.scores
    # game.scores is a list like [p1_score, p2_score, p3_score, p4_score]
    if hasattr(game, 'scores'):
        for i, score in enumerate(game.scores):
            # i+1 is Player ID
            p_text = f"P{i+1}:"
            s_text = f"{score}"
            if score == WINNINGSCORE:
                global running
                running = False
            
            y_pos = 300 + (i * 60)
            
            # Highlight local player (if we knew our ID)
            color = WHITE
            if i + 1 == player_number: 
                color = (100, 255, 100) # Green for self
                p_text += " (You)"
                global victory
                victory = True

            # Render Player Name
            name_surf = GAME_FONT.render(p_text, True, color)
            screen.blit(name_surf, (start_x + 20, y_pos))
            
            # Render Score
            score_surf = title = SUB_FONT.render(s_text, True, color)
            screen.blit(score_surf, (start_x + 20, y_pos + 25))
    else:
        # Fallback if scores not yet initialized
        err = GAME_FONT.render("Loading...", True, (100, 100, 100))
        screen.blit(err, (start_x + 20, 100))

def draw_simulation():
    screen.fill(BLACK)
    
    # 1. Draw Sidebars
    draw_tools_sidebar()
    draw_scoreboard()

    # Metrics for scaling
    start_x, start_y, tile_size = get_layout_metrics()
    tile_grid = get_list_of_tiles()
    grid_len = len(tile_grid)

    # Assets
    try:
        bg_tile = pygame.transform.scale(pygame.image.load(os.path.join("Assets", "Tile_Background.png")), (tile_size, tile_size))
        arrow_tile = pygame.transform.scale(pygame.image.load(os.path.join("Assets", "Tile_Arrow.png")), (tile_size, tile_size))
        box = pygame.transform.scale(pygame.image.load(os.path.join("Assets", "Box.png")), (tile_size - 2 , tile_size - 2))
    except:
        bg_tile = pygame.Surface((tile_size, tile_size))
        bg_tile.fill((100, 100, 100))
        arrow_tile = pygame.Surface((tile_size, tile_size))
        arrow_tile.fill((0, 255, 0))
        box = pygame.Surface((tile_size - 2, tile_size - 2))
        box.fill((255, 0, 0))

    # Draw Grid Layers
    for i in range(grid_len):
        for j in range(grid_len):
            x_pos = start_x + i * tile_size
            y_pos = start_y + j * tile_size

            # Layer 0: Background
            screen.blit(bg_tile, (x_pos, y_pos))

            # Layer 1: Objects
            tile = tile_grid[j][i]

            if isinstance(tile, Tile):
                if tile.direction != Direction.STILL:
                    angle = (tile.direction.value - 1) * -90
                    rotated = pygame.transform.rotate(arrow_tile, angle)
                    # Re-center after rotation
                    new_rect = rotated.get_rect(center=(x_pos + tile_size//2, y_pos + tile_size//2))
                    screen.blit(rotated, new_rect)
            
            elif isinstance(tile, backend_helper.Spawner):
                if hasattr(tile, 'img'):
                      screen.blit(pygame.transform.scale(tile.img, (tile_size, tile_size)), (x_pos, y_pos))
                else:
                      pygame.draw.rect(screen, (128, 0, 128), (x_pos, y_pos, tile_size, tile_size))

            elif isinstance(tile, backend_helper.Goal):
                 if hasattr(tile, 'img'):
                      screen.blit(pygame.transform.scale(tile.img, (tile_size, tile_size)), (x_pos, y_pos))
                 else:
                      pygame.draw.rect(screen, (255, 215, 0), (x_pos, y_pos, tile_size, tile_size))

    # Text Overlay
    if game_phase == GamePhase.PLACING_TILES:
        title = TITLE_FONT.render("Placing Phase", True, WHITE)
        # Center text in available space
        avail_w = SCREEN_WIDTH - SIDEBAR_WIDTH - SCOREBOARD_WIDTH
        center_x = SIDEBAR_WIDTH + avail_w // 2

        screen.blit(title, (center_x - title.get_width()//2, 20))
    
        #Boxes Layer
        for box_obj in game.boxes:
            x_pos = start_x + box_obj.coords[0] * tile_size + 2
            y_pos = start_y + box_obj.coords[1] * tile_size + 2
        
            screen.blit(box, (x_pos, y_pos))
    
    if game_phase == GamePhase.MOVING_BOXES:
        title = TITLE_FONT.render("Moving Phase", True, WHITE)
        avail_w = SCREEN_WIDTH - SIDEBAR_WIDTH - SCOREBOARD_WIDTH
        center_x = SIDEBAR_WIDTH + avail_w // 2

        screen.blit(title, (center_x - title.get_width()//2, 20))

        # Animated Boxes Layer
        # Pass the global animation_frame variable (defined in step 3)
        draw_box_handled(start_x, start_y, tile_size)
            

def draw_game_over():
    screen.fill(BLACK)
    font = pygame.font.SysFont(FONTNAME, 55)
    text = font.render("Game Over!", True, (255, 255, 255))
    screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - text.get_height() // 2 - 40))
    text = font.render("CONGRATULATIONS - You won!" if victory else "Better luck next time...", True, (255, 255, 255))
    screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 + text.get_height() // 2 + 40))

def draw():
    screen.fill(BLACK)

    if game_state == GameState.LOBBY:
        draw_lobby()
    elif game_state == GameState.SIMULATION:
        draw_simulation()
        apply_crt_effect(screen)
    elif game_state == GameState.GAME_OVER:
        draw_game_over()



# REMOVE LATER - Mock setup for testing
#game = backend_game.Game([], seed=random.randint(0, 2**32 - 1))
#game.scores = [0, 0, 0, 0] # Initialize scores list
animation_frame = 0
TOTAL_ANIMATION_FRAMES = 60 # Adjust speed here (60 = 1 second move)

while running:
    # Process any packets that came in
    while received:
        packet = received.pop(0)
        print(packet)

        if not started and packet["type"] == "INIT_GAME_STATE":
            game = backend_game.Game([], packet["data"]["seed"])
            # Initialize scores if they aren't in the game object

            game_state = GameState.SIMULATION
            game_phase = GamePhase.PLACING_TILES

            if not hasattr(game, 'scores'): game.scores = [0, 0, 0, 0]
            
            player_number = packet["data"]["player_number"]
            started = True
            playing = True
        
        elif started and packet["type"] == "TILE_PLACE":
                # IMPORTANT: Reset local placement limit when a new round starts
                # Assuming receiving TILE_PLACE implies the previous round ended or new one starting
                # Logic might need adjustment depending on your exact server phases
                # For now, we manually reset it when the phase changes
                
            for x in reversed(packet["data"]):
                temp_tile = game.game[x["coords"][1]][x["coords"][0]] 
                #if type(temp_tile) == backend_helper.Tile:
                temp_tile.direction = x["direction"]

            game_phase = GamePhase.MOVING_BOXES
            game.move_boxes()
            tiles_placed_count = 0
            animation_frame = 0
            print("DOING SHIT")

        else: 
            print(f"Found unknown packet: {packet}")

        print(f"[CLIENT] Got: {packet}")


    handle_events()
    update()
    draw()

    while send:
        try:
            o = send.pop(0)
            send_obj(sock, o)
        except:
            print("[CLIENT] Failed to send, host probably disconnected")
            break

    clock.tick(FPS)

sock.close()