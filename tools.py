import configparser
import os
import threading


CONFIG_FILE = "credentials.ini"
SECTION = "DEFAULT"
PRINTER_SECTION_PREFIX = "printer:"

_config_lock = threading.RLock()


def _make_private(path):
    """Restrict credential files to the current user on POSIX systems."""
    if os.name == "posix":
        os.chmod(path, 0o600)


def ReadCredentials():
    config = configparser.ConfigParser()
    with _config_lock:
        if not os.path.exists(CONFIG_FILE):
            try:
                descriptor = os.open(
                    CONFIG_FILE,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
                with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                    file.write("[DEFAULT]\n")
            except FileExistsError:
                pass

        config.read(CONFIG_FILE, encoding="utf-8")
        _make_private(CONFIG_FILE)
    return config


def _write_credentials(config):
    temporary_path = f"{CONFIG_FILE}.tmp-{os.getpid()}-{threading.get_ident()}"
    try:
        descriptor = os.open(
            temporary_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as configfile:
            config.write(configfile)
            configfile.flush()
            os.fsync(configfile.fileno())
        os.replace(temporary_path, CONFIG_FILE)
        _make_private(CONFIG_FILE)
    finally:
        try:
            os.remove(temporary_path)
        except FileNotFoundError:
            pass


def SaveNewToken(name, token):
    with _config_lock:
        config = ReadCredentials()
        config[SECTION][name] = str(token)
        _write_credentials(config)


def DeleteToken(name, section=SECTION):
    """Remove a saved value, primarily for retiring legacy secrets."""
    with _config_lock:
        config = ReadCredentials()
        if section == SECTION:
            removed = config[SECTION].pop(name, None) is not None
        elif config.has_section(section):
            removed = config.remove_option(section, name)
        else:
            removed = False
        if removed:
            _write_credentials(config)
        return removed


def _printer_section(device_id):
    return f"{PRINTER_SECTION_PREFIX}{device_id}"


def _first_value(values, *keys):
    for key in keys:
        value = values.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def SavePrinterDevices(devices):
    """Merge all cloud-bound printers into credentials.ini.

    Existing IP addresses, manually entered access codes, and enabled flags are
    retained. The legacy single-printer DEFAULT values are migrated to their
    matching printer section.
    """
    with _config_lock:
        config = ReadCredentials()
        legacy_id = config.get(SECTION, "dev_id", fallback="").strip()
        legacy_ip = config.get(SECTION, "printer_ip", fallback="").strip()
        legacy_code = config.get(SECTION, "dev_acces_code", fallback="").strip()

        saved = 0
        for device in devices or []:
            device_id = _first_value(device, "dev_id", "device_id", "serial")
            if not device_id:
                continue

            section = _printer_section(device_id)
            if not config.has_section(section):
                config.add_section(section)

            values = config[section]
            name = _first_value(device, "name", "dev_name", "device_name")
            model = _first_value(
                device,
                "dev_product_name",
                "product_name",
                "dev_model_name",
                "model",
            )
            access_code = _first_value(
                device, "dev_access_code", "access_code", "dev_acces_code"
            )

            values["device_id"] = device_id
            if name:
                values["name"] = name
            if model:
                values["model"] = model
            if access_code:
                values["access_code"] = access_code
            elif (
                device_id == legacy_id and legacy_code and not values.get("access_code")
            ):
                values["access_code"] = legacy_code
            if device_id == legacy_id and legacy_ip and not values.get("ip"):
                values["ip"] = legacy_ip
            if not values.get("enabled"):
                values["enabled"] = "true"
            saved += 1

        _write_credentials(config)
        return saved


def MigrateLegacyPrinter():
    """Create a printer section from old single-printer credentials if needed."""
    with _config_lock:
        config = ReadCredentials()
        if any(
            section.startswith(PRINTER_SECTION_PREFIX) for section in config.sections()
        ):
            return

        device_id = config.get(SECTION, "dev_id", fallback="").strip()
        if not device_id:
            return

        section = _printer_section(device_id)
        config.add_section(section)
        config[section]["device_id"] = device_id
        config[section]["name"] = device_id
        config[section]["enabled"] = "true"

        printer_ip = config.get(SECTION, "printer_ip", fallback="").strip()
        access_code = config.get(SECTION, "dev_acces_code", fallback="").strip()
        if printer_ip:
            config[section]["ip"] = printer_ip
        if access_code:
            config[section]["access_code"] = access_code
        _write_credentials(config)


def GetConfiguredPrinters(enabled_only=True):
    MigrateLegacyPrinter()
    config = ReadCredentials()
    printers = []
    for section in config.sections():
        if not section.startswith(PRINTER_SECTION_PREFIX):
            continue

        values = config[section]
        try:
            enabled = values.getboolean("enabled", fallback=True)
        except ValueError:
            enabled = True
        if enabled_only and not enabled:
            continue
        device_id = values.get(
            "device_id", section[len(PRINTER_SECTION_PREFIX) :]
        ).strip()
        if not device_id:
            continue
        printers.append(
            {
                "section": section,
                "device_id": device_id,
                "name": values.get("name", device_id).strip() or device_id,
                "model": values.get("model", "").strip(),
                "ip": values.get("ip", "").strip(),
                "access_code": values.get("access_code", "").strip(),
                "enabled": enabled,
            }
        )
    return printers


def SavePrinterSetting(device_id, name, value):
    with _config_lock:
        config = ReadCredentials()
        section = _printer_section(device_id)
        if not config.has_section(section):
            config.add_section(section)
            config[section]["device_id"] = str(device_id)
            config[section]["name"] = str(device_id)
            config[section]["enabled"] = "true"
        config[section][name] = str(value)
        _write_credentials(config)
