import socket
import threading
import time
from helper import send_obj, recv_obj

SERVER_IP = "192.168.137.25"  # <-- Change to host's Wi-Fi IP
PORT = 6000

received = []         # incoming packets land here
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

while running:
    # Process any packets that came in
    while received:
        packet = received.pop(0)
        print(f"[CLIENT] Got: {packet}")

    # Send client state to host
    try:
        send_obj(sock, client_data)
    except:
        print("[CLIENT] Failed to send, host probably disconnected")
        break

    client_data["x"] -= 1
    time.sleep(0.1)

sock.close()
