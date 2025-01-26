import os
import requests
from tools import *


# Test the Spoolman API endpoint
def TestSpoolmanApi(ip, port):
    url = f"http://{ip}:{port}/api/v1/info"
    try:
        response = requests.get(url, timeout=5)  # Timeout after 5 seconds
        if response.status_code == 200:
            print("Spoolman API is working correctly!")
            return True
        else:
            print(f"Failed to connect with status code {response.status_code}: {response.text}")
    except requests.RequestException as e:
        print(f"Error connecting to Spoolman API: {e}")
    return False

# Prompt user for Spoolman IP and Port
def ConfigureSpoolmanApi():
    # See if the data is in the credentials file
    credentials = ReadCredentials()
    spoolman_ip = credentials.get('spoolman_ip')
    spoolman_port = credentials.get('spoolman_port')
    if spoolman_ip and spoolman_port:
        if TestSpoolmanApi(spoolman_ip, spoolman_port):
            print("Spoolman configuration working")
            return
        
    while True:
        print("Configure Spoolman IP and Port")
        spoolman_ip = input("Enter Spoolman IP: ").strip()
        spoolman_port = input("Enter Spoolman Port (Default is 7912): ").strip()

        # Validate inputs
        if not spoolman_ip or not spoolman_port:
            print("Invalid input. Both IP and Port are required.")
            continue

        # Test the API connection
        if TestSpoolmanApi(spoolman_ip, spoolman_port):
            # Save to credentials file if successful
            SaveNewToken("spoolman_ip", spoolman_ip)    
            SaveNewToken("spoolman_port", spoolman_port)
            print(f"Spoolman configuration completed: IP={spoolman_ip}, Port={spoolman_port}")
            break
        else:
            print("Connection to Spoolman API failed. Please try again.")