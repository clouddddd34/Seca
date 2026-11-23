param([string]$Path = '/', [string]$LinkedFrom = 'User-supplied URL')
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Net.Http
$origin = 'http://127.0.0.1:2164'
$uri = [Uri]::new([Uri]$origin, $Path)
if ($uri.GetLeftPart([UriPartial]::Authority) -ne $origin) { throw 'Outside authorized origin' }
$logPath = Join-Path (Get-Location).Path 'requests.jsonl'
$count = 0
if (Test-Path -LiteralPath $logPath) { $count = @(Get-Content -LiteralPath $logPath).Count }
if ($count -ge 40) { throw 'Request budget exhausted' }
$id = $count + 1
$handler = [System.Net.Http.HttpClientHandler]::new()
$handler.AllowAutoRedirect = $false
$handler.UseCookies = $false
$handler.UseProxy = $false
$client = [System.Net.Http.HttpClient]::new($handler)
$client.Timeout = [TimeSpan]::FromSeconds(15)
$record = [ordered]@{id=$id;method='GET';url=$uri.AbsoluteUri;linkedFrom=$LinkedFrom;utc=[DateTime]::UtcNow.ToString('o')}
$record | ConvertTo-Json -Compress | Add-Content -LiteralPath $logPath
try {
 $response = $client.GetAsync($uri).GetAwaiter().GetResult()
 $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
 $headers = ($response.Headers.ToString() + $response.Content.Headers.ToString())
 $headers = [regex]::Replace($headers, '(?im)^(Set-Cookie|Cookie|Authorization):.*$', '$1: [REDACTED]')
 $body = [regex]::Replace($body, '(?is)(<input\b[^>]*\bvalue\s*=\s*)(["''])(.*?)\2', '$1$2[REDACTED]$2')
 $body = [regex]::Replace($body, '(?i)((?:csrf[\w-]*|password|passwd|secret|access_token|api_key|session_token)\s*["'']?\s*[:=]\s*["'']?)[^\s"''<>,;}]+', '$1[REDACTED]')
 $body = [regex]::Replace($body, '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '[REDACTED EMAIL]')
 $evidence = "Request $id GET $($uri.AbsoluteUri)`nLinked from: $LinkedFrom`nStatus: $([int]$response.StatusCode)`n$headers`n$body"
 $file = Join-Path (Get-Location).Path ('evidence-{0:D2}.txt' -f $id)
 $evidence | Set-Content -LiteralPath $file
 $evidence
} finally { $client.Dispose(); $handler.Dispose() }

