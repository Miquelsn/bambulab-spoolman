import asyncio
import websockets
import threading
import json

class WebSocketService:
    def __init__(self, host='localhost', port=12346):
        self.host = host
        self.port = port
        self.connected_clients = set()

    def load_tasks_from_file(self, path="task.txt"):
        """Parses the task.txt JSON file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading tasks file: {e}")
            return []
        
    def load_logs_from_file(self, path="app.log"):
        """Parses the app.log JSON file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading logs file: {e}")
            return []    
        

    async def handle_client(self, websocket):
        self.connected_clients.add(websocket)
        try:
            async for message in websocket:
                print(f"Received: {message}")

                if message == "get_tasks":
                    tasks = self.load_tasks_from_file()
                    response = {
                        "type": "tasks",
                        "payload": tasks
                    }
                    await websocket.send(json.dumps(response))
                    
                if message == "get_logs":
                    with open("app.log", "r") as f:
                        log_content = f.read()

                    response = {
                        "type": "logs",
                        "payload": [log_content]
                    }
                    await websocket.send(json.dumps(response))
                    
                    
                else:
                    # Echo to sender
                    await websocket.send(f"Echo: {message}")

                    # Broadcast to others
                    for client in self.connected_clients:
                        if client != websocket:
                            await client.send(f"Broadcast: {message}")

        except websockets.exceptions.ConnectionClosed as e:
            print(f"Connection closed: {e}")
        finally:
            self.connected_clients.remove(websocket)

    async def start_server(self):
        server = await websockets.serve(self.handle_client, self.host, self.port)
        print(f"WebSocket server started on ws://{self.host}:{self.port}")
        await server.wait_closed()

    def run_server(self):
        asyncio.run(self.start_server())

# Wrapper to start in thread
def start_websocket_server():
    ws_service = WebSocketService(host='localhost', port=12346)
    websocket_thread = threading.Thread(target=ws_service.run_server)
    websocket_thread.daemon = True
    websocket_thread.start()
