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

# Verificar e iniciar PostgreSQL si no está activo
$pgPort = Get-NetTCPConnection -LocalPort 5432 -ErrorAction SilentlyContinue
if (-not $pgPort) {
    Write-Host "Iniciando servicio de PostgreSQL..." -ForegroundColor Cyan
    $pgService = Get-Service -Name *postgres* -ErrorAction SilentlyContinue | Where-Object { $_.Status -ne 'Running' } | Select-Object -First 1
    if ($pgService) {
        Start-Service $pgService.Name -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    } else {
        $pgCtl = "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe"
        $pgData = "C:\Program Files\PostgreSQL\18\data"
        if ((Test-Path $pgCtl) -and (Test-Path $pgData)) {
            & $pgCtl start -D $pgData
            Start-Sleep -Seconds 2
        }
    }
}

$backendPath = Join-Path $root "backend"
$frontendPath = Join-Path $root "frontend"

$pythonExe = (where.exe python | Where-Object { $_ -notmatch 'WindowsApps' } | Select-Object -First 1)
if (-not $pythonExe) { $pythonExe = "python" }

Start-Process powershell -ArgumentList '-ExecutionPolicy', 'Bypass', '-NoExit', '-Command', `
    "`$host.ui.RawUI.WindowTitle = 'DataCheck - Backend (:8005)'; Set-Location -LiteralPath '$backendPath'; & '$pythonExe' -m uvicorn app.main:app --host 127.0.0.1 --port 8005 --reload"

Start-Process powershell -ArgumentList '-ExecutionPolicy', 'Bypass', '-NoExit', '-Command', `
    "`$host.ui.RawUI.WindowTitle = 'DataCheck - Frontend (:4200)'; Set-Location -LiteralPath '$frontendPath'; npx ng serve --host 0.0.0.0 --port 4200"

Write-Host "Backend:  http://127.0.0.1:8005/docs" -ForegroundColor Green
Write-Host "Frontend: http://localhost:4200" -ForegroundColor Green

