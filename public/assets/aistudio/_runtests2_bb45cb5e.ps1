$py = 'c:\Users\admin\dilkush007\.venv\Scripts\python.exe'
$root = 'c:\Users\admin\dilkush007'
$rep = @()

# re-verify py_compile explicitly, record exit
& $py -m py_compile "$root\wallix-code\smart_pinterest_agent.py" "$root\wallix-code\tests\test_agent_pipeline.py" 2>&1 |
    ForEach-Object { $rep += "PC: $_" }
$rep += "PYCOMPILE_EXIT=$LASTEXITCODE"

# full Python pipeline test file
Push-Location "$root\wallix-code"
& $py -m pytest 'tests\test_agent_pipeline.py' -v 2>&1 | ForEach-Object { $rep += $_ }
$fullExit = $LASTEXITCODE
Pop-Location
$rep += "FULL_PYTEST_EXIT=$fullExit"

Set-Content -Path "$root\_pipeline_tests.txt" -Value $rep -Encoding UTF8
Write-Host "FULL_DONE exit=$fullExit"
