import socket
import threading
import time
from helper import send_obj, recv_obj

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
            clients.append((conn, addr))
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
    clients[:] = [(c, a) for c, a in clients if c != conn]
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
    for conn, addr in clients:
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

# Main loop
host_data = {"name": "Host", "x": 100, "y": 200}

while running:
    # Process any packets that came in
    while received:
        conn, packet = received.pop(0)
        print(f"[HOST] Got: {packet}")

    # Broadcast host state to everyone
    broadcast(host_data)

    host_data["x"] += 1
    time.sleep(0.1)

server.close()
