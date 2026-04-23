$workspace = Split-Path -Parent $MyInvocation.MyCommand.Path

function Get-PythonCommand {
    $candidates = @(
        "C:\Users\ritam\AppData\Local\Microsoft\WindowsApps\python3.11.exe",
        "python3.11",
        "python",
        "py -3.11"
    )

    foreach ($candidate in $candidates) {
        $commandName = $candidate.Split(' ')[0]
        if (Test-Path $candidate) {
            return $candidate
        }

        if (Get-Command $commandName -ErrorAction SilentlyContinue) {
            return $candidate
        }
    }

    throw "Nao foi encontrado um executavel Python compativel."
}

function Start-DashboardProcess {
    param(
        [string]$Title,
        [string]$ScriptName,
        [string]$PythonCommand
    )

    $scriptPath = Join-Path $workspace $ScriptName
    if (-not (Test-Path $scriptPath)) {
        Write-Warning "Ficheiro nao encontrado: $ScriptName"
        return
    }

    $command = "Set-Location '$workspace'; `$Host.UI.RawUI.WindowTitle = '$Title'; & $PythonCommand '$scriptPath'"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $command | Out-Null
}

$pythonCommand = Get-PythonCommand

$dashboards = @(
    @{ Title = "Dashboard Atual"; Script = "app copy.py" },
    @{ Title = "Mapa Base"; Script = "app.py" },
    @{ Title = "Evolucao Temporal"; Script = "dashboard2.py" },
    @{ Title = "Comparacao por Categoria"; Script = "dashboard3.py" },
    @{ Title = "Comparacao Adaptativa"; Script = "dasboard3_2.py" },
    @{ Title = "Mapa de Precisao"; Script = "dashboard4.py" },
    @{ Title = "Mapa Fish Eye"; Script = "dashboard4_2.py" },
    @{ Title = "Dashboard Experiencia"; Script = "dashboard_experiencia.py" },
    @{ Title = "Modo Escuro"; Script = "modo.escuro.py" }
)

foreach ($dashboard in $dashboards) {
    Start-DashboardProcess -Title $dashboard.Title -ScriptName $dashboard.Script -PythonCommand $pythonCommand
}

Write-Host "Dashboards iniciados em janelas separadas." -ForegroundColor Green