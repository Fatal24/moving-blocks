import enum
import math
import os

import numpy as np

import backend_game
import backend_helper
import socket
import threading
import time
import random
from helper import send_obj, recv_obj
import random
import pygame
from Config import *
from fontTools.ttLib import TTFont
FONTNAME = "GothicByte"
font = TTFont(os.path.join("Assets", f"{FONTNAME}.ttf"))
# Pygame setup
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()
pygame.display.set_caption("Moving Blocks")

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

def place_tile(direction, coords):
    try:
        send.append({"type": "TILE_PLACE", "data": {"direction": direction, "coords": coords}})
        game.game[coords[1]][coords[0]].direction = direction
    except:
        print("Invalid placemnet!")

def handle_events():
    global running
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

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
    apply_crt_effect(screen)


def draw_simulation():
    screen.fill(BLACK)

    # Draw grid
    tile_image = pygame.transform.scale(pygame.image.load(os.path.join("Assets", "Tile_Background.png")), (32, 32))
    tile_grid = get_list_of_tiles()
    tile_grid_size = len(tile_grid)
    tile_size = 32
    tile_grid_x, tile_grid_y = (SCREEN_WIDTH - tile_grid_size * tile_size) // 2, (SCREEN_HEIGHT - tile_grid_size * tile_size) // 4
    # Plane grid first
    for i in range(tile_grid_size):
        for j in range(tile_grid_size):
            screen.blit(tile_image, (tile_grid_x + i * tile_size, tile_grid_y + j * tile_size))
    
    # Then draw tiles
    for i in range(tile_grid_size):
        for j in range(tile_grid_size):
            tile = tile_grid[j][i]
            if isinstance(tile, backend_helper.Tile):
                if tile.direction != backend_helper.Direction.STILL:
                    arrow_image = pygame.transform.rotate(
                        pygame.transform.scale(
                            pygame.image.load(os.path.join("Assets", "Tile_Arrow.png")), (32, 32)
                        ),
                        (tile.direction.value - 1) * 90
                    )
                    screen.blit(arrow_image, (tile_grid_x + i * tile_size, tile_grid_y + j * tile_size))
            elif isinstance(tile, backend_helper.Spawner):
                spawner_image = pygame.transform.scale(tile.img, (32, 32)
                )
                screen.blit(spawner_image, (tile_grid_x + i * tile_size, tile_grid_y + j * tile_size))
            elif isinstance(tile, backend_helper.Goal):
                goal_image = pygame.transform.scale(tile.img, (32, 32)
                )
                screen.blit(goal_image, (tile_grid_x + i * tile_size, tile_grid_y + j * tile_size))
    
    # Game phase (Placing tiles)
    if game_phase == GamePhase.PLACING_TILES:
        font = pygame.font.SysFont(FONTNAME, 45)
        text = font.render("Placing Tiles Phase - Click on a tile and place it on a grid square", True, WHITE)
        screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 20))
    
    apply_crt_effect(screen)
            

def draw_game_over():
    screen.fill(BLACK)
    font = pygame.font.SysFont(FONTNAME, 55)
    text = font.render("Game Over!", True, (255, 255, 255))
    screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - text.get_height() // 2 - 40))
    text = font.render("CONGRATULATIONS - You won!" if victory else "Better luck next time...", True, (255, 255, 255))
    screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 + text.get_height() // 2 + 40))
    apply_crt_effect(screen)

def draw():
    screen.fill((0, 0, 0))

    if game_state == GameState.LOBBY:
        draw_lobby()
    elif game_state == GameState.SIMULATION:
        draw_simulation()
    elif game_state == GameState.GAME_OVER:
        draw_game_over()

    pygame.display.flip()

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
