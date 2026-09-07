$ErrorActionPreference = "Stop"

# -----------------------------
# Desktop Clock build script
# -----------------------------

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

$PythonPath = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$IconPath = Join-Path $ProjectRoot "assets\desktop-clock.ico"
$BuildDir = Join-Path $ProjectRoot "build"
$DistDir = Join-Path $ProjectRoot "dist"
$GeneratedSpecDir = Join-Path $BuildDir "pyinstaller"
$BuildCacheDir = Join-Path $BuildDir "pycache"
$OutputExe = Join-Path $ProjectRoot "dist\DesktopClock.exe"

Write-Host ""
Write-Host "========================================"
Write-Host " Desktop Clock - Build"
Write-Host "========================================"
Write-Host ""

# 1. Check virtual environment
if (-not (Test-Path $PythonPath)) {
    Write-Host "Build failed: Python virtual environment not found."
    Write-Host "Expected:"
    Write-Host $PythonPath
    exit 1
}

Write-Host "[1/5] Python environment OK"

# Keep this script ASCII-compatible for Windows PowerShell 5.1.
# Detect Tcl/Tk data directories from the project's Python environment.
$TclLibrary = & $PythonPath -c "import tkinter; print(tkinter.Tcl().eval('info library'))"
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($TclLibrary)) {
    throw "Build failed: Python could not detect the Tcl library directory."
}
$TclLibrary = $TclLibrary.Trim()

$TkVersion = & $PythonPath -c "import _tkinter; print(_tkinter.TK_VERSION)"
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($TkVersion)) {
    throw "Build failed: Python could not detect the Tk version."
}
$TkVersion = $TkVersion.Trim()
$TkLibrary = Join-Path (Split-Path $TclLibrary -Parent) "tk$TkVersion"

if (-not (Test-Path (Join-Path $TclLibrary "init.tcl"))) {
    Write-Host "Build failed: Tcl library not found."
    exit 1
}

if (-not (Test-Path (Join-Path $TkLibrary "tk.tcl"))) {
    Write-Host "Build failed: Tk library not found."
    exit 1
}

$env:TCL_LIBRARY = $TclLibrary
$env:TK_LIBRARY = $TkLibrary

# 2. Check icon
if (-not (Test-Path $IconPath)) {
    Write-Host "Build failed: icon file not found."
    Write-Host "Expected:"
    Write-Host $IconPath
    exit 1
}

Write-Host "[2/5] Icon OK"

# 3. Check PyInstaller
& $PythonPath -m PyInstaller --version | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed: PyInstaller is not installed."
    Write-Host "Install it with:"
    Write-Host ".\.venv\Scripts\python.exe -m pip install pyinstaller"
    exit 1
}

Write-Host "[3/5] PyInstaller OK"

# 4. Prepare directories
if (Test-Path $BuildDir) {
    Remove-Item $BuildDir -Recurse -Force
}

if (Test-Path $DistDir) {
    Remove-Item $DistDir -Recurse -Force
}

New-Item -ItemType Directory -Force $GeneratedSpecDir | Out-Null
New-Item -ItemType Directory -Force $BuildCacheDir | Out-Null
$env:PYTHONPYCACHEPREFIX = $BuildCacheDir

Write-Host "[4/5] Old build files cleaned"

# 5. Build executable
$PyInstallerArgs = @(
    "-m"
    "PyInstaller"
    "--noconfirm"
    "--clean"
    "--windowed"
    "--onefile"
    "--runtime-tmpdir"
    "."
    "--name"
    "DesktopClock"
    "--icon"
    $IconPath
    "--add-data"
    "$IconPath;assets"
    "--specpath"
    $GeneratedSpecDir
    "main.py"
)

Write-Host "[5/5] Building DesktopClock.exe..."
Write-Host ""

& $PythonPath @PyInstallerArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Build failed."
    exit $LASTEXITCODE
}

if (-not (Test-Path $OutputExe)) {
    Write-Host ""
    Write-Host "Build failed: DesktopClock.exe was not generated."
    exit 1
}

Write-Host ""
Write-Host "========================================"
Write-Host " Build succeeded"
Write-Host "========================================"
Write-Host ""
Write-Host "Output:"
Write-Host $OutputExe
Write-Host ""
