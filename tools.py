import configparser
import os

CONFIG_FILE = "credentials.ini"
SECTION = "DEFAULT"
def ReadCredentials():
    config = configparser.ConfigParser()
    # Create file if it doesn't exist
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as file:
            file.write("[DEFAULT]\n")  # Add an empty DEFAULT section

    config.read(CONFIG_FILE)
    return config

def SaveNewToken(name, token):
    config = ReadCredentials()
    config[SECTION][name] = token
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)
