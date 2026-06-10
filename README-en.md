# yice (易策) - AI Multi-Agent Decision System Based on I Ching Philosophy

> "Yi" means Change. "Ce" means Decision.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Stars](https://img.shields.io/github/stars/RobbyShao-8ag/yice.svg?style=social)](https://github.com/RobbyShao-8ag/yice)

**English** | [中文](README.md)

---

## What is yice?

An AI multi-agent decision system grounded in **I Ching (周易)** philosophy framework.

**NOT fortune-telling.** This is a structured decision analysis system using the I Ching's symbolic system and change logic.

## Try It First: No API Key Required

yice now has a **local demo mode**. If `models.json` is missing, or still contains example API keys, the CLI still runs the full flow with built-in hexagram data, line texts, and six-perspective rules. Add a real LLM key later to upgrade the same pipeline into AI-generated multi-agent analysis.

```bash
python main.py
```

Try a real decision question:

```text
I have an AI tool prototype and two trial customers, but only four months of runway. Should I go full-time now?
```

### For Developers

```bash
python main.py --help
python main.py
python -m pytest tests/test_cli.py tests/test_yao_agents.py tests/test_reporter.py -q
```

Start with `main.py` for the pipeline, `agents/` for role logic, and `data/` for the thick-data design.

### For Vibe Coding / Non-Programmers

1. Run `./setup.sh` (`.\setup.ps1` on Windows PowerShell).
2. Run `python main.py` without configuring an API key.
3. Paste a real decision and check whether the report helps you see environment, resources, risks, strategy, long-term direction, and review points.

## Key Differentiator

| Regular AI Fortune-telling | yice |
|---------------------------|------|
| Single LLM call, black box | **6 parallel AI agents** with different perspectives |
| Result only | **Full transparent reasoning** process |
| Generic answers | **Time, Environment, Risk, Strategy, Planning, Extreme** - six layers |
| Fixed responses | **Multi-model support** - configure different LLMs per agent |

---

## What is I Ching?

The **I Ching (周易)** is an ancient Chinese divination text and philosophical system:

- **64 Hexagrams** representing 64 typical life situations
- **6 Lines (爻)** per hexagram, each with specific meaning
- **Changing Lines** allow transformation to new situations
- Core philosophy: **Change (易)** is the fundamental nature of reality

yice uses this symbolic framework as input for AI agents to analyze decisions from multiple angles.

---

## Quick Start

### 1. One-Click Install

```bash
git clone https://github.com/RobbyShao-8ag/yice.git
cd yice
```

**macOS / Linux / Windows Git Bash / WSL**

```bash
./setup.sh
```

**Windows PowerShell**

```powershell
.\setup.ps1
```

If PowerShell blocks script execution, run this in the current PowerShell window first:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 2. Run the Local Demo

```bash
python main.py
```

Without an API key, the CLI automatically uses local demo mode instead of exiting.

### 3. Optional: Configure API Key

```bash
cp models.example.json models.json
# Edit models.json with your LLM provider API key
python main.py
```

To use a config file in another location:

```bash
YICE_MODELS_CONFIG=/path/to/models.json python main.py
```

---

## 🎯 Model Recommendation: Chinese LLMs for I Ching Analysis

I Ching divination requires deep understanding of:
- **Classical Chinese** (文言文): Ancient grammar, historical references
- **Cultural context**: Concepts like "Time, Position, Change" (时、位、变)
- **Historical background**: Western Zhou system, hexagram evolution logic

Chinese LLMs have higher Chinese training data ratio, providing better understanding for I Ching analysis.

### Recommended Model Mix: DeepSeek V4 Flash + Pro

yice is not a single chatbot. It runs multiple roles in one decision pipeline, and each role has different model requirements. Some roles need speed and cost control; others need stronger reasoning and synthesis. The recommended setup is to use both DeepSeek V4 variants by role:

| Role | Task Profile | Recommended Model | Why |
|------|--------------|-------------------|-----|
| Qigua Agent `qigua_agent` | Multi-turn clarification, background and constraint extraction | `deepseek-v4-flash` | Frequent interaction, faster response, lower cost |
| Scene Router `scene_router` | Classify the question and match it to a 64-hexagram scenario | `deepseek-v4-pro` | Needs stronger semantic judgment and decision-feature matching |
| Yao Agent `yao_agent` | Generate six parallel line analyses | `deepseek-v4-flash` | High call volume, best fit for cost-effective parallel execution |
| Reporter `reporter` | Synthesize all analyses into the final decision reference | `deepseek-v4-pro` | Needs stronger reasoning, consistency, and structured writing |

DeepSeek's official API added `deepseek-v4-pro` and `deepseek-v4-flash` on 2026-04-24. The legacy `deepseek-chat` / `deepseek-reasoner` model names are scheduled for discontinuation on 2026-07-24, so new configurations should use the V4 model names directly.

### Configuration Example

**Recommended DeepSeek V4 setup**
```json
{
  "providers": {
    "deepseek": {
      "api_key": "your-key",
      "base_url": "https://api.deepseek.com",
      "default_model": "deepseek-v4-flash"
    }
  },
  "agents": {
    "qigua_agent": { "provider": "deepseek", "model": "deepseek-v4-flash" },
    "scene_router": { "provider": "deepseek", "model": "deepseek-v4-pro" },
    "yao_agent": { "provider": "deepseek", "model": "deepseek-v4-flash" },
    "reporter": { "provider": "deepseek", "model": "deepseek-v4-pro" }
  }
}
```

**Get API Key:**
- DeepSeek: https://platform.deepseek.com

---

<details>
<summary>📖 Manual Installation</summary>

### Requirements
- Python 3.11+
- Node.js 18+ for the Web version

### CLI Version (Zero Dependencies)
```bash
git clone https://github.com/RobbyShao-8ag/yice.git
cd yice
python main.py

# Optional: enable LLM analysis
cp models.example.json models.json
# Edit models.json to add API key, then run again
python main.py
```

### Web Version: macOS / Linux
```bash
# Backend
cd web/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install

# Start
cd ../..
python web/main.py
```

### Web Version: Windows PowerShell
```powershell
# Backend
cd web\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Frontend
cd ..\frontend
npm install

# Start
cd ..\..
python web\main.py
```

</details>

---

## System Architecture

```
User Question → Qigua Agent (澄清问题) → Scene Router (匹配卦象)
  → 6 Yao Agents (parallel analysis) → Reporter Agent → Decision Report
```

**Six Yao Agents represent six perspectives:**

| Position | Traditional | Modern Mapping |
|----------|-------------|----------------|
| 初爻 (1st) | 潜龙勿用 | Environment Perception |
| 二爻 (2nd) | 见龙在田 | Resource Configuration |
| 三爻 (3rd) | 君子乾乾 | Risk Assessment |
| 四爻 (4th) | 或跃在渊 | Strategy Execution |
| 五爻 (5th) | 飞龙在天 | Long-term Planning |
| 上爻 (6th) | 亢龙有悔 | Result Review |

---

## License

MIT License - Feel free to use, modify, and distribute.

---

## Acknowledgments

- I Ching Wilhelm Translation Dataset (MIT License, Public Domain)
- Classical I Ching scholarship
