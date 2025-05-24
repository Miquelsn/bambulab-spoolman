import socket
import threading
import time

def broadcast_server_ip(port=12346, broadcast_port=54545):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    # Get local IP (best-effort)
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    message = f'WS_SERVER:{local_ip}:{port}'
    while True:
        sock.sendto(message.encode(), ('<broadcast>', broadcast_port))
        time.sleep(5)

# Start broadcasting in another thread
def start_broadcast_thread():
    t = threading.Thread(target=broadcast_server_ip, daemon=True)
    t.start()

