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
./setup.sh
```

### 2. Configure API Key

Edit `models.json` with your LLM provider API key.

---

## 🎯 Model Recommendation: Chinese LLMs for I Ching Analysis

I Ching divination requires deep understanding of:
- **Classical Chinese** (文言文): Ancient grammar, historical references
- **Cultural context**: Concepts like "Time, Position, Change" (时、位、变)
- **Historical background**: Western Zhou system, hexagram evolution logic

Chinese LLMs have higher Chinese training data ratio, providing better understanding for I Ching analysis.

### Recommended Models

| Model | Features | Price |
|-------|----------|-------|
| <img src="https://raw.githubusercontent.com/lobehub/lobe-icons/main/static/deepseek.svg" width="24" valign="middle"> **DeepSeek R1** | Best reasoning, lowest cost | $0.14/M tokens |
| <img src="https://raw.githubusercontent.com/lobehub/lobe-icons/main/static/qwen.svg" width="24" valign="middle"> **Qwen3-Max** | Best Chinese understanding, 1M context | $0.28/M tokens |
| <img src="https://raw.githubusercontent.com/lobehub/lobe-icons/main/static/zhipu.svg" width="24" valign="middle"> **GLM-5.1** | New user bonus: 20M free tokens | $0.70/M tokens |

### Configuration Examples

**Option 1: DeepSeek R1 (Recommended)**
```json
{
  "providers": {
    "openrouter": {
      "api_key": "your-key",
      "base_url": "https://openrouter.ai/api/v1"
    }
  },
  "agents": {
    "qigua_agent": { "provider": "openrouter", "model": "deepseek/deepseek-r1" },
    "scene_router": { "provider": "openrouter", "model": "deepseek/deepseek-r1" },
    "yao_agent": { "provider": "openrouter", "model": "deepseek/deepseek-r1" },
    "reporter": { "provider": "openrouter", "model": "deepseek/deepseek-r1" }
  }
}
```

**Get API Keys:**
- DeepSeek: https://platform.deepseek.com or https://openrouter.ai
- Qwen: https://dashscope.aliyun.com
- GLM: https://open.bigmodel.cn

---

<details>
<summary>📖 Manual Installation</summary>

### CLI Version (Zero Dependencies)
```bash
git clone https://github.com/RobbyShao-8ag/yice.git
cd yice
cp models.example.json models.json
# Edit models.json to add API key
python main.py
```

### Web Version
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