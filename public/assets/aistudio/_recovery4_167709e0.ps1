$diff = git -C wallix-code diff -- smart_pinterest_agent.py 2>&1 | Out-String
Set-Content -Path 'c:\Users\admin\dilkush007\_patch_diff.txt' -Value $diff -Encoding UTF8
$stat = git -C wallix-code diff --stat -- smart_pinterest_agent.py 2>&1 | Out-String
Write-Host '--- STAT ---'
Write-Host $stat
Write-Host PATCHDIFF_DONE
