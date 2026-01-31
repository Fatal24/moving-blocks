import enum
import backend_game
import socket
import threading
import time
from helper import send_obj, recv_obj
import random

SERVER_IP = "0.0.0.0"  # <-- Change to host's Wi-Fi IP
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


seed = random.randint(0, 2**32 -1)
game = backend_game.Game([], seed=seed)

def get_list_of_tiles():
    return game.game

while running:
    # Process any packets that came in
    while received:
        packet = received.pop(0)
        print(f"[CLIENT] Got: {packet}")

    while send:
        try:
            o = send.pop(0)
            send_obj(sock, o)
        except:
            print("[CLIENT] Failed to send, host probably disconnected")
            break

    time.sleep(0.1)

sock.close()
