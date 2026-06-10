# 易策 Windows PowerShell 一键安装脚本

$ErrorActionPreference = "Stop"

Write-Host "🌟 易策 (yice) 安装脚本" -ForegroundColor Cyan
Write-Host ""

function Find-Python {
    $candidates = @("python", "py -3.12", "py -3.11", "python3")

    foreach ($candidate in $candidates) {
        $parts = $candidate -split " "
        $cmd = $parts[0]
        $args = @()
        if ($parts.Length -gt 1) {
            $args = $parts[1..($parts.Length - 1)]
        }

        try {
            $null = & $cmd @args -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) {
                return @{
                    Command = $cmd
                    Args = $args
                }
            }
        }
        catch {
            continue
        }
    }

    return $null
}

$python = Find-Python
if ($null -eq $python) {
    Write-Host "❌ 需要 Python 3.11+" -ForegroundColor Red
    Write-Host "   请安装或升级 Python: https://www.python.org/downloads/"
    exit 1
}

$pythonVersion = & $python.Command @($python.Args + @("--version"))
Write-Host "✅ $pythonVersion ($($python.Command) $($python.Args -join ' '))" -ForegroundColor Green

if (-not (Test-Path "models.json")) {
    Write-Host ""
    Write-Host "⚠️  未找到 models.json 配置文件" -ForegroundColor Yellow
    if (Test-Path "models.example.json") {
        Write-Host "   复制示例配置..."
        Copy-Item "models.example.json" "models.json"
        Write-Host "✅ 已创建 models.json" -ForegroundColor Green
        Write-Host ""
        Write-Host "   🔑 如需启用 LLM 推演，请编辑 models.json 配置你的 API 密钥："
        Write-Host "      - DeepSeek: https://platform.deepseek.com"
    }
}

Write-Host ""
Write-Host "📦 CLI 版本：零依赖，可直接运行"
Write-Host "   python main.py"

Write-Host ""
Write-Host "📦 Web 界面安装（可选）..."
Write-Host ""

if (Test-Path "web/backend") {
    Write-Host "   后端依赖..."
    Push-Location "web/backend"

    $venvScripts = Join-Path "venv" "Scripts"
    $venvBin = Join-Path "venv" "bin"
    $venvPython = Join-Path $venvScripts "python.exe"
    $unixVenvPython = Join-Path $venvBin "python"
    if ((Test-Path "venv") -and -not (Test-Path $venvPython) -and -not (Test-Path $unixVenvPython)) {
        Write-Host "   检测到不完整的虚拟环境，重新创建..."
        Remove-Item "venv" -Recurse -Force
    }

    if (-not (Test-Path "venv")) {
        Write-Host "   创建虚拟环境..."
        & $python.Command @($python.Args + @("-m", "venv", "venv"))
    }

    if (Test-Path $venvPython) {
        & $venvPython -m pip install -r requirements.txt
    }
    elseif (Test-Path $unixVenvPython) {
        & $unixVenvPython -m pip install -r requirements.txt
    }
    else {
        Write-Host "❌ 后端虚拟环境创建失败，未找到 Python 解释器" -ForegroundColor Red
        Pop-Location
        exit 1
    }

    Pop-Location
    Write-Host "   ✅ 后端依赖已安装" -ForegroundColor Green
}

if ((Test-Path "web/frontend") -and (Test-Path "web/frontend/package.json")) {
    Write-Host "   前端依赖..."
    Push-Location "web/frontend"

    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Write-Host "   ⚠️  未检测到 npm，请先安装 Node.js: https://nodejs.org" -ForegroundColor Yellow
    }
    else {
        npm install
        Write-Host "   ✅ 前端依赖已安装" -ForegroundColor Green
    }

    Pop-Location
}

Write-Host ""
Write-Host "✅ 安装完成！" -ForegroundColor Green
Write-Host ""
Write-Host "下一步："
Write-Host "  1. 先试 CLI 本地演示: python main.py"
Write-Host "  2. 如需 LLM 推演，编辑 models.json 配置 API 密钥"
Write-Host "  3. Web 运行: python web/main.py"
Write-Host ""
