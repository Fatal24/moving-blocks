import socket

HOST_IP = "0.0.0.0"
PORT = 6000

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST_IP, PORT))
server.listen(5)

print(f"[HOST] Listening on {HOST_IP}:{PORT}")
print("[HOST] Waiting for connections...\n")

while True:
    conn, addr = server.accept()
    print(f"[HOST] Connection received from {addr[0]}:{addr[1]}")

    # Send a test message
    conn.sendall(b"PING")
    print(f"[HOST] Sent PING to {addr[0]}")

    # Wait for response
    data = conn.recv(1024)
    if data:
        print(f"[HOST] Received: {data.decode()} from {addr[0]}")
        print("[HOST] Connection successful!\n")
    else:
        print(f"[HOST] No response from {addr[0]}\n")

    conn.close()
    print("[HOST] Waiting for next connection...\n")
