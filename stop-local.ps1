# Detiene nz-monitor local (frontend, backend y recolector).
$ErrorActionPreference = 'SilentlyContinue'
foreach ($p in 8000, 5173) {
  Get-NetTCPConnection -LocalPort $p -State Listen -EA SilentlyContinue |
    Select-Object -Expand OwningProcess -Unique |
    ForEach-Object { Stop-Process -Id $_ -Force -EA SilentlyContinue }
}
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -EA SilentlyContinue |
  Where-Object { $_.CommandLine -like '*collector*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -EA SilentlyContinue }
Write-Host 'nz-monitor detenido'
