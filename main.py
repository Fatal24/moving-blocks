import enum
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
FONTNAME = "GothicByte"
# Pygame setup
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()

class GameState(enum.Enum):
    LOBBY = 1
    SIMULATION = 2
    GAME_OVER = 3

game_state = GameState.LOBBY

SERVER_IP = "192.168.137.25"  # <-- Change to host's Wi-Fi IP
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

"""# Setup
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
"""
game = None
victory = True
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
    screen.fill(BLACK)
    font = pygame.font.SysFont(FONTNAME, 55)
    text = font.render("Lobby - Waiting for everyone to join...", True, WHITE)
    screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - text.get_height() // 2))
    pygame.display.flip()
    pass

draw_lobby()

def draw_simulation():
    pass

def draw_game_over():
    screen.fill(BLACK)
    font = pygame.font.SysFont(FONTNAME, 55)
    text = font.render("Game Over!", True, (255, 255, 255))
    screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - text.get_height() // 2 - 40))
    text = font.render("CONGRATULATIONS - You won!" if victory else "Better luck next time...", True, (255, 255, 255))
    screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 + text.get_height() // 2 + 40))
    pygame.display.flip()
    pass
draw_game_over()
"""
def draw():
    screen.fill((0, 0, 0))

    if game_state == GameState.LOBBY:
        draw_lobby()
    elif game_state == GameState.SIMULATION:
        draw_simulation()
    elif game_state == GameState.GAME_OVER:
        draw_game_over()

    pygame.display.flip()

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

    def draw():


    time.sleep(0.1)
    clock.tick(FPS)
"""
#sock.close()
