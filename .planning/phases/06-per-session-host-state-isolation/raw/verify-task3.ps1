$f = '.planning/phases/06-per-session-host-state-isolation/06-keyring-recon.md'
$c = Get-Content $f -Raw
$ship = ([regex]::Matches($c, '\*\*SHIP: ISOL-04\*\*')).Count
$defer = ([regex]::Matches($c, '\*\*DEFER: ISOL-04\*\*')).Count
if (($ship + $defer) -ne 1) { Write-Host "FAIL: Expected exactly one decision marker; got SHIP=$ship DEFER=$defer"; exit 1 }
if ($c -notmatch '## 3\. Decision') { Write-Host 'FAIL: section 3 missing'; exit 1 }
if ($c -notmatch '## 5\. Open questions') { Write-Host 'FAIL: section 5 missing'; exit 1 }
if ($c -notmatch 'Plan 06-02 consequence') { Write-Host 'FAIL: Plan 06-02 consequence missing'; exit 1 }
$section4 = ([regex]::Matches($c, '(?m)^## 4\.')).Count
if ($section4 -ne 0) { Write-Host "FAIL: section 4 should be omitted (count=$section4)"; exit 1 }
Write-Host "PASS (decision: SHIP=$ship DEFER=$defer)"
exit 0
