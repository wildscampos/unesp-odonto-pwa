param(
    [int]$Hour = 6,
    [int]$Minute = 30
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = (Get-Command python).Source
$Action = New-ScheduledTaskAction -Execute $Python -Argument "-m unesp_study run" -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.AddHours($Hour).AddMinutes($Minute))
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries

Register-ScheduledTask -TaskName "UnespStudyDaily" -Action $Action -Trigger $Trigger -Settings $Settings -Description "Gera prova diaria da Unesp e resolucao do dia anterior." -Force

Write-Host "Tarefa UnespStudyDaily criada para rodar diariamente as $($Hour.ToString('00')):$($Minute.ToString('00'))."
