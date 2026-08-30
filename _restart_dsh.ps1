# Temp DSH restart script: kill old dsh web processes, wait, relaunch detached.
Start-Sleep -Seconds 12   # 留时间让当前消息送达用户
Get-Process -Id 8688,24408,12980 -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 3
Set-Location $env:USERPROFILE
Start-Process -FilePath "node" -ArgumentList "C:\Users\Administrator\AppData\Roaming\npm\node_modules\@deepseek-ai\dsh\lib\bin.js","web" -WindowStyle Hidden
