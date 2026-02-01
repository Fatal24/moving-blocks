import enum
import os
import backend_game
import backend_helper
import socket
import threading
import time
import random
from helper import send_obj, recv_obj
import random
import pygame
from Config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, WHITE

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

SERVER_IP = "192.168.137.61"  # <-- Change to host's Wi-Fi IP
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

def draw_lobby():
    font = pygame.font.SysFont(None, 55)
    text = font.render("Lobby - Waiting for everyone to join...", True, (255, 255, 255))
    screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - text.get_height() // 2))

def draw_simulation():
    screen.fill(WHITE)

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
        font = pygame.font.SysFont(None, 45)
        text = font.render("Placing Tiles Phase - Click on a tile and place it on a grid square", True, (0, 0, 0))
        screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 20))
    
    pygame.display.flip()
            

def draw_game_over():
    font = pygame.font.SysFont(None, 55)
    text = font.render("Game Over!", True, (255, 255, 255))
    screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - text.get_height() // 2))

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

    time.sleep(0.1)
    clock.tick(FPS)

sock.close()
