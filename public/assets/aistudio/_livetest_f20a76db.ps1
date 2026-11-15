$py = 'c:\Users\admin\dilkush007\.venv\Scripts\python.exe'
$root = 'c:\Users\admin\dilkush007'
$log = "$root\_live_run.log"
$err = "$root\_live_run.err"
Remove-Item $log, $err -ErrorAction SilentlyContinue
$p = Start-Process -FilePath $py `
    -ArgumentList @('smart_pinterest_agent.py', '--max-pins', '2', '--download') `
    -WorkingDirectory "$root\wallix-code" `
    -RedirectStandardOutput $log -RedirectStandardError $err `
    -PassThru -NoNewWindow
$done = $p.WaitForExit(180000)
if (-not $done) {
    try { $p.Kill() } catch {}
    Write-Host 'LIVE_TIMEOUT'
} else {
    Write-Host "LIVE_EXIT=$($p.ExitCode)"
}
Write-Host '--- LOG ---'
if (Test-Path $log) { Get-Content $log -Encoding UTF8 | ForEach-Object { Write-Host $_ } }
if ((Test-Path $err) -and ((Get-Item $err).Length -gt 0)) {
    Write-Host '--- ERR ---'
    Get-Content $err -Encoding UTF8 | ForEach-Object { Write-Host $_ }
}
Write-Host '--- FILES ---'
foreach ($d in @('staging', 'processed', 'processed\desktop', 'quarantine')) {
    $dp = Join-Path "$root\wallix-code\downloads" $d
    if (Test-Path $dp) {
        Get-ChildItem $dp -File -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Host ($d + ' | ' + $_.Name + ' | ' + $_.Length + ' | ' + $_.LastWriteTime)
        }
    }
}
Write-Host 'LIVEDONE'
