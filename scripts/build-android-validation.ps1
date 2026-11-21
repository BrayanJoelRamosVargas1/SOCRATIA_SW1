param([string]$OutputDirectory = "artifacts/android-validacion-20261121")
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path $PSScriptRoot -Parent
$mobileRoot = Join-Path $projectRoot "mobile"
$javaCandidate = "C:\Program Files\Android\Android Studio\jbr"
$previousJava = $env:JAVA_HOME
$previousOptions = $env:JAVA_TOOL_OPTIONS
$previousKey = $env:SOCRATIA_PILOT_KEYSTORE
$originalLocation = Get-Location
try {
    if (Test-Path -LiteralPath (Join-Path $javaCandidate "bin/java.exe")) { $env:JAVA_HOME = $javaCandidate }
    if (-not $env:JAVA_HOME) { throw "Falta JDK 21. No se instalará automáticamente." }
    if (-not $env:SOCRATIA_PILOT_KEYSTORE) { $env:SOCRATIA_PILOT_KEYSTORE = Join-Path $env:USERPROFILE ".android/debug.keystore" }
    if (-not (Test-Path -LiteralPath $env:SOCRATIA_PILOT_KEYSTORE)) { throw "Falta una clave de firma existente. No se generará ni sustituirá una clave." }
    if (-not (Test-Path -LiteralPath (Join-Path $mobileRoot "android/app/google-services.json"))) { throw "Falta configuración Firebase local para validar push en la APK." }
    $socketTemp = Join-Path $projectRoot "artifacts/java-tmp"
    New-Item -ItemType Directory -Force -Path $socketTemp | Out-Null
    $env:JAVA_TOOL_OPTIONS = "$previousOptions -Djdk.net.unixdomain.tmpdir=$socketTemp".Trim()
    Set-Location -LiteralPath $mobileRoot
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw "Falló la interfaz móvil." }
    & node "node_modules/@capacitor/cli/bin/capacitor" sync android
    if ($LASTEXITCODE -ne 0) { throw "Falló la sincronización de Android." }
    Set-Location -LiteralPath (Join-Path $mobileRoot "android")
    & .\gradlew.bat --no-daemon --max-workers=1 "-Dorg.gradle.jvmargs=-Xmx768m -XX:MaxMetaspaceSize=384m" :app:assembleDebug
    if ($LASTEXITCODE -ne 0) { throw "Falló la compilación Android. No se publicará ningún archivo." }
    $destination = [IO.Path]::GetFullPath((Join-Path $projectRoot $OutputDirectory))
    if (-not $destination.StartsWith($projectRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw "El destino debe estar dentro del proyecto." }
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    $source = Join-Path $mobileRoot "android/app/build/outputs/apk/debug/app-debug.apk"
    $target = Join-Path $destination "Socratia-Android-validacion-0.3.0.apk"
    $sdkRoot = if ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { Join-Path $env:LOCALAPPDATA "Android/Sdk" }
    $signer = Join-Path $sdkRoot "build-tools/36.0.0/apksigner.bat"
    $certificate = & $signer verify --print-certs $source
    if ($LASTEXITCODE -ne 0) { throw "La firma de la APK no es válida." }
    Copy-Item -LiteralPath $source -Destination $target
    $digest = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
    "$digest  $([IO.Path]::GetFileName($target))" | Set-Content -LiteralPath (Join-Path $destination "SHA256SUMS.txt")
    $certificate | Set-Content -LiteralPath (Join-Path $destination "SIGNING-CERTIFICATE.txt")
    Set-Location -LiteralPath $projectRoot
    $revision = & git rev-parse HEAD
    $dirty = [bool](& git status --porcelain)
    @{ source_commit=$revision; working_tree_dirty=$dirty; version="0.3.0"; apk_sha256=$digest;
        physical_installation_verified=$false; production_backend_updated=$false;
        note="La firma local puede diferir del piloto: no desinstales la aplicación anterior para reemplazarla sin revisar la firma." } |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $destination "validation.json")
    Write-Output "APK de validación: $target"
    Write-Output "SHA-256: $digest"
} finally {
    $env:JAVA_HOME = $previousJava
    $env:JAVA_TOOL_OPTIONS = $previousOptions
    $env:SOCRATIA_PILOT_KEYSTORE = $previousKey
    Set-Location -LiteralPath $originalLocation
}
