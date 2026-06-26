
$ErrorActionPreference = "Stop"
$src = "C:\Users\31133\Desktop\StudyRag"
$docx = (Get-ChildItem -Path $src -Filter "*.docx" |
         Where-Object { $_.Name -notlike "~*" } | Select-Object -First 1).FullName
if (-not $docx) { Write-Output "DOCX NOT FOUND"; exit 1 }
Write-Output "opening: $docx"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$d = $word.Documents.Open($docx, $false, $false)
Write-Output "toc count: $($d.TablesOfContents.Count)"
foreach ($toc in $d.TablesOfContents) { $toc.Update() }
$d.Repaginate()
Write-Output "pages: $($d.ComputeStatistics(2))"
$d.Save()
$d.ExportAsFixedFormat("$src\docs\build\report\preview.pdf", 17)
$d.Close($false)
$word.Quit()
Write-Output "DONE"
