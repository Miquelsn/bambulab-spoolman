import http.server
import socketserver
import webbrowser
import threading

PORT = 89
DIRECTORY = "GUI/bambulab_spoolman/build/web"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def log_message(self, format, *args):
        pass  # This suppresses logging

# Start server in a thread
def start_server():
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Serving Flutter web app at http://127.0.0.1:{PORT}")
        httpd.serve_forever()

def start_thread():
    threading.Thread(target=start_server, daemon=True).start()
