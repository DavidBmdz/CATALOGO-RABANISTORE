@echo off
title Detener Rabanistore
echo Deteniendo el servidor local de Rabanistore en el puerto 8000...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ids = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; if ($ids) { $ids | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }; Write-Host 'Servidor detenido.' } else { Write-Host 'No se encontro un servidor escuchando en el puerto 8000.' }"
pause
