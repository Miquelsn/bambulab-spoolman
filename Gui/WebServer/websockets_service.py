import asyncio
import websockets
import threading

class WebSocketService:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.connected_clients = set()

    async def handle_client(self, websocket):
        """Handles each client connection and echoes messages back."""
        self.connected_clients.add(websocket)
        try:
            async for message in websocket:
                print(f"Received: {message}")
                
                # Send message back to sender
                await websocket.send(f"Echo: {message}")

                # Also broadcast to other clients
                for client in self.connected_clients:
                    if client != websocket:
                        await client.send(f"Broadcast: {message}")

        except websockets.exceptions.ConnectionClosed as e:
            print(f"Connection closed: {e}")
        finally:
            self.connected_clients.remove(websocket)

    async def start_server(self):
        """Starts the WebSocket server."""
        server = await websockets.serve(self.handle_client, self.host, self.port)
        print(f"WebSocket server started on ws://{self.host}:{self.port}")
        await server.wait_closed()

    def run_server(self):
        """Runs the WebSocket server in an asyncio event loop."""
        asyncio.run(self.start_server())

# Wrapper function to start the WebSocket server in a thread
def start_websocket_server():
    ws_service = WebSocketService(host='localhost', port=12345)
    websocket_thread = threading.Thread(target=ws_service.run_server)
    websocket_thread.daemon = True
    websocket_thread.start()
