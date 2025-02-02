import requests
import os
from tools import *


BASE_URL = "https://api.bambulab.com/v1"



HEADERS = {
    "User-Agent": "bambu_network_agent/01.09.05.01",
    "X-BBL-Client-Name": "OrcaSlicer",
    "X-BBL-Client-Type": "slicer",
    "X-BBL-Client-Version": "01.09.05.51",
    "X-BBL-Language": "en-US",
    "X-BBL-OS-Type": "linux",
    "X-BBL-OS-Version": "6.2.0",
    "X-BBL-Agent-Version": "01.09.05.01",
    "X-BBL-Executable-info": "{}",
    "X-BBL-Agent-OS-Type": "linux",
    "Accept": "application/json",
    "Content-Type": "application/json",
}



def GetJobID(taskID):
    if taskID == None or taskID == "0":
        print("Error with taks ID")
        return
    # Load credentials from the file
    credentials = ReadCredentials()
    ACCES_TOKEN = credentials.get('access_token')
    HEADERS['Authorization'] = f"Bearer {ACCES_TOKEN}"
    try:
        # Concatenate the base URL with the task ID
        url = BASE_URL + "/iot-service/api/user/task/" + str(taskID)
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            json_data = response.json()
            if "job_id" in json_data:
              return json_data['job_id']
            else:
              print(f"Failed to get job id with status code {response.status_code}: {response.text}")
        else:
            print(f"Failed to get job id with status code {response.status_code}: {response.text}")  
    except Exception as e:
        print(f"An error occurred while getting the tasks: {e}")    
    return None


def GetTaksDetail(jobID):
    if jobID == None or jobID == 0:
        print("Error with taks ID")
        return
    # Load credentials from the file
    credentials = ReadCredentials()
    ACCES_TOKEN = credentials.get('access_token')
    HEADERS['Authorization'] = f"Bearer {ACCES_TOKEN}"
    
    try:
        url = BASE_URL + "/user-service/my/tasks"
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            json_data = response.json()
            if json_data["hits"]:
              for hit in json_data["hits"]:
                if "id" in hit:
                  if hit["id"] == jobID:
                    return hit
            else:
                print("No hits available.")
        else:
            print(f"Failed to get tasks with status code {response.status_code}: {response.text}")  
        return None
    except Exception as e:
        print(f"An error occurred while getting the tasks: {e}")

