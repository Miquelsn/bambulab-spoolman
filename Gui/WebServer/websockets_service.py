import asyncio
import websockets
import threading
import json

from tools import *
from Local_MQTT.local_mqtt import *
from BambuCloud.login import *

import BambuCloud.slicer_filament
import Spoolman.spoolman_filament
from Filament.filament import *

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
                print(f"📩 Received: {message}")

                # ---------- SIMPLE STRING COMMANDS ----------
                if message == "get_tasks":
                    tasks = self.load_tasks_from_file()
                    response = {"type": "tasks", "payload": tasks}
                    await websocket.send(json.dumps(response))
                    continue

                if message == "get_logs":
                    with open("app.log", "r") as f:
                        log_content = f.read()
                    response = {"type": "logs", "payload": [log_content]}
                    await websocket.send(json.dumps(response))
                    continue

                if message == "get_local_settings":
                    credentials = ReadCredentials()

                    printer_ip = credentials.get('DEFAULT', 'printer_ip', fallback=None)
                    if not (printer_ip and IsValidIp(printer_ip)):
                        printer_ip = ""

                    spoolman_ip = credentials.get('DEFAULT', 'spoolman_ip', fallback="")
                    spoolman_port = int(credentials.get('DEFAULT', 'spoolman_port', fallback=0))

                    response = {
                        "type": "local_settings",
                        "payload": {
                            "printer_ip": printer_ip,
                            "spoolman_ip": spoolman_ip,
                            "spoolman_port": spoolman_port
                        }
                    }
                    await websocket.send(json.dumps(response))
                    continue
                
                if message == "get_bambucloud_settings":
                    credentials = ReadCredentials()

                    email = credentials.get('DEFAULT','email', fallback= None)
                    password = credentials.get('DEFAULT','password', fallback= None)

                    response = {
                        "type": "bambucloud_settings",
                        "payload": {
                            "email": email,
                            "password": password
                        }
                    }
                    await websocket.send(json.dumps(response))
                    continue
                if message == "get_filaments":
                    
                    # Try to update the filament lists
                    filaments = BambuCloud.slicer_filament.GetSlicerFilaments()
                    filaments = BambuCloud.slicer_filament.ProcessSlicerFilament(filaments)
                    if filaments:
                        BambuCloud.slicer_filament.SaveFilamentsToFile(filaments)

                    # Save Filaments From Spoolman
                    filaments = Spoolman.spoolman_filament.GetSpoolmanFilaments()
                    filaments = Spoolman.spoolman_filament.ProcessSpoolmanFilament(filaments)
                    if filaments:
                        Spoolman.spoolman_filament.SaveFilamentsToFile(filaments)

                    bambu_filaments = parse_filaments(BAMBU_FILE)
                    spoolman_filaments = parse_filaments(SPOOLMAN_FILE)
                    mappings = load_mappings()

                    used_spool_ids = set(mappings.values())
                    pending_filaments = [f for f in bambu_filaments.values() if f["id"] not in mappings]

                    # Compute possible matches for unmapped filaments
                    possible_matches = {}
                    for bambu in pending_filaments:
                        match = find_best_match(bambu, spoolman_filaments, used_spool_ids)
                        if match:
                            possible_matches[bambu["id"]] = [spoolman_filaments[match]["id"]]
                        else:
                            # fallback: return all unused spoolman IDs
                            possible_matches[bambu["id"]] = [f["id"] for f in spoolman_filaments.values() if f["id"] not in used_spool_ids]

                    response = {
                        "type": "filaments_data",
                        "payload": {
                            "bambuFilaments": list(bambu_filaments.values()),
                            "spoolmanFilaments": list(spoolman_filaments.values()),
                            "mappings": mappings,
                            "possibleMatches": possible_matches
                        }
                    }
                    await websocket.send(json.dumps(response))

                # ---------- JSON COMMANDS ----------
                try:
                    data = json.loads(message)

                    if data.get("type") == "update_local_settings":
                        payload = data.get("payload", {})

                        printer_ip = payload.get("printer_ip", "")
                        spoolman_ip = payload.get("spoolman_ip", "")
                        spoolman_port = str(payload.get("spoolman_port", 0))

                        SaveNewToken("printer_ip", printer_ip)
                        SaveNewToken("spoolman_ip", spoolman_ip)
                        SaveNewToken("spoolman_port", spoolman_port)
                        StartMQTT()

                        print("⚙️ Settings updated:",
                            printer_ip, spoolman_ip, spoolman_port)

                        # Send confirmation as JSON
                        response = {
                            "type": "settings_saved",
                            "payload": True
                        }
                        await websocket.send(json.dumps(response))
                    
                    elif data.get("type") == "bambu_login":
                        payload = data.get("payload", {})
                        email = payload.get("email", "")
                        password = payload.get("password", "")
                        code = payload.get("code")  # only present when user enters verification code

                        SaveNewToken("email", email)
                        SaveNewToken("password", password)

                        result = LoginAndGetToken(verification_code=code)
                        
                        if result == LOGIN_SUCCESS:
                            if TestToken():
                                print("✅ BambuCloud login successful")
                                StartMQTT()
                            else:
                                print("❌ BambuCloud login failed after obtaining token")
                                result = LOGIN_BAD_CREDENTIALS
                    
                        response = {
                            "type": "bambucloud_login",
                            "payload": result
                        }

                        await websocket.send(json.dumps(response))
    
                except json.JSONDecodeError:
                    print("⚠️ Ignored non-JSON message")

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
    ws_service = WebSocketService(host='0.0.0.0', port=12346)
    websocket_thread = threading.Thread(target=ws_service.run_server)
    websocket_thread.daemon = True
    websocket_thread.start()
