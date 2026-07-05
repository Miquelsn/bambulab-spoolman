import os
import sys
import threading
import time
import webbrowser

from Gui.WebServer.auto_discover import start_broadcast_thread
from helper_logs import logger
import Local_MQTT.local_mqtt as MQTT
import Gui.WebServer.flutter_web_server as flutter_web_server
import Gui.WebServer.websockets_service as websocket_service
from initialization import initialize


def _initialize_runtime():
    try:
        status = initialize()
        MQTT.StartMQTT(status.get("printers", []))
    except Exception as error:
        logger.log_exception(error)
        logger.log_warning(
            "Background setup did not finish. Correct the settings in the GUI and retry."
        )


def _open_dashboard():
    if os.environ.get("BAMBU_OPEN_BROWSER", "1").lower() in {"0", "false", "no"}:
        return
    webbrowser.open("http://127.0.0.1:2323")


def main():
    try:
        flutter_web_server.start_thread()
        start_broadcast_thread()
        websocket_service.start_websocket_server()
        threading.Thread(
            target=_initialize_runtime,
            name="background-initialization",
            daemon=True,
        ).start()
        threading.Timer(1.0, _open_dashboard).start()
        logger.log_info(
            "Service started. Configuration is available at http://127.0.0.1:2323."
        )

        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        logger.log_info("Stopping service.")
    except Exception as error:
        logger.log_exception(error)
        return 1
    finally:
        MQTT.StopMQTT()
    return 0


if __name__ == "__main__":
    sys.exit(main())
