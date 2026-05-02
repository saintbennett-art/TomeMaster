$ai1 = Get-Content 'ai_p1.txt' -Raw
$ai2 = Get-Content 'ai_p2.txt' -Raw
$ai = $ai1 + $ai2
Set-Content 'backend/services/ai_service.py' $ai

$ui1 = Get-Content 'ui_p1.txt' -Raw
$ui2 = Get-Content 'ui_p2.txt' -Raw
$ui = $ui1 + $ui2
Set-Content 'frontend/src/components/AnalysisDashboard.tsx' $ui

Remove-Item 'ai_p1.txt'
Remove-Item 'ai_p2.txt'
Remove-Item 'ui_p1.txt'
Remove-Item 'ui_p2.txt'
