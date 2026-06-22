import socket
import threading
import hashlib
import base64

# A list to keep track of all connected client sockets
active_clients = []

def handle_client(conn, addr):
    print(f"[+] Connection from {addr}")
    
    try:
        # Receive the initial HTTP request
        raw_request = conn.recv(1024)
        if not raw_request:
            conn.close()
            return
            
        request = raw_request.decode('utf-8', errors='ignore')
        headers = request.split('\r\n')
        
        # 1. Catch Cloudflare HTTP health checks safely
        if "Upgrade: websocket" not in request and "upgrade: websocket" not in request:
            # Satisfy Cloudflare's probe with a standard 200 OK
            probe_response = "HTTP/1.1 200 OK\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
            conn.sendall(probe_response.encode())
            conn.close()
            return

        # 2. Extract Key Case-Insensitively
        key = None
        for h in headers:
            if ':' in h:
                name, value = h.split(':', 1)
                if name.strip().lower() == 'sec-websocket-key':
                    key = value.strip()
                    break

        if not key:
            print(f"[-] Dropped bad WebSocket request from {addr}")
            conn.close()
            return

        # 3. The WebSocket Handshake Protocol
        magic_string = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        accept_key = base64.b64encode(hashlib.sha1(key.encode() + magic_string).digest()).decode()
        
        handshake_response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n"
        )
        conn.sendall(handshake_response.encode())
        active_clients.append(conn)
        print(f"[*] Handshake successful for {addr}")

        # 4. Listen for incoming frames
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
            message = unmasked.decode('utf-8', errors='ignore')
            
            # 5. Broadcast the received message
            # Server-to-client frames are NOT masked. 
            # 129 in binary is 10000001 (FIN bit set, Opcode 1 for Text)
            broadcast_frame = bytes([129, len(message)]) + message.encode()
            
            for client in active_clients:
                if client != conn:  # Optional: avoid echoing back to the sender
                    try:
                        client.sendall(broadcast_frame)
                    except:
                        pass
                        
    except Exception as e:
        print(f"[-] Exception loop for {addr}: {e}")
    finally:
        if conn in active_clients:
            active_clients.remove(conn)
        conn.close()
        print(f"[-] Connection closed for {addr}")

# Initialize raw TCP socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Allow immediate port reuse after script restart
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# Bind to 0.0.0.0 to catch all local traffic routing
server.bind(('0.0.0.0', 8080))
server.listen(5)

print("Raw WebSocket Server listening on 0.0.0.0:8080...")

# Main execution loop
while True:
    try:
        conn, addr = server.accept()
        # Spin up a new thread for every inbound connection
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        break
    except Exception as e:
        print(f"Server error: {e}")
