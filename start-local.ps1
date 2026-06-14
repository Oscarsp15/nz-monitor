# Lanzador LOCAL de nz-monitor (solo red WiFi, sin Internet).
# Arranca: backend API (8000) + recolector + frontend build servido (5173).
# Requiere VPN activa para datos reales de Netezza. Idempotente: si ya corre, lo reinicia.
$ErrorActionPreference = 'SilentlyContinue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'

# 1) Liberar puertos y matar recolector previo (evita duplicados)
foreach ($p in 8000, 5173) {
  Get-NetTCPConnection -LocalPort $p -State Listen -EA SilentlyContinue |
    Select-Object -Expand OwningProcess -Unique |
    ForEach-Object { Stop-Process -Id $_ -Force -EA SilentlyContinue }
}
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -EA SilentlyContinue |
  Where-Object { $_.CommandLine -like '*collector*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -EA SilentlyContinue }

# 2) Build del frontend si aún no existe
if (-not (Test-Path (Join-Path $frontend 'dist'))) {
  Start-Process -Wait -WorkingDirectory $frontend -FilePath 'cmd.exe' -ArgumentList '/c', 'npm run build'
}

# 3) Servicios (ventanas minimizadas para poder cerrarlas si quieres)
Start-Process -WindowStyle Minimized -WorkingDirectory $backend -FilePath 'python' `
  -ArgumentList '-m', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', '8000'
Start-Process -WindowStyle Minimized -WorkingDirectory $backend -FilePath 'python' `
  -ArgumentList '-m', 'collector'
Start-Process -WindowStyle Minimized -WorkingDirectory $frontend -FilePath 'cmd.exe' `
  -ArgumentList '/c', 'npm run preview -- --host 0.0.0.0 --port 5173'

Write-Host 'nz-monitor arrancado -> http://192.168.18.210:5173  (requiere VPN para datos)'
