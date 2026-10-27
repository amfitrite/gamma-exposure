# Skrip Pembuatan Shortcut Desktop untuk GEX Terminal
$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath('Desktop')
$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$Shortcut = $WshShell.CreateShortcut("$DesktopPath\GEX Terminal.lnk")
$Shortcut.TargetPath = "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\pythonw.exe"
if (-not (Test-Path $Shortcut.TargetPath)) {
    $py = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
    if ($py) { $Shortcut.TargetPath = $py }
}
$Shortcut.Arguments = "`"$RepoDir\gex_terminal.pyw`""
$Shortcut.WorkingDirectory = "$RepoDir"
$Shortcut.IconLocation = "$RepoDir\icon.ico, 0"
$Shortcut.Description = "GEX Terminal - Real-Time Gamma Exposure HUD"
$Shortcut.Save()

Write-Host "[OK] Shortcut 'GEX Terminal' berhasil dibuat di Desktop: $DesktopPath\GEX Terminal.lnk" -ForegroundColor Green
