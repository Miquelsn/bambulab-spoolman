file_path = "credentials.txt"

# Read credentials from a file
def ReadCredentials():
    credentials = {}
    try:
        with open(file_path, 'r') as file:
            for line in file.readlines():
                if '=' in line:
                    key, value = line.strip().split('=')
                    credentials[key] = value
    except Exception as e:
        print(f"Error reading credentials file: {e}")
    return credentials
  
  
  # Save access token to the credentials file
def SaveNewToken(name_token, token):
    try:
      #See if token exists and delete current entry
        credentials = ReadCredentials()
        if credentials.get(name_token):
            with open(file_path, 'r') as file:
                lines = file.readlines()
            with open(file_path, 'w') as file:
                for line in lines:
                    if not line.startswith(name_token):
                        file.write(line)
        # Append the new token to the file
        with open(file_path, 'a') as file:  # Open in append mode
            file.write(f"\n{name_token}={token}")  # Append token to the file
    except Exception as e:
        print(f"Error saving access token: {e}")