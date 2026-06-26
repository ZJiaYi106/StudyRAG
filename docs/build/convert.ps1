$ErrorActionPreference = "Stop"
$src = "C:\Users\31133\Desktop\StudyRag"
$out = "$src\docs\build\tpl"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$map = @{ "1_*.doc" = "template"; "2_*.doc" = "requirements" }
foreach ($k in $map.Keys) {
  $f = Get-ChildItem -Path $src -Filter $k | Select-Object -First 1
  if ($null -eq $f) { Write-Output "MISSING: $k"; continue }
  $doc = $word.Documents.Open($f.FullName, $false, $true)
  $base = Join-Path $out $map[$k]
  $doc.SaveAs2("$base.docx", 16)
  $doc.SaveAs2("$base.txt", 7)
  $doc.Close($false)
  Write-Output "converted: $k"
}
$word.Quit()
