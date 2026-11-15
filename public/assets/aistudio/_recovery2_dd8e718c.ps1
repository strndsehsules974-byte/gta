$out = @()
$out += '=== OOM HITS in root *.txt (last 3 days) ==='
$hits = Get-ChildItem 'c:\Users\admin\dilkush007' -Filter '*.txt' -File -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-3) } |
    Select-String -Pattern 'heap out of memory' -SimpleMatch -ErrorAction SilentlyContinue
foreach ($h in $hits) { $out += ($h.Path + ' :: ' + $h.LineNumber + ' :: ' + $h.Line.Trim()) }
$out += '=== OOM HITS in wallix-code *.txt (last 3 days) ==='
$hits2 = Get-ChildItem 'c:\Users\admin\dilkush007\wallix-code' -Filter '*.txt' -File -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-3) } |
    Select-String -Pattern 'heap out of memory' -SimpleMatch -ErrorAction SilentlyContinue
foreach ($h in $hits2) { $out += ($h.Path + ' :: ' + $h.LineNumber + ' :: ' + $h.Line.Trim()) }
$out += '=== RECENT FILES (root, last 24h) ==='
$out += (Get-ChildItem 'c:\Users\admin\dilkush007' -File -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt (Get-Date).AddHours(-24) } |
    Sort-Object LastWriteTime -Descending |
    ForEach-Object { $_.Name + ' | ' + $_.Length + ' | ' + $_.LastWriteTime } | Out-String)
$out += '=== RECENT FILES (wallix-code, last 24h) ==='
$out += (Get-ChildItem 'c:\Users\admin\dilkush007\wallix-code' -File -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt (Get-Date).AddHours(-24) } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 30 |
    ForEach-Object { $_.Name + ' | ' + $_.Length + ' | ' + $_.LastWriteTime } | Out-String)
Set-Content -Path 'c:\Users\admin\dilkush007\_oom1.txt' -Value $out -Encoding UTF8
Write-Host OOMREPORT_DONE
