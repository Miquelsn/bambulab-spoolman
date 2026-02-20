FROM python:3.14-slim

# WORKDIR must be /app — flutter_web_server.py resolves the web assets
# directory and all runtime data files relative to CWD.
WORKDIR /app

# Disable Python output buffering so logs appear immediately in `docker compose logs`.
ENV PYTHONUNBUFFERED=1

# Install dependencies before copying source so this layer is cached
# independently of code changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application tree (filtered by .dockerignore).
COPY . .

# Inbound ports. Port 8883 (MQTT to printer) is outbound-only, not listed.
EXPOSE 2323
EXPOSE 12346
EXPOSE 54545/udp

# Exec form keeps Python as PID 1 so it receives SIGTERM from docker stop.
CMD ["python", "main.py"]
