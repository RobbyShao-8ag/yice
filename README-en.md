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

### 1. Clone & Install

```bash
git clone https://github.com/RobbyShao-8ag/yice.git
cd yice
./setup.sh
```

### 2. Configure API Key

Edit `models.json` with your LLM provider API key:

- **OpenAI**: https://platform.openai.com/api-keys
- **DeepSeek**: https://platform.deepseek.com (cost-effective)
- **MiniMax**: https://www.minimaxi.com

### 3. Run

```bash
# CLI mode
python main.py

# Web interface
python web/main.py
```

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