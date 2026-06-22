
---

# Marauder Map

A real-time, zero-dependency WebSocket mapping application. This project provides a live, interactive map displaying the geolocation, trajectory, and heading of multiple connected clients.

The architecture is designed to bypass NAT and carrier-grade firewalls by pairing a raw, multi-threaded Python TCP socket server with Cloudflare Zero Trust Tunnels. The frontend is a vanilla web client utilizing Spherical Mercator projections for OpenStreetMap (OSM) tile rendering and device hardware magnetometers for absolute orientation.

## Features

* **Bare-Metal WebSocket Server:** A custom-built Python server utilizing raw TCP sockets, handling the HTTP 101 Switching Protocols handshake, SHA1/Base64 key generation, and bitwise XOR payload unmasking without relying on external WebSocket libraries.
* **Real-Time Trajectory:** Client-side JavaScript calculates angular momentum and trajectory (`Math.atan2`) between coordinate updates to animate footprint vectors.
* **Hardware Magnetometer Integration:** Custom SVG compass bound to absolute device orientation events, utilizing shortest-path angular calculations and linear interpolation (LERP) to eliminate hardware jitter.
* **Garbage Collection:** Automated server-side and client-side sweeping of stale connections and ghost markers.
* **Zero Trust Routing:** End-to-end SSL termination and proxying via `cloudflared` daemon, satisfying the strict HTTPS requirements of the modern HTML5 Geolocation API.

## Architecture Stack

* **Backend:** Python 3 (Raw Sockets, Threading, Hashlib)
* **Frontend:** Vanilla HTML, CSS, JavaScript (No frameworks)
* **Mapping:** OpenStreetMap (OSM) Tile API
* **Network Edge:** Cloudflare Tunnels (`cloudflared`)
* **Deployment:** GitHub Pages (Frontend), Termux/Linux (Backend)

## Prerequisites

* Python 3.8+
* `cloudflared` installed on the host machine
* A registered domain configured with Cloudflare Zero Trust

## Installation and Setup

### 1. Backend Server

The server requires no external Python dependencies. It binds to `0.0.0.0:8080` by default to intercept all local traffic routed by the Cloudflare daemon.

```bash
# Clone the repository
git clone https://github.com/noisyboy/marauder-map.git
cd marauder-map

# Execute the raw socket server
python3 server.py

```

### 2. Network Tunnel Configuration

To expose the local socket securely, initiate a Cloudflare tunnel. Ensure your Zero Trust dashboard routes the public hostname (e.g., `tun.yourdomain.com`) strictly to `http://127.0.0.1:8080`.

```bash
# Authenticate and run the tunnel
cloudflared tunnel run --token <YOUR_CLOUDFLARE_TOKEN>

```

*Note: Ensure "No TLS Verify" is enabled in your Cloudflare Public Hostname settings, as the Python server handles raw HTTP/WS locally.*

### 3. Frontend Deployment

The frontend is designed to be hosted statically via GitHub Pages.

1. Update the WebSocket URI in `index.html` to point to your secure Cloudflare tunnel endpoint:
```javascript
const ws = new WebSocket('wss://tun.yourdomain.com');

```


2. Commit and push the changes to your `main` or `gh-pages` branch.
3. Access the live GitHub Pages URL via a mobile device.

## Protocol Handshake Details

The backend explicitly handles Cloudflare network edge probes to prevent socket termination. Standard HTTP `GET` health checks are caught and satisfied with an `HTTP/1.1 200 OK` response, preventing `EOF` disconnects while preserving the thread for legitimate `Upgrade: websocket` requests.

## Security Considerations

This application was built as a proof-of-concept for handling raw sockets and bypassing strict NAT environments.

* The Python backend currently accepts connections from any origin routed through the tunnel.
* Client-to-server frames are masked, but server-to-client broadcast frames are transmitted unmasked per the RFC 6455 specification.
* Ensure your Cloudflare Access policies are configured strictly if you do not want public users accessing the telemetry feed.

## License

MIT License. See `LICENSE` for more information.
