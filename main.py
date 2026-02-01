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
SIDEBAR_WIDTH = 200
clock = pygame.time.Clock()
pygame.display.set_caption("Moving Blocks")

# --- CONFIGURATION ---
FONTNAME = "GothicByte"
# Fallback font handling if custom font is missing

try:
    font_path = os.path.join("Assets", f"{FONTNAME}.ttf")
    # Just checking if file exists, TTFont not strictly needed for pygame rendering
    if not os.path.exists(font_path):
        raise FileNotFoundError
    GAME_FONT = pygame.font.Font(font_path, 24)
    TITLE_FONT = pygame.font.Font(font_path, 55)
    SUB_FONT = pygame.font.Font(font_path, 25)
except:
    print("Custom font not found, using system default.")
    GAME_FONT = pygame.font.SysFont("Arial", 24)
    TITLE_FONT = pygame.font.SysFont("Arial", 55)
    SUB_FONT = pygame.font.SysFont("Arial", 25)

class GameState(enum.Enum):
    LOBBY = 1
    SIMULATION = 2
    GAME_OVER = 3

class GamePhase(enum.Enum):
    PLACING_TILES = 1
    MOVING_BOXES = 2
    NOT_SIMULATING = 3

game_state = GameState.SIMULATION
game_phase = GamePhase.PLACING_TILES
selected_direction = Direction.NORTH

# --- UI RECTS ---
# Define buttons for sidebar selection
sidebar_buttons = {
    Direction.NORTH: pygame.Rect(50, 150, 100, 100),
    Direction.EAST:  pygame.Rect(50, 270, 100, 100),
    Direction.SOUTH: pygame.Rect(50, 390, 100, 100),
    Direction.WEST:  pygame.Rect(50, 510, 100, 100)
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
sock.connect((SERVER_IP, PORT))
sock.settimeout(None)
print(f"[CLIENT] Connected to {SERVER_IP}:{PORT}")

# Start receiving in background
threading.Thread(target=recv_loop, args=(sock,), daemon=True).start()

# Main loop
client_data = {"name": "Client", "x": 300, "y": 400}

playing = False
started = False

send.append({"type": "INIT_CONNECTION"})

game = None
victory = False
player_number = -1

def get_list_of_tiles():
    return game.game

def get_layout_metrics():
    """Helper to calculate grid position and scale uniformly"""
    tile_grid = get_list_of_tiles()
    grid_size = len(tile_grid)
    
    available_width = SCREEN_WIDTH - SIDEBAR_WIDTH
    available_height = SCREEN_HEIGHT * 0.8 # Leave space for top text
    
    # Calculate tile size to fit smallest dimension
    tile_size = min(available_width, available_height) // grid_size
    
    # Center the grid
    grid_w_px = grid_size * tile_size
    grid_h_px = grid_size * tile_size
    
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
    col, row = coords
    
    # Validation 1: Check bounds
    if row < 0 or row >= len(game.game) or col < 0 or col >= len(game.game):
        return

    tile_obj = game.game[row][col]

    # Validation 2: Must be a standard Tile (not Spawner/Goal)
    if not isinstance(tile_obj, Tile):
        print("❌ Cannot place on Special Object")
        return

    # Validation 3: Must be empty (Direction.STILL)
    # Uncomment if you want to prevent overwriting existing arrows
    # if tile_obj.direction != Direction.STILL:
    #     print("❌ Tile already occupied")
    #     return

    # Validation 4: Cannot place under a Box
    for box in game.boxes:
        # Assuming box.coords is [col, row]
        if box.coords == [col, row]:
            print("❌ Cannot place under a Box")
            return

    # Send to Server
    try:
        send.append({
            "type": "TILE_PLACE", 
            "data": {"direction": direction, "coords": coords}
        })
        # Optimistic local update (for instant feedback)
        tile_obj.direction = direction
        print(f"✅ Placed {direction.name} at {coords}")
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
                mx, my = pygame.mouse.get_pos()

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
    pass

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
    distorted = np.zeros_like(glitch_surface_arr)
    cx, cy = width / 2, height / 2
    for y in range(height):
        for x in range(width):
            # normalized coords (-1 to 1)
            nx = (x - cx) / cx
            ny = (y - cy) / cy
            r = math.sqrt(nx * nx + ny * ny)
            # barrel distortion factor
            k = 0.1
            nr = r * (1 + k * (r ** 2))
            if nr == 0:
                continue
            tx = int(cx + nx / r * nr * cx)
            ty = int(cy + ny / r * nr * cy)
            if 0 <= tx < width and 0 <= ty < height:
                distorted[x, y] = glitch_surface_arr[tx, ty]
    glitch_surface = pygame.surfarray.make_surface(distorted)
    screen.blit(glitch_surface, (0, 0))
    pygame.display.flip()


def draw_lobby():
    font = pygame.font.SysFont(FONTNAME, 55)
    text = font.render("Lobby - Waiting for everyone to join...", True, WHITE)
    screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - text.get_height() // 2))


def draw_sidebar():
    # Sidebar Background
    pygame.draw.rect(screen, (40, 40, 40), (0, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT))
    
    # Title
    lbl = SUB_FONT.render("Tools:", True, WHITE)
    screen.blit(lbl, (int(SIDEBAR_WIDTH * 0.1), int(SCREEN_HEIGHT * 0.1)))

    update_sidebar_buttons()

    for direction, rect in sidebar_buttons.items():
        # Highlight selected
        if selected_direction == direction:
            pygame.draw.rect(screen, (255, 215, 0), rect.inflate(6, 6), 3)
        
        # Button Box
        pygame.draw.rect(screen, (70, 70, 70), rect)
        pygame.draw.rect(screen, (200, 200, 200), rect, 2)

        # Icon
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

def draw_simulation():
    screen.fill(BLACK)
    draw_sidebar()

    # Metrics for scaling
    start_x, start_y, tile_size = get_layout_metrics()
    tile_grid = get_list_of_tiles()
    grid_len = len(tile_grid)

    # Assets
    try:
        bg_tile = pygame.transform.scale(pygame.image.load(os.path.join("Assets", "Tile_Background.png")), (tile_size, tile_size))
        arrow_tile = pygame.transform.scale(pygame.image.load(os.path.join("Assets", "Tile_Arrow.png")), (tile_size, tile_size))
    except:
        bg_tile = pygame.Surface((tile_size, tile_size))
        bg_tile.fill((100, 100, 100))
        arrow_tile = pygame.Surface((tile_size, tile_size))
        arrow_tile.fill((0, 255, 0))

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
        sub = SUB_FONT.render("Select arrow -> Click grid", True, (200, 200, 200))
        
        # Center text in available space
        avail_w = SCREEN_WIDTH - SIDEBAR_WIDTH
        center_x = SIDEBAR_WIDTH + avail_w // 2
        
        screen.blit(title, (center_x - title.get_width()//2, 20))
        screen.blit(sub, (center_x - sub.get_width()//2, 80))
            

def draw_game_over():
    screen.fill(BLACK)
    font = pygame.font.SysFont(FONTNAME, 55)
    text = font.render("Game Over!", True, (255, 255, 255))
    screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - text.get_height() // 2 - 40))
    text = font.render("CONGRATULATIONS - You won!" if victory else "Better luck next time...", True, (255, 255, 255))
    screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 + text.get_height() // 2 + 40))

def draw():
    screen.fill((0, 0, 0))

    if game_state == GameState.LOBBY:
        draw_lobby()
    elif game_state == GameState.SIMULATION:
        draw_simulation()
    elif game_state == GameState.GAME_OVER:
        draw_game_over()

    apply_crt_effect(screen)

# REMOVE LATER
game = backend_game.Game([], seed=random.randint(0, 2**32 - 1))

while running:
    # Process any packets that came in
    while received:
        packet = received.pop(0)

        if not started and packet["type"] == "INIT_GAME_STATE":
            game = backend_game.Game([], packet["data"]["seed"])
            player_number = packet["data"]["player_number"]
            started = True
            playing = True
        
        elif started and not playing and packet["type"] == "TILE_PLACE":
            try:
                for x in packet["data"]:
                    temp_tile = game.game[x["coords"][1]][x["coords"][0]] 
                    if type(temp_tile) == backend_helper.Tile:
                        temp_tile.add_direction(x["direction"])
            except:
                print("Failed to parse TILE_PLACE data! line 68")

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
