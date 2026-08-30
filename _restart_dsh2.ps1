# Temp DSH restart script v2: kill current dsh web (15688), relaunch detached.
Start-Sleep -Seconds 12   # 留时间让当前消息送达
Get-Process -Id 15688,22264 -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 3
Set-Location $env:USERPROFILE
Start-Process -FilePath "node" -ArgumentList "C:\Users\Administrator\AppData\Roaming\npm\node_modules\@deepseek-ai\dsh\lib\bin.js","web" -WindowStyle Hidden
