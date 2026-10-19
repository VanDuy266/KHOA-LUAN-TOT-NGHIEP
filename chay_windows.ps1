# Mở PowerShell trong thư mục dự án rồi chạy: powershell -ExecutionPolicy Bypass -File .\chay_windows.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function KiemTraLenh([string]$Buoc) {
    if ($LASTEXITCODE -ne 0) {
        throw "Buoc '$Buoc' bi loi. Dung tai day, khong chay tiep cac lenh sau."
    }
}

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Chua co Python Launcher. Cai Python 3.12 tu python.org roi mo lai VS Code."
}
py -3.12 --version
if ($LASTEXITCODE -ne 0) {
    throw "Chua cai Python 3.12. Chay 'py install 3.12', sau do thu lai."
}
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.12 -m venv .venv
    KiemTraLenh "Tao moi truong"
}
$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $Python -m pip install -r requirements-app.txt
KiemTraLenh "Cai thu vien - hay cho den khi hoan tat"
$DaCoDemo = (Test-Path "artifacts\random_forest.joblib") -and
    (Test-Path "data\clean\sample_measurements.csv") -and
    (Test-Path "reports\dataset_summary.json") -and
    (Test-Path "reports\metrics_summary.csv")
if (-not $DaCoDemo) {
    & $Python scripts\download_data.py
    KiemTraLenh "Tai du lieu"
    & $Python scripts\prepare_data.py
    KiemTraLenh "Lam sach du lieu"
    & $Python -m pip install -r requirements.txt
    KiemTraLenh "Cai thu vien huan luyen"
    & $Python scripts\run_experiment.py
    KiemTraLenh "Huan luyen va danh gia"
} else {
    Write-Host "Da co mo hinh SDU va du lieu mau."
}
if (-not (Test-Path "data\clean\cells\primary_SDU_01.parquet")) {
    & $Python scripts\download_data.py
    KiemTraLenh "Tai SDU day du"
    & $Python scripts\prepare_data.py
    KiemTraLenh "Xu ly SDU"
}
& $Python -m streamlit run app\streamlit_app.py
KiemTraLenh "Chay ung dung"
