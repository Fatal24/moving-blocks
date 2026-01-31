import socket
import pickle
import struct

'''
 data_packet structure: {type: "INIT_GAME_STATE (server -> user) | 
                                TILE_PLACE (server <-> user) |
                                INIT_CONNECTION (server <- user) |",
                         data: ...}
                                 
'''

def send_obj(conn, obj):
    data = pickle.dumps(obj)
    conn.sendall(struct.pack('>I', len(data)) + data)

def recv_obj(conn):
    raw_len = b""

    while len(raw_len) < 4:
        chunk = conn.recv(4 - len(raw_len))
        if not chunk:
            return None
        raw_len += chunk

    msg_len = struct.unpack('>I', raw_len)[0]

    # Then read exactly that many bytes
    data = b""
    while len(data) < msg_len:
        chunk = conn.recv(msg_len - len(data))
        if not chunk:
            return None
        data += chunk

    return pickle.loads(data)

def recieve_tiles
