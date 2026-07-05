import asyncio
import json
import threading

import websockets

import BambuCloud.login as bambu_login
import BambuCloud.slicer_filament as slicer_catalog
import Local_MQTT.local_mqtt as local_mqtt
import Spoolman.login as spoolman_login
import Spoolman.spoolman_filament as spoolman_catalog
from Filament.filament import load_mappings, parse_filaments, save_mappings
from BambuPrinter.task_history import (
    enrich_task_history,
    load_filament_catalog,
    load_spool_catalog,
    reassign_task_filament,
)
from BambuPrinter.task_repository import load_tasks
from helper_logs import _legacy_event, logger
from initialization import initialize
from Spoolman.spoolman_filament import LoadFilamentMapping
from tools import GetConfiguredPrinters, ReadCredentials, SavePrinterSetting


class WebSocketService:
    def __init__(self, host="localhost", port=12346, database_path=None):
        self.host = host
        self.port = port
        self.database_path = database_path
        self.connected_clients = set()

    def load_tasks_from_file(
        self,
        path="task.txt",
        filament_path="slicer_filaments.txt",
        spool_path="spoolman_filaments.txt",
    ):
        """Load SQLite history, importing the legacy JSON file once."""
        return enrich_task_history(
            load_tasks(database_path=self.database_path, legacy_path=path),
            load_filament_catalog(filament_path),
            load_spool_catalog(spool_path),
            LoadFilamentMapping(),
        )

    def load_logs_from_file(self, path=None):
        """Return structured recent events; path is retained for test/migration use."""
        if path is None:
            return logger.get_last_logs()
        events = []
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as log_file:
                for line in log_file.read().splitlines()[-1000:]:
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        event = _legacy_event(line)
                    if isinstance(event, dict):
                        events.append(event)
        except FileNotFoundError:
            return []
        except OSError as error:
            logger.log_error(
                f"Could not read application logs: {error}",
                event="log_read_failed",
                subsystem="dashboard",
            )
        return events

    def load_spools_from_file(self, path="spoolman_filaments.txt"):
        catalog = load_spool_catalog(path)
        return sorted(
            [
                {
                    "id": spool_id,
                    "name": details["name"],
                    "type": details["type"],
                    "vendor": details["vendor"],
                }
                for spool_id, details in catalog.items()
            ],
            key=lambda spool: (
                spool["vendor"].casefold(),
                spool["type"].casefold(),
                spool["name"].casefold(),
            ),
        )

    def load_filament_mapping_data(
        self,
        bambu_path="slicer_filaments.txt",
        spoolman_path="spoolman_filaments.txt",
    ):
        bambu_by_name = parse_filaments(bambu_path)
        spoolman_by_name = parse_filaments(spoolman_path)
        mappings = {
            str(key): str(value)
            for key, value in load_mappings().items()
            if "::" not in str(key)
        }
        bambu_filaments = sorted(
            bambu_by_name.values(),
            key=lambda item: (
                item["vendor"].casefold(),
                item["type"].casefold(),
                item["name"].casefold(),
            ),
        )
        spoolman_filaments = sorted(
            spoolman_by_name.values(),
            key=lambda item: (
                item["vendor"].casefold(),
                item["type"].casefold(),
                item["name"].casefold(),
            ),
        )
        used_spools = set(mappings.values())
        possible_matches = {}
        for filament in bambu_filaments:
            current = mappings.get(filament["id"])
            ranked = sorted(
                spoolman_filaments,
                key=lambda spool: (
                    spool["vendor"].casefold() != filament["vendor"].casefold(),
                    spool["type"].casefold() != filament["type"].casefold(),
                    spool["name"].casefold() != filament["name"].casefold(),
                    spool["name"].casefold(),
                ),
            )
            possible_matches[filament["id"]] = [
                str(spool["id"])
                for spool in ranked
                if str(spool["id"]) == current or str(spool["id"]) not in used_spools
            ][:5]
        return {
            "bambuFilaments": bambu_filaments,
            "spoolmanFilaments": spoolman_filaments,
            "mappings": mappings,
            "possibleMatches": possible_matches,
        }

    def update_filament_mapping(self, bambu_id, spoolman_id):
        bambu_id = str(bambu_id or "").strip()
        spoolman_id = None if spoolman_id is None else str(spoolman_id).strip()
        data = self.load_filament_mapping_data()
        valid_bambu_ids = {item["id"] for item in data["bambuFilaments"]}
        valid_spool_ids = {str(item["id"]) for item in data["spoolmanFilaments"]}
        if bambu_id not in valid_bambu_ids:
            raise ValueError("The selected slicer filament no longer exists.")
        if spoolman_id is not None and spoolman_id not in valid_spool_ids:
            raise ValueError("The selected Spoolman spool no longer exists.")

        mappings = load_mappings()
        if spoolman_id is None:
            mappings.pop(bambu_id, None)
        else:
            duplicate = next(
                (
                    key
                    for key, value in mappings.items()
                    if "::" not in str(key)
                    and str(key) != bambu_id
                    and str(value) == spoolman_id
                ),
                None,
            )
            if duplicate is not None:
                raise ValueError(
                    "That Spoolman spool is already mapped to another slicer filament."
                )
            mappings[bambu_id] = spoolman_id
        save_mappings(mappings)
        return self.load_filament_mapping_data()

    def refresh_filament_catalogs(self):
        warnings = []
        slicer_filaments = slicer_catalog.ProcessSlicerFilament(
            slicer_catalog.GetSlicerFilaments()
        )
        if slicer_filaments:
            slicer_catalog.SaveFilamentsToFile(slicer_filaments)
        else:
            warnings.append("Bambu Cloud returned no slicer filaments.")

        spoolman_filaments = spoolman_catalog.ProcessSpoolmanFilament(
            spoolman_catalog.GetSpoolmanFilaments()
        )
        if spoolman_filaments:
            spoolman_catalog.SaveFilamentsToFile(spoolman_filaments)
        else:
            warnings.append("Spoolman is unavailable or returned no spools.")

        data = self.load_filament_mapping_data()
        if warnings:
            data["warning"] = " ".join(warnings)
        return data

    def load_printer_status(self):
        configured = GetConfiguredPrinters(enabled_only=False)
        try:
            from Local_MQTT.local_mqtt import GetPrinterStates

            states = GetPrinterStates()
        except (ImportError, RuntimeError):
            states = {}

        printers = []
        for printer in configured:
            state = states.get(printer["device_id"])
            task = getattr(state, "print_task", None)
            printers.append(
                {
                    "id": printer["device_id"],
                    "name": printer.get("name") or printer["device_id"],
                    "model": printer.get("model") or None,
                    "enabled": printer.get("enabled", True),
                    "connected": state is not None,
                    "state": getattr(
                        getattr(state, "current_state", None), "name", "OFFLINE"
                    ),
                    "progress": round(float(getattr(state, "current_percent", 0))),
                    "task_name": getattr(task, "model_name", None),
                }
            )
        return printers

    def load_settings(self):
        credentials = ReadCredentials()
        connected_ids = set(local_mqtt.GetPrinterStates())
        printers = []
        for printer in GetConfiguredPrinters(enabled_only=False):
            printers.append(
                {
                    "id": printer["device_id"],
                    "name": printer.get("name") or printer["device_id"],
                    "model": printer.get("model") or None,
                    "ip": printer.get("ip") or "",
                    "enabled": printer.get("enabled", True),
                    "connected": printer["device_id"] in connected_ids,
                    "has_access_code": bool(printer.get("access_code")),
                }
            )
        return {
            "cloud": {
                "email": credentials.get("DEFAULT", "email", fallback=""),
                "authenticated": bool(
                    credentials.get("DEFAULT", "access_token", fallback="")
                ),
            },
            "spoolman": {
                "host": credentials.get("DEFAULT", "spoolman_ip", fallback=""),
                "port": credentials.get("DEFAULT", "spoolman_port", fallback="7912"),
            },
            "printers": printers,
        }

    def update_printer_settings(self, request):
        device_id = str(request.get("device_id") or "").strip()
        printers = {
            printer["device_id"]: printer
            for printer in GetConfiguredPrinters(enabled_only=False)
        }
        if device_id not in printers:
            raise ValueError("The selected printer is no longer configured.")

        enabled = request.get("enabled", True) is not False
        ip = str(request.get("ip") or "").strip()
        access_code = str(request.get("access_code") or "").strip()
        if ip and not local_mqtt.IsValidIp(ip):
            raise ValueError("Enter a valid IPv4 address or use automatic discovery.")

        SavePrinterSetting(device_id, "enabled", str(enabled).lower())
        if ip:
            SavePrinterSetting(device_id, "ip", ip)
        if access_code:
            SavePrinterSetting(device_id, "access_code", access_code)
        local_mqtt.RestartMQTT(discover=False)
        return self.load_settings()

    @staticmethod
    def refresh_runtime():
        status = initialize()
        local_mqtt.ReplaceMQTT(status.get("printers", []))

    async def _send_response(self, websocket, response_type, payload):
        await websocket.send(json.dumps({"type": response_type, "payload": payload}))

    @staticmethod
    def _decode_request(message):
        try:
            request = json.loads(message)
        except (TypeError, json.JSONDecodeError):
            request = {"action": str(message)}
        if not isinstance(request, dict):
            return {"action": ""}
        return request

    async def _handle_request(self, websocket, request):
        action = request.get("action")
        if action == "get_tasks":
            await self._send_response(
                websocket,
                "tasks",
                await asyncio.to_thread(self.load_tasks_from_file),
            )
        elif action == "get_logs":
            await self._send_response(websocket, "logs", self.load_logs_from_file())
        elif action == "get_spools":
            await self._send_response(websocket, "spools", self.load_spools_from_file())
        elif action == "get_printers":
            await self._send_response(websocket, "printers", self.load_printer_status())
        elif action == "get_settings":
            await self._send_response(websocket, "settings", self.load_settings())
        elif action == "bambu_login":
            result = await asyncio.to_thread(
                bambu_login.LoginWithCredentials,
                request.get("email"),
                request.get("password"),
            )
            await self._send_response(websocket, "auth_result", result)
            if result.get("status") == "success":
                await asyncio.to_thread(self.refresh_runtime)
            await self._send_response(websocket, "settings", self.load_settings())
        elif action == "bambu_verify":
            result = await asyncio.to_thread(
                bambu_login.SubmitVerificationCode,
                request.get("email"),
                request.get("code"),
            )
            await self._send_response(websocket, "auth_result", result)
            if result.get("status") == "success":
                await asyncio.to_thread(self.refresh_runtime)
            await self._send_response(websocket, "settings", self.load_settings())
        elif action == "discover_printers":
            matched = await asyncio.to_thread(
                local_mqtt.DiscoverAndSavePrinterIPs,
                float(request.get("timeout") or 6.0),
            )
            await asyncio.to_thread(local_mqtt.RestartMQTT, False)
            await self._send_response(
                websocket,
                "printer_discovery_result",
                {
                    "status": "success" if matched else "not_found",
                    "message": (
                        f"Found {len(matched)} configured printer(s)."
                        if matched
                        else "No configured Bambu printers announced themselves on this network."
                    ),
                    "printers": matched,
                },
            )
            await self._send_response(websocket, "settings", self.load_settings())
        elif action == "update_printer":
            try:
                settings = await asyncio.to_thread(
                    self.update_printer_settings, request
                )
            except ValueError as error:
                await self._send_response(
                    websocket,
                    "printer_update_result",
                    {"status": "invalid", "message": str(error)},
                )
                return
            await self._send_response(
                websocket,
                "printer_update_result",
                {"status": "success", "message": "Printer settings saved."},
            )
            await self._send_response(websocket, "settings", settings)
        elif action == "update_spoolman":
            result = await asyncio.to_thread(
                spoolman_login.SaveSpoolmanSettings,
                request.get("host"),
                request.get("port"),
            )
            await self._send_response(websocket, "spoolman_update_result", result)
            if result.get("status") == "success":
                await asyncio.to_thread(self.refresh_runtime)
                await self._send_response(websocket, "settings", self.load_settings())
        elif action == "get_filaments":
            await self._send_response(
                websocket,
                "filaments_data",
                await asyncio.to_thread(self.load_filament_mapping_data),
            )
        elif action == "refresh_filaments":
            await self._send_response(
                websocket,
                "filaments_data",
                await asyncio.to_thread(self.refresh_filament_catalogs),
            )
        elif action == "update_mapping":
            try:
                data = await asyncio.to_thread(
                    self.update_filament_mapping,
                    request.get("bambu_id"),
                    request.get("spoolman_id"),
                )
            except ValueError as error:
                await self._send_response(
                    websocket,
                    "filament_mapping_error",
                    {"message": str(error)},
                )
                return
            await self._send_response(websocket, "filament_mapping_updated", data)
        elif action == "update_task_filament":
            try:
                task = await asyncio.to_thread(
                    reassign_task_filament,
                    request.get("history_id"),
                    request.get("filament_index"),
                    request.get("spool_id"),
                )
            except (KeyError, TypeError, ValueError, RuntimeError) as error:
                logger.log_error(
                    f"Could not update task filament: {error}",
                    event="task_filament_update_failed",
                    subsystem="tasks",
                    task_id=request.get("history_id"),
                )
                await self._send_response(
                    websocket,
                    "mutation_error",
                    {
                        "request": "update_task_filament",
                        "history_id": request.get("history_id"),
                        "filament_index": request.get("filament_index"),
                        "message": str(error),
                    },
                )
                return
            await self._send_response(websocket, "task_updated", task)
        else:
            await self._send_response(websocket, "error", "Unsupported request.")

    async def handle_client(self, websocket):
        self.connected_clients.add(websocket)
        try:
            async for message in websocket:
                await self._handle_request(websocket, self._decode_request(message))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.connected_clients.discard(websocket)

    async def start_server(self):
        server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            max_size=64 * 1024,
            ping_interval=20,
            ping_timeout=20,
        )
        logger.log_info(
            f"WebSocket server started on ws://{self.host}:{self.port}.",
            event="dashboard_api_started",
            subsystem="dashboard",
        )
        await server.wait_closed()

    def run_server(self):
        asyncio.run(self.start_server())


def start_websocket_server():
    ws_service = WebSocketService(host="0.0.0.0", port=12346)
    websocket_thread = threading.Thread(
        target=ws_service.run_server,
        name="websocket-server",
        daemon=True,
    )
    websocket_thread.start()
    return ws_service, websocket_thread
