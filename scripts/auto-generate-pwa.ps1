param(
  [datetime]$Date = (Get-Date),
  [switch]$Force
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..")
$LogDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$IsoDate = $Date.ToString("yyyy-MM-dd")
$LogPath = Join-Path $LogDir "auto-generate-$IsoDate.log"

Start-Transcript -Path $LogPath -Append | Out-Null

try {
  Set-Location $Root

  $SchedulePath = Join-Path $Root "config\study_schedule.json"
  $Schedule = Get-Content $SchedulePath -Raw | ConvertFrom-Json
  $FirstExamDate = [datetime]::ParseExact($Schedule.first_exam_date, "yyyy-MM-dd", $null)
  $Weekday = ([int]$Date.DayOfWeek + 6) % 7
  $ExamWeekdays = @($Schedule.exam_weekdays | ForEach-Object { [int]$_ })

  Write-Host "Unesp Odonto automation"
  Write-Host "Date: $IsoDate"
  Write-Host "Root: $Root"

  if ($Date.Date -lt $FirstExamDate.Date) {
    Write-Host "Skipping: schedule starts on $($FirstExamDate.ToString('yyyy-MM-dd'))."
    exit 0
  }

  if ($ExamWeekdays -notcontains $Weekday) {
    Write-Host "Skipping: no exam scheduled for weekday index $Weekday."
    exit 0
  }

  $StatePath = Join-Path $Root "state\prova-$IsoDate.json"
  if ((Test-Path $StatePath) -and -not $Force) {
    Write-Host "Skipping: exam already exists for $IsoDate."
    exit 0
  }

  $Ollama = Get-Command ollama -ErrorAction SilentlyContinue
  $OllamaExe = if ($Ollama) { $Ollama.Source } else { Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe" }
  if (-not (Test-Path $OllamaExe)) {
    throw "Ollama is not installed or not available in PATH. Install Ollama before scheduled generation."
  }

  $env:OLLAMA_MODEL = [Environment]::GetEnvironmentVariable("OLLAMA_MODEL", "User")
  if (-not $env:OLLAMA_MODEL) { $env:OLLAMA_MODEL = "qwen3:4b" }
  $env:OLLAMA_VALIDATOR_MODEL = [Environment]::GetEnvironmentVariable("OLLAMA_VALIDATOR_MODEL", "User")
  if (-not $env:OLLAMA_VALIDATOR_MODEL) { $env:OLLAMA_VALIDATOR_MODEL = $env:OLLAMA_MODEL }
  if (-not $env:OLLAMA_NUM_CTX) { $env:OLLAMA_NUM_CTX = "4096" }
  if (-not $env:OLLAMA_NUM_PREDICT) { $env:OLLAMA_NUM_PREDICT = "700" }
  if (-not $env:OLLAMA_TIMEOUT_SECONDS) { $env:OLLAMA_TIMEOUT_SECONDS = "600" }
  if (-not $env:SOURCE_CONTEXT_CHARS) { $env:SOURCE_CONTEXT_CHARS = "1200" }

  $InstalledModels = & $OllamaExe list
  if ($InstalledModels -notmatch [regex]::Escape($env:OLLAMA_MODEL)) {
    Write-Host "Pulling local model $env:OLLAMA_MODEL..."
    & $OllamaExe pull $env:OLLAMA_MODEL
    if ($LASTEXITCODE -ne 0) { throw "ollama pull failed with exit code $LASTEXITCODE." }
  }

  if ($env:OLLAMA_VALIDATOR_MODEL -ne $env:OLLAMA_MODEL -and $InstalledModels -notmatch [regex]::Escape($env:OLLAMA_VALIDATOR_MODEL)) {
    Write-Host "Pulling local validator model $env:OLLAMA_VALIDATOR_MODEL..."
    & $OllamaExe pull $env:OLLAMA_VALIDATOR_MODEL
    if ($LASTEXITCODE -ne 0) { throw "ollama pull failed with exit code $LASTEXITCODE." }
  }

  Write-Host "Generating exam with local Ollama model $env:OLLAMA_MODEL..."
  & python -m unesp_study exam --date $IsoDate
  if ($LASTEXITCODE -ne 0) { throw "Exam generation failed with exit code $LASTEXITCODE." }

  Write-Host "Exporting shared PWA data..."
  & python -m unesp_study export-web
  if ($LASTEXITCODE -ne 0) { throw "PWA export failed with exit code $LASTEXITCODE." }

  Write-Host "Building PWA..."
  & npm.cmd run build
  if ($LASTEXITCODE -ne 0) { throw "PWA build failed with exit code $LASTEXITCODE." }

  Write-Host "Committing source changes..."
  & git add state web/public/data/exams.json
  if ($LASTEXITCODE -ne 0) { throw "git add failed with exit code $LASTEXITCODE." }

  $Changes = & git status --porcelain
  if ($Changes) {
    & git commit -m "Add scheduled exam $IsoDate"
    if ($LASTEXITCODE -ne 0) { throw "git commit failed with exit code $LASTEXITCODE." }

    & git push origin master
    if ($LASTEXITCODE -ne 0) { throw "git push failed with exit code $LASTEXITCODE." }
  } else {
    Write-Host "No source changes to commit."
  }

  Write-Host "Deploying GitHub Pages..."
  $DeployDir = Join-Path $env:TEMP ("unesp-odonto-pages-" + [guid]::NewGuid().ToString("N"))
  New-Item -ItemType Directory -Path $DeployDir | Out-Null

  try {
    Push-Location $DeployDir
    & git init | Out-Null
    & git config user.name "Codex"
    & git config user.email "codex@local"
    & git remote add origin "https://github.com/wildscampos/unesp-odonto-pwa.git"
    & git checkout --orphan gh-pages | Out-Null
    Pop-Location

    Copy-Item -Path (Join-Path $Root "dist\*") -Destination $DeployDir -Recurse -Force
    New-Item -ItemType File -Path (Join-Path $DeployDir ".nojekyll") -Force | Out-Null

    Push-Location $DeployDir
    & git add .
    & git commit -m "Deploy scheduled exam $IsoDate"
    if ($LASTEXITCODE -ne 0) { throw "Pages commit failed with exit code $LASTEXITCODE." }

    & git push origin gh-pages --force
    if ($LASTEXITCODE -ne 0) { throw "Pages push failed with exit code $LASTEXITCODE." }
    Pop-Location
  } finally {
    if ((Get-Location).Path -eq $DeployDir) {
      Pop-Location
    }
    Remove-Item -LiteralPath $DeployDir -Recurse -Force -ErrorAction SilentlyContinue
  }

  Write-Host "Done: exam $IsoDate generated and published."
} catch {
  Write-Error $_
  exit 1
} finally {
  Stop-Transcript | Out-Null
}
