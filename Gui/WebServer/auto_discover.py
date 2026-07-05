import ipaddress
import socket
import threading
import time

from helper_logs import logger


def get_local_ip():
    destinations = []
    try:
        from tools import GetConfiguredPrinters

        destinations.extend(
            printer["ip"]
            for printer in GetConfiguredPrinters(enabled_only=False)
            if printer.get("ip")
        )
    except (ImportError, OSError):
        pass
    destinations.append("8.8.8.8")

    for destination in destinations:
        candidate = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            candidate.connect((destination, 80))
            local_ip = candidate.getsockname()[0]
            if not local_ip.startswith("127."):
                return local_ip
        except OSError:
            continue
        finally:
            candidate.close()
    return "127.0.0.1"


def broadcast_server_ip(port=12346, broadcast_port=54545):
    local_ip = get_local_ip()
    message = f"WS_SERVER:{local_ip}:{port}"
    logger.log_info(f"Autodiscover: {message}")
    if local_ip == "127.0.0.1":
        logger.log_warning("WebSocket autodiscovery is unavailable on loopback only.")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    broadcast_ip = str(
        ipaddress.ip_network(f"{local_ip}/24", strict=False).broadcast_address
    )
    try:
        try:
            sock.bind((local_ip, 0))
        except OSError:
            pass
        failure_logged = False
        while True:
            try:
                sock.sendto(message.encode(), (broadcast_ip, broadcast_port))
                failure_logged = False
            except OSError as error:
                if not failure_logged:
                    logger.log_warning(f"Autodiscovery broadcast unavailable: {error}")
                    failure_logged = True
            time.sleep(5)
    finally:
        sock.close()


# Start broadcasting in another thread
def start_broadcast_thread():
    t = threading.Thread(
        target=broadcast_server_ip,
        name="websocket-autodiscovery",
        daemon=True,
    )
    t.start()
    return t
