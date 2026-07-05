param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)

$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

function Test-Command($Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-FFmpegInstalled() {
    if (Test-Command "ffmpeg") {
        return $true
    }

    $WinGetLink = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\ffmpeg.exe"
    if (Test-Path $WinGetLink) {
        return $true
    }

    $WinGetPackages = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
    if (Test-Path $WinGetPackages) {
        return [bool](Get-ChildItem $WinGetPackages -Recurse -Filter "ffmpeg.exe" -ErrorAction SilentlyContinue | Select-Object -First 1)
    }

    return $false
}

if (-not (Test-Command "py") -and -not (Test-Command "python")) {
    if (Test-Command "winget") {
        Write-Host "Installing Python 3 with winget..."
        winget install --id Python.Python.3.12 -e
    } else {
        throw "Python is not installed and winget is unavailable. Install Python 3 from https://www.python.org/downloads/windows/"
    }
}

if (-not (Test-FFmpegInstalled)) {
    if (Test-Command "winget") {
        Write-Host "Installing FFmpeg with winget..."
        winget install --id Gyan.FFmpeg -e
        Write-Host "If ffmpeg is still not found after install, close and reopen PowerShell, then run this script again."
    } else {
        throw "FFmpeg is not installed and winget is unavailable. Install FFmpeg and add it to PATH."
    }
}

if (Test-Command "py") {
    & py -3 ".\ascii_cat.py" @ScriptArgs
} elseif (Test-Command "python") {
    & python ".\ascii_cat.py" @ScriptArgs
} else {
    throw "Python was not found after installation. Close and reopen PowerShell, then run this script again."
}
