#!/bin/bash
set -e

echo "Setting up data files for bambulab-spoolman..."

for f in credentials.ini task.txt slicer_filaments.txt spoolman_filaments.txt app.log; do
    if [ ! -f "$f" ]; then
        touch "$f"
        echo "  Created: $f"
    else
        echo "  Exists:  $f (skipped)"
    fi
done

if [ ! -f filament_mapping.json ]; then
    echo '{}'  > filament_mapping.json
    echo "  Created: filament_mapping.json"
else
    echo "  Exists:  filament_mapping.json (skipped)"
fi

echo ""
echo "Setup complete. You can now run:"
echo "  docker compose up -d"
