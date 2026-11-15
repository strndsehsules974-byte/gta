$out = @()
$out += '=== PWD ==='
$out += (Get-Location).Path
$out += '=== TOPLEVEL (root) ==='
$out += (git rev-parse --show-toplevel 2>&1 | Out-String)
$out += '=== TOPLEVEL (wallix-code) ==='
$out += (git -C wallix-code rev-parse --show-toplevel 2>&1 | Out-String)
$out += '=== STATUS (root) ==='
$out += (git status --short 2>&1 | Out-String)
$out += '=== STATUS (wallix-code) ==='
$out += (git -C wallix-code status --short 2>&1 | Out-String)
$out += '=== DIFF STAT (root) ==='
$out += (git diff --stat 2>&1 | Out-String)
$out += '=== STAGED STAT (root) ==='
$out += (git diff --cached --stat 2>&1 | Out-String)
$out += '=== DIFF STAT (wallix-code) ==='
$out += (git -C wallix-code diff --stat 2>&1 | Out-String)
$out += '=== STAGED STAT (wallix-code) ==='
$out += (git -C wallix-code diff --cached --stat 2>&1 | Out-String)
Set-Content -Path 'c:\Users\admin\dilkush007\_git1.txt' -Value $out -Encoding UTF8
Write-Host GITREPORT_DONE
