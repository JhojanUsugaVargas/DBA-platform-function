<#
  Levanta backend (FastAPI :8005) y frontend (Angular :4200) en ventanas
  independientes de PowerShell, para que no dependan de Antigravity.
  Uso:  .\start.ps1        (reinicia todo)
        .\start.ps1 -Stop  (solo detiene)
#>
param([switch]$Stop)

$root = $PSScriptRoot

function Stop-Project {
    # Mata arboles completos de procesos huerfanos (uvicorn / ng serve), no solo el
    # que escucha el puerto: los huerfanos conservan codigo viejo y confunden al navegador.
    Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -match 'uvicorn app\.main:app|ng(\.cmd)? serve|@angular[\\/]cli' } |
        ForEach-Object { & taskkill /PID $_.ProcessId /T /F 2>$null | Out-Null }

    foreach ($port in 8005, 4200) {
        Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
            Where-Object { $_.OwningProcess -ne 0 } |
            ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    }
}

Stop-Project
if ($Stop) { Write-Host "Servicios detenidos."; return }

Start-Process powershell -ArgumentList '-NoExit', '-Command', `
    "Set-Location '$root\backend'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8005 --reload"

Start-Process powershell -ArgumentList '-NoExit', '-Command', `
    "Set-Location '$root\frontend'; npx ng serve --port 4200"

Write-Host "Backend:  http://127.0.0.1:8005/docs"
Write-Host "Frontend: http://localhost:4200"
