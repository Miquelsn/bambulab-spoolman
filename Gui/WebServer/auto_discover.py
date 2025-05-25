import socket
import threading
import time
from helper_logs import logger
import socket

def get_local_ip():
    # Método robusto para obtener IP local
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()



def broadcast_server_ip(port=12346, broadcast_port=54545):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    local_ip = get_local_ip()
    port = 12346

    message = f'WS_SERVER:{local_ip}:{port}'
    logger.log_info(f"Autodiscover: {message}")
    while True:
        try:
            sock.sendto(message.encode(), ('<broadcast>', broadcast_port))
        except Exception as e:
            print(f"Broadcast error: {e}")
        time.sleep(5)



# Start broadcasting in another thread
def start_broadcast_thread():
    t = threading.Thread(target=broadcast_server_ip, daemon=True)
    t.start()

