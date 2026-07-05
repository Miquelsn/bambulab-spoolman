from helper_logs import logger
import BambuCloud.login
import BambuCloud.slicer_filament
import Spoolman.spoolman_filament
import Spoolman.login
import Local_MQTT.local_mqtt as MQTT


def initialize():
    """Prepare available services without blocking on terminal input."""
    cloud_ready = BambuCloud.login.TestToken()
    if not cloud_ready:
        logger.log_warning(
            "Bambu Cloud authentication is required. Open Settings in the GUI."
        )

    configured_printers = MQTT.ConfigurePrinters()
    spoolman_ready = Spoolman.login.ConfigureSpoolmanApi()

    if not cloud_ready or not spoolman_ready:
        logger.log_info(
            "Startup is waiting for configuration in the GUI; available printers can still be monitored."
        )
        return {
            "cloud_ready": cloud_ready,
            "spoolman_ready": spoolman_ready,
            "printers": configured_printers,
        }

    slicer_filaments = BambuCloud.slicer_filament.ProcessSlicerFilament(
        BambuCloud.slicer_filament.GetSlicerFilaments()
    )
    if slicer_filaments:
        BambuCloud.slicer_filament.SaveFilamentsToFile(slicer_filaments)

    spoolman_filaments = Spoolman.spoolman_filament.ProcessSpoolmanFilament(
        Spoolman.spoolman_filament.GetSpoolmanFilaments()
    )
    if spoolman_filaments:
        Spoolman.spoolman_filament.SaveFilamentsToFile(spoolman_filaments)

    logger.log_info("Initialization completed successfully.")
    return {
        "cloud_ready": cloud_ready,
        "spoolman_ready": spoolman_ready,
        "printers": configured_printers,
    }


if __name__ == "__main__":
    try:
        initialize()
        logger.log_info("Run main.py to start the service.")
    except (KeyboardInterrupt, RuntimeError) as error:
        logger.log_error(str(error))
