# Open this project in PowerShell and run this file.
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Can cai Python 3.12 truoc." }
}
$AppPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $AppPython -m pip install -r requirements-render.txt
if ($LASTEXITCODE -ne 0) { throw "Cai thu vien that bai." }
& $AppPython scripts/check_hosting.py
if ($LASTEXITCODE -ne 0) { throw "Thieu du lieu hoac mo hinh. Tai goi san pham day du." }
& $AppPython scripts/start_render.py
