import concurrent.futures
import ipaddress
import json
import re
import socket
import ssl
import threading
import time
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

from BambuPrinter.bambu_printer import BambuPrinter
from helper_logs import logger
from tools import GetConfiguredPrinters, SavePrinterSetting


PORT = 8883  # MQTT over TLS
USERNAME = "bblp"  # Fixed username for local MQTT

_clients = {}
_printer_states = {}
_mqtt_lock = threading.RLock()

DISCOVERY_PORT = 2021
SSDP_ADDRESS = "239.255.255.250"
SSDP_PORT = 1900


def IsValidIp(ip):
    """Validate an IPv4 address."""
    pattern = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
    if pattern.match(ip or ""):
        return all(0 <= int(part) <= 255 for part in ip.split("."))
    return False


def _printer_label(printer):
    model = f" ({printer['model']})" if printer.get("model") else ""
    return f"{printer.get('name', printer['device_id'])}{model}"


def _new_client(userdata=None):
    # paho-mqtt 1.x and 2.x both support this constructor. Keeping callback
    # API v1 signatures also preserves compatibility with existing installs.
    return mqtt.Client(userdata=userdata, clean_session=True)


def _configure_tls(client):
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)


def CheckMQTTConnection(printer=None, timeout=5.0, quiet=False):
    """Check whether one configured printer's local MQTT broker is reachable."""
    if printer is None:
        printers = GetConfiguredPrinters()
        printer = printers[0] if printers else None
    if not printer or not printer.get("ip") or not printer.get("access_code"):
        return False

    client = _new_client()
    client.username_pw_set(USERNAME, printer["access_code"])
    _configure_tls(client)
    connected = threading.Event()
    result = {"code": None}

    def connection_result(_client, _userdata, _flags, reason_code, properties=None):
        result["code"] = reason_code
        connected.set()

    client.on_connect = connection_result
    loop_started = False
    try:
        client.connect(printer["ip"], PORT, 10)
        client.loop_start()
        loop_started = True
        if not connected.wait(timeout):
            if not quiet:
                logger.log_error(
                    f"Timed out authenticating to {_printer_label(printer)} at "
                    f"{printer['ip']}."
                )
            return False
        if result["code"] != 0:
            if not quiet:
                logger.log_error(
                    f"MQTT authentication failed for {_printer_label(printer)} "
                    f"(code {result['code']})."
                )
            return False
        return True
    except Exception as error:
        if not quiet:
            logger.log_error(
                f"Could not connect to {_printer_label(printer)} at {printer['ip']}: {error}"
            )
        return False
    finally:
        if loop_started:
            client.loop_stop()
        try:
            client.disconnect()
        except Exception:
            pass


def _parse_discovery_packet(payload, source_ip=""):
    try:
        message = payload.decode("utf-8", errors="replace")
    except AttributeError:
        message = str(payload)
    headers = {}
    for line in message.replace("\r\n", "\n").split("\n"):
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()

    device_type = headers.get("nt") or headers.get("st") or ""
    if "bambulab-com:device:3dprinter" not in device_type:
        return None

    serial = headers.get("usn", "").removeprefix("uuid:").split("::", 1)[0]
    location = headers.get("location", "")
    parsed_location = urlparse(
        location if "://" in location else f"//{location}",
        scheme="http",
    )
    ip = parsed_location.hostname or source_ip
    if not serial or not IsValidIp(ip):
        return None
    return {
        "device_id": serial,
        "ip": ip,
        "name": headers.get("devname.bambu.com", ""),
        "model": headers.get("devmodel.bambu.com", ""),
    }


def DiscoverPrinters(timeout=6.0, socket_factory=socket.socket):
    """Listen for Bambu SSDP announcements and return printers by serial."""
    discovered = {}
    listener = socket_factory(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except OSError:
                pass
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        listener.bind(("", DISCOVERY_PORT))
        listener.settimeout(0.25)

        query = (
            "M-SEARCH * HTTP/1.1\r\n"
            f"HOST: {SSDP_ADDRESS}:{SSDP_PORT}\r\n"
            'MAN: "ssdp:discover"\r\n'
            "MX: 2\r\n"
            "ST: urn:bambulab-com:device:3dprinter:1\r\n\r\n"
        ).encode("ascii")
        try:
            listener.sendto(query, (SSDP_ADDRESS, SSDP_PORT))
            listener.sendto(query, ("255.255.255.255", SSDP_PORT))
        except OSError:
            logger.log_info(
                "Bambu broadcast discovery is unavailable; trying the authenticated subnet scan."
            )

        deadline = time.monotonic() + max(0.0, float(timeout))
        while time.monotonic() < deadline:
            try:
                payload, address = listener.recvfrom(8192)
            except socket.timeout:
                continue
            except OSError:
                break
            printer = _parse_discovery_packet(payload, address[0])
            if printer:
                discovered[printer["device_id"].casefold()] = printer
    except OSError as error:
        logger.log_warning(f"Automatic printer discovery is unavailable: {error}")
    finally:
        listener.close()
    return list(discovered.values())


def DiscoverAndSavePrinterIPs(timeout=6.0, discovery_func=DiscoverPrinters):
    """Match LAN announcements to cloud-bound serials and save their IPs."""
    configured = {
        printer["device_id"].casefold(): printer
        for printer in GetConfiguredPrinters(enabled_only=False)
    }
    matched = []
    matched_ids = set()
    for discovered in discovery_func(timeout=timeout):
        saved = configured.get(discovered["device_id"].casefold())
        if not saved:
            continue
        if saved.get("ip") != discovered["ip"]:
            SavePrinterSetting(saved["device_id"], "ip", discovered["ip"])
        matched.append({**saved, **discovered, "enabled": saved.get("enabled", True)})
        matched_ids.add(saved["device_id"].casefold())
        logger.log_info(
            f"Discovered {_printer_label(matched[-1])} at {discovered['ip']}.",
            event="printer_discovered",
            subsystem="mqtt",
            printer_id=saved["device_id"],
        )
    unmatched = [
        printer
        for key, printer in configured.items()
        if key not in matched_ids and printer.get("access_code")
    ]
    excluded_ips = {printer["ip"] for printer in matched}
    matched.extend(DiscoverPrintersBySubnetScan(unmatched, excluded_ips=excluded_ips))
    return matched


def _mqtt_port_open(ip, timeout):
    try:
        with socket.create_connection((ip, PORT), timeout=timeout):
            return ip
    except OSError:
        return None


def DiscoverPrintersBySubnetScan(
    printers,
    *,
    excluded_ips=None,
    socket_timeout=0.12,
    max_workers=32,
    connection_checker=CheckMQTTConnection,
):
    """Fallback discovery for networks where SSDP broadcasts are filtered."""
    printers = [printer for printer in printers if printer.get("access_code")]
    if not printers:
        return []

    networks = []
    for printer in printers:
        if IsValidIp(printer.get("ip")):
            network = ipaddress.ip_network(f"{printer['ip']}/24", strict=False)
            if network not in networks:
                networks.append(network)
    if not networks:
        return []

    excluded_ips = set(excluded_ips or ())
    candidates = []
    for network in networks:
        candidates.extend(
            str(ip) for ip in network.hosts() if str(ip) not in excluded_ips
        )

    open_hosts = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for result in executor.map(
            lambda ip: _mqtt_port_open(ip, socket_timeout), candidates
        ):
            if result:
                open_hosts.append(result)

    matched = []
    remaining = list(printers)
    for host in open_hosts:
        ordered = sorted(remaining, key=lambda printer: printer.get("ip") != host)
        for printer in ordered:
            candidate = {**printer, "ip": host}
            if not connection_checker(candidate, timeout=3.0, quiet=True):
                continue
            SavePrinterSetting(printer["device_id"], "ip", host)
            discovered = {**printer, "ip": host}
            matched.append(discovered)
            remaining.remove(printer)
            logger.log_info(
                f"Found {_printer_label(discovered)} at {host} by authenticated LAN scan.",
                event="printer_discovered",
                subsystem="mqtt",
                printer_id=printer["device_id"],
            )
            break
        if not remaining:
            break
    return matched


def ConfigurePrinters(connection_checker=CheckMQTTConnection, discover=True):
    """Discover and verify enabled printers without terminal interaction."""
    printers = GetConfiguredPrinters()
    if not printers:
        logger.log_warning(
            "No enabled Bambu Lab printers are configured. Use Settings in the GUI."
        )
        return []

    if discover:
        DiscoverAndSavePrinterIPs()
        printers = GetConfiguredPrinters()

    configured = []
    for printer in printers:
        label = _printer_label(printer)
        if not printer.get("access_code"):
            logger.log_warning(
                f"Skipping {label}: add its LAN access code in Settings.",
                event="printer_configuration_required",
                subsystem="mqtt",
                printer_id=printer["device_id"],
            )
            continue
        if not IsValidIp(printer.get("ip")):
            logger.log_warning(
                f"Skipping {label}: it was not found on the local network.",
                event="printer_offline_skipped",
                subsystem="mqtt",
                printer_id=printer["device_id"],
            )
            continue
        if not connection_checker(printer):
            logger.log_warning(
                f"Skipping {label}: the printer is offline or its LAN access code is invalid.",
                event="printer_offline_skipped",
                subsystem="mqtt",
                printer_id=printer["device_id"],
            )
            continue
        logger.log_info(f"Connected to {label} at {printer['ip']} successfully.")
        configured.append(printer)

    return configured


def GetPrinterIP():
    """Backward-compatible alias for the old single-printer setup function."""
    return ConfigurePrinters()


def SendStatusMessage(client, printer=None):
    """Request a full status payload from one printer."""
    if printer is None:
        printer = (getattr(client, "_userdata", None) or {}).get("printer")
    if not printer:
        raise ValueError("Printer context is required to request status")
    topic = f"device/{printer['device_id']}/request"
    message = {
        "pushing": {
            "sequence_id": "0",
            "command": "pushall",
            "version": 1,
            "push_target": 1,
        }
    }
    client.publish(topic, json.dumps(message))


def OnConnect(client, userdata, flags, rc, properties=None):
    printer = userdata["printer"]
    if rc != 0:
        logger.log_error(
            f"MQTT connection to {_printer_label(printer)} failed with code {rc}."
        )
        return
    topic = f"device/{printer['device_id']}/report"
    client.subscribe(topic)
    logger.log_info(f"Listening for {_printer_label(printer)} on {topic}.")
    SendStatusMessage(client, printer)


def OnMessage(client, userdata, msg):
    try:
        userdata["state"].ProcessMQTTMessage(msg)
    except Exception as error:
        printer = userdata["printer"]
        logger.log_error(
            f"Failed to process a message from {_printer_label(printer)}.",
            event="printer_message_failed",
            subsystem="mqtt",
            printer_id=printer["device_id"],
        )
        logger.log_exception(
            error,
            event="printer_message_exception",
            subsystem="mqtt",
            printer_id=printer["device_id"],
        )


def OnDisconnect(client, userdata, rc, properties=None):
    if rc != 0:
        logger.log_error(
            f"Unexpected MQTT disconnect from {_printer_label(userdata['printer'])} "
            f"(code {rc}); paho-mqtt will retry.",
            event="printer_disconnected",
            subsystem="mqtt",
            printer_id=userdata["printer"]["device_id"],
            reason_code=rc,
        )


def _start_mqtt(printers=None):
    """Start one independent MQTT connection and state machine per printer."""
    if printers is None:
        printers = GetConfiguredPrinters()
    if not printers:
        logger.log_warning("No printers are enabled; MQTT monitoring is idle.")
        return {}

    started = {}
    for printer in printers:
        device_id = printer["device_id"]
        if not printer.get("ip") or not printer.get("access_code"):
            logger.log_error(
                f"Skipping {_printer_label(printer)} because its IP or access code is missing."
            )
            continue

        state = BambuPrinter(
            printer_id=device_id,
            printer_name=printer.get("name"),
            printer_model=printer.get("model"),
        )
        userdata = {"printer": printer, "state": state}
        client = _new_client(userdata=userdata)
        client.username_pw_set(USERNAME, printer["access_code"])
        _configure_tls(client)
        client.on_connect = OnConnect
        client.on_message = OnMessage
        client.on_disconnect = OnDisconnect

        try:
            client.connect(printer["ip"], PORT, 60)
            client.loop_start()
        except Exception as error:
            logger.log_error(
                f"Failed to start MQTT for {_printer_label(printer)} at "
                f"{printer['ip']}: {error}"
            )
            continue

        _clients[device_id] = client
        _printer_states[device_id] = state
        started[device_id] = client
        logger.log_info(
            f"Started MQTT for {_printer_label(printer)} at {printer['ip']}.",
            event="printer_connected",
            subsystem="mqtt",
            printer_id=device_id,
        )

    if not started:
        logger.log_warning(
            "No configured printers are currently available; the service will remain running."
        )
    return started


def StartMQTT(printers=None):
    with _mqtt_lock:
        return _start_mqtt(printers)


def _stop_mqtt():
    for client in list(_clients.values()):
        client.loop_stop()
        client.disconnect()
    _clients.clear()
    _printer_states.clear()


def StopMQTT():
    with _mqtt_lock:
        _stop_mqtt()


def ReplaceMQTT(printers):
    """Atomically replace active clients with an already verified printer list."""
    with _mqtt_lock:
        _stop_mqtt()
        return _start_mqtt(printers)


def RestartMQTT(discover=False):
    """Apply GUI configuration changes without restarting the Python service."""
    with _mqtt_lock:
        _stop_mqtt()
        if discover:
            DiscoverAndSavePrinterIPs()
        return _start_mqtt(ConfigurePrinters(discover=False))


def GetPrinterStates():
    return dict(_printer_states)
