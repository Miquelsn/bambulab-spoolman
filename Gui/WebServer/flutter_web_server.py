import http.server
from pathlib import Path
import socketserver
import threading

from helper_logs import logger

PORT = 2323
# Should point to the *folder*, not the index.html file
DIRECTORY = Path(__file__).resolve().parents[1] / "bambulab_spoolman/build/web"


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def log_message(self, format, *args):
        pass  # Suppress logs if desired


def start_server():
    if not (DIRECTORY / "index.html").exists():
        raise FileNotFoundError(
            "Flutter web build not found. Run 'flutter build web' in "
            "Gui/bambulab_spoolman first."
        )
    with ReusableTCPServer(("0.0.0.0", PORT), Handler) as httpd:
        logger.log_info(f"Serving the dashboard at http://127.0.0.1:{PORT}.")
        httpd.serve_forever()


def start_thread():
    thread = threading.Thread(
        target=start_server,
        name="flutter-web-server",
        daemon=True,
    )
    thread.start()
    return thread
