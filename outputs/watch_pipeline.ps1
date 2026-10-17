# Monitor en vivo del pipeline pea_drone
$host.UI.RawUI.WindowTitle = "pea_drone - progreso del pipeline"
Set-Location "C:\Trabajo_eterno\drone_images"
Write-Host "Monitor del pipeline pea_drone (Ctrl+C para cerrar; el pipeline sigue corriendo)" -ForegroundColor Cyan
Write-Host "Log: outputs\pipeline_run.log   Estado: outputs\pipeline_status.json`n" -ForegroundColor DarkGray
Get-Content -Path "outputs\pipeline_run.log" -Wait -Tail 60 -Encoding UTF8
