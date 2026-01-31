import socket

SERVER_IP = "192.168.137.61"  # <-- Change this to the host's Wi-Fi IP
PORT = 6000

print(f"[CLIENT] Connecting to {SERVER_IP}:{PORT}...")

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)  # 5 second timeout so it doesn't hang forever
    sock.connect((SERVER_IP, PORT))
    print("[CLIENT] Connected!\n")

    # Wait for PING from host
    data = sock.recv(1024)
    if data:
        print(f"[CLIENT] Received: {data.decode()} from host")

        # Send PONG back
        sock.sendall(b"PONG")
        print("[CLIENT] Sent PONG back")
        print("[CLIENT] Connection successful!")
    else:
        print("[CLIENT] Connected but received no data.")

    sock.close()

except socket.timeout:
    print("[CLIENT] Connection timed out. Host didn't respond in time.")
except ConnectionRefusedError:
    print("[CLIENT] Connection refused. Is the host running?")
except OSError as e:
    print(f"[CLIENT] Error: {e}")
