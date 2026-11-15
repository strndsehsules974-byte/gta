$py = 'c:\Users\admin\dilkush007\.venv\Scripts\python.exe'
Set-Location 'c:\Users\admin\dilkush007\wallix-code'
& $py 'smart_pinterest_agent.py' --login
Write-Host "LOGIN_EXIT=$LASTEXITCODE"
