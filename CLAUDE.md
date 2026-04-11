# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

This project has **MVP implementation complete**. Core agents, pipeline, and web interface are functional.

## Project Overview

**易策 (yice)** — Open-source AI multi-agent decision system grounded in I Ching (周易) philosophy. Users pose life/work decisions; the system runs them through a structured multi-agent pipeline and returns a decision reference report.

Authors: 阿木 (Amu) + 邵琦 (Shaoqi). Documentation language: Chinese.

## Architecture

Five-stage pipeline:

```
User Question → 起卦官 (Qigua Agent) → 场景路由器 (Scene Router)
  → 六爻Agents (6 parallel Yao Agents) → 变卦引擎 (Bian Gua Engine)
  → 决策报告官 (Reporter Agent) → Decision Report
```

**Agents:**
- **起卦官**: Multi-turn dialogue to clarify problem; outputs structured JSON `{问题类型, 背景摘要, 关键约束, 期望结果, 时间维度, 风险承受}`
- **场景路由器**: Matches structured problem to one of 64 hexagrams; outputs `{本卦, 匹配理由, 变卦触发条件}`
- **六爻Agents** (run in parallel): 初爻(环境感知), 二爻(资源配置), 三爻(风险评估), 四爻(策略执行), 五爻(长期规划), 上爻(结果复盘)
- **变卦引擎**: Monitors conditions, triggers hexagram transitions, predicts evolution
- **决策报告官**: Aggregates all results into final report

## Technical Stack

**Backend (MVP target):**
- Python, native/minimal dependencies — zero complex framework imports
- LLM: direct API calls to providers (Moonshot, DeepSeek, Ollama, etc.)
- Data: JSON files for hexagram database and case history
- Entry point: CLI script (no web UI in MVP)

**LLM config format** (`models.json`, modeled after OpenClaw):
```json
{
  "providers": {
    "moonshot": { "baseUrl": "...", "apiKey": "...", "models": ["kimi-k2.5"] },
    "deepseek": { ... },
    "ollama": { ... }
  }
}
```
Each agent independently selects its model/provider.

**Frontend (post-MVP):**
- Next.js 14 or Vue 3, Framer Motion, Zustand, Tailwind CSS, deployed on Vercel
- Design: East Asian ink-wash aesthetic, 70%+ whitespace, dark theme (#0D0D0D background, #C41E3A accent, #D4AF37 gold)
- Fonts: Noto Serif SC (headings), Noto Sans SC (body)

## Key Data Structures

**Hexagram record** (`data/hexagrams.json`):
```json
{
  "卦名": "乾", "卦符号": "☰☰", "卦辞": "元亨利贞",
  "卦义": "刚健进取", "分类": "行动卦",
  "适用场景": ["创业启动", "争取机会"],
  "忌讳场景": ["防守收缩"]
}
```

**Yao position record**:
```json
{
  "卦名": "乾",
  "爻位": [{ "位置": "初九", "爻辞": "潜龙勿用", "时机": "积累期", "建议": "..." }]
}
```

**Bian Gua (changing hexagram) record**:
```json
{ "本卦": "屯卦", "变卦": "随卦", "触发条件": "第四爻动", "演变解读": "..." }
```

## Development Milestones

| Milestone | Scope |
|-----------|-------|
| M1 | CLI: Qigua multi-turn dialogue + simplified hexagram matching + basic report |
| M2 | All 6 Yao Agents with parallel execution + result aggregation |
| M3 | Bian Gua engine: trigger conditions, evolution prediction |
| M4 | Full 64-hexagram database, all yao interpretations, bian gua graph |
| M5 | Open-source release: docs, install scripts, example cases |

## Design Principles

- **Simplicity first**: minimal dependencies, users run `python main.py` after configuring API keys
- Each agent must be independently configurable (model, persona, dialogue-turn limit)
- All outputs are decision *references*, not authoritative answers — frame accordingly to avoid superstition framing
