import socket
import threading
import time
from helper import send_obj, recv_obj
import random
import backend_game

HOST_IP = "0.0.0.0"
PORT = 6000

clients = []          # list of (conn, addr)
received = []         # list of (conn, packet)
running = True

def accept_loop(server):
    """Accepts new connections and spawns a listener thread for each."""
    while running:
        try:
            conn, addr = server.accept()
            print(f"[HOST] {addr} connected ({len(clients)} total)")

            t = threading.Thread(target=recv_loop, args=(conn, addr), daemon=True)
            t.start()
        except OSError:
            break

def recv_loop(conn, addr):
    """Listens on a single client and pushes packets into received."""
    while running:
        try:
            packet = recv_obj(conn)
            if packet is None:
                break
            received.append((conn, packet))
        except:
            break

    # Clean up on disconnect
    clients[:] = [c for c in clients if c != conn]
    print(f"[HOST] {addr} disconnected ({len(clients)} remaining)")
    conn.close()

def send_to(conn, packet):
    """Send a packet to a specific client."""
    try:
        send_obj(conn, packet)
    except:
        print(f"[HOST] Failed to send to {conn.getpeername()}")

def broadcast(packet, exclude=None):
    """Send a packet to all clients, optionally excluding one."""
    for conn in clients:
        if conn == exclude:
            continue
        send_to(conn, packet)

# Setup
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST_IP, PORT))
server.listen(5)
print(f"[HOST] Listening on port {PORT}...")

# Accept connections in background
threading.Thread(target=accept_loop, args=(server,), daemon=True).start()

seed = random.randint(0, 2**32-1)
game = backend_game.Game([], seed=seed)

started = False

# Main loop

tile_placements = []
number_of_players = 1



while running:
    # Process any packets that came in
    while received:
        conn, packet = received.pop(0)

        if packet["type"] == "INIT_CONNECTION":
            clients.append(conn)

        elif packet["type"] == "TILE_PLACE" and started:
            tile_placements.append(packet["data"])

        print(f"[HOST] Got: {packet}")

    if len(clients) == number_of_players and not started:
        for client in range(len(clients)):
            send_to(clients[client], {"type": "INIT_GAME_STATE", "data": {"seed": seed, "player_number": client+1}})
        started = True

    if len(tile_placements) == number_of_players:
        broadcast({"type": "TILE_PLACE", "data": tile_placements})
        tile_placements = []
    

    # Broadcast host state to everyone
    time.sleep(0.1)

server.close()
