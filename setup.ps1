Write-Host "Setting up data files for bambulab-spoolman..."

$emptyFiles = @('credentials.ini', 'task.txt', 'slicer_filaments.txt', 'spoolman_filaments.txt', 'app.log')

foreach ($file in $emptyFiles) {
    if (-not (Test-Path $file)) {
        New-Item -ItemType File -Path $file | Out-Null
        Write-Host "  Created: $file"
    } else {
        Write-Host "  Exists:  $file (skipped)"
    }
}

if (-not (Test-Path 'filament_mapping.json')) {
    '{}' | Set-Content -Path 'filament_mapping.json' -Encoding UTF8
    Write-Host "  Created: filament_mapping.json"
} else {
    Write-Host "  Exists:  filament_mapping.json (skipped)"
}

Write-Host ""
Write-Host "Setup complete. You can now run:"
Write-Host "  docker compose up -d"
