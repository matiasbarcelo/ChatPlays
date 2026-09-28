# Keeps ePSXe (running your game), ChatPlays and OBS open on the stream server,
# relaunching whichever one closes or crashes. Edit the paths below, then have
# it start at sign-in with start-watchdog.cmd.

$EpsxeExe = "C:\ePSXe205\ePSXe.exe"
$GameFile = "C:\ePSXe205\isos\game.cue"
$ObsExe = "C:\Program Files\obs-studio\bin\64bit\obs64.exe"
$CheckSeconds = 15

$ChatPlaysExe = @(
    "$env:LOCALAPPDATA\Programs\ChatPlays\ChatPlays.exe",
    "$env:ProgramFiles\ChatPlays\ChatPlays.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

$LogFile = Join-Path $env:LOCALAPPDATA "ChatPlays\watchdog.log"
New-Item -ItemType Directory -Force (Split-Path $LogFile) | Out-Null
$missingReported = @{}

function Write-Log([string]$Message) {
    $line = "{0:yyyy-MM-dd HH:mm:ss}  {1}" -f (Get-Date), $Message
    Add-Content -Path $LogFile -Value $line
}

# Returns $true when it had to start the program.
function Start-IfStopped([string]$ProcessName, [string]$Exe, [string]$Arguments) {
    if (Get-Process -Name $ProcessName -ErrorAction SilentlyContinue) { return $false }
    if (-not $Exe -or -not (Test-Path $Exe)) {
        if (-not $missingReported[$ProcessName]) {
            Write-Log "Can't start ${ProcessName}: '$Exe' not found. Fix the path in watchdog.ps1."
            $missingReported[$ProcessName] = $true
        }
        return $false
    }
    Write-Log "$ProcessName is not running; starting it."
    $start = @{ FilePath = $Exe; WorkingDirectory = (Split-Path $Exe) }
    if ($Arguments) { $start.ArgumentList = $Arguments }
    Start-Process @start
    return $true
}

Write-Log "Watchdog started."
while ($true) {
    # ePSXe first so OBS finds its window to capture; pause after each launch
    # so a program is up before the next one starts.
    if (Start-IfStopped "ePSXe" $EpsxeExe "-nogui -loadiso `"$GameFile`"") { Start-Sleep 5 }
    if (Start-IfStopped "ChatPlays" $ChatPlaysExe "") { Start-Sleep 10 }
    if (Start-IfStopped "obs64" $ObsExe "--startstreaming --disable-shutdown-check") { Start-Sleep 5 }
    Start-Sleep $CheckSeconds
}
