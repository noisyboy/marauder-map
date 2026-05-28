import socket
import threading
import hashlib
import base64

# A list to keep track of all connected client sockets
active_clients = []

def handle_client(conn, addr):
    print(f"[+] Connection from {addr}")
    
    # 1. Receive the initial HTTP GET request
    request = conn.recv(1024).decode()
    headers = request.split('\r\n')
    
    # Extract the Sec-WebSocket-Key
    key = next((h.split(': ')[1] for h in headers if 'Sec-WebSocket-Key' in h), None)
    if not key:
        conn.close()
        return

    # 2. The WebSocket Handshake Protocol
    magic_string = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    accept_key = base64.b64encode(hashlib.sha1(key.encode() + magic_string).digest()).decode()
    
    handshake_response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n"
    )
    conn.send(handshake_response.encode())
    active_clients.append(conn)
    print(f"[*] Handshake successful for {addr}")

    # 3. Listen for incoming frames
    try:
        while True:
            data = conn.recv(1024)
            if not data: break
            
            # Extract payload length (assuming < 126 bytes for this prototype)
            payload_len = data[1] & 127
            
            # Extract the 4-byte masking key
            mask_key = data[2:6]
            encrypted_payload = data[6:6+payload_len]
            
            # Unmask the payload using bitwise XOR
            unmasked = bytearray([encrypted_payload[i] ^ mask_key[i % 4] for i in range(len(encrypted_payload))])
            message = unmasked.decode()
            
            # 4. Broadcast the received message to ALL other clients
            # Server-to-client frames are NOT masked. 
            # 129 in binary is 10000001 (FIN bit set, Opcode 1 for Text)
            broadcast_frame = bytes([129, len(message)]) + message.encode()
            
            for client in active_clients:
                client.send(broadcast_frame)
                
    except Exception as e:
        print(f"[-] Disconnected: {e}")
    finally:
        if conn in active_clients:
            active_clients.remove(conn)
        conn.close()

# Initialize raw TCP socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('0.0.0.0', 8080))
server.listen(5)

print("Raw WebSocket Server listening on 0.0.0.0:8080...")

while True:
    conn, addr = server.accept()
    threading.Thread(target=handle_client, args=(conn, addr)).start()
