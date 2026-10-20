Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object {
    $_.CommandLine -like "*agent.py*" -or
    $_.CommandLine -like "*widget*" -or
    $_.CommandLine -like "*uvicorn*"
} | ForEach-Object {
    try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch {}
}
Write-Host "MYRA parado." -ForegroundColor Green
Start-Sleep -Seconds 2
