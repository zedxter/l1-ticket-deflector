# L1 Ticket Deflector 🎫🤖

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-agent-orange.svg)](https://github.com/langchain-ai/langgraph)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An AI agent that takes load off an IT service desk's **L1 queue**: it resolves
routine tickets automatically and hands sensitive cases (access, privileges,
security, budget) to a human **with full context** — human-in-the-loop by design.

> **Proof of work** — a working, runnable demo of an L1 deflection agent for
> mid-market IT helpdesks (DACH / EU). Runs on top of your existing ITSM.

---

## Why this exists

- **50–70%** of L1 tickets are routine: password, VPN, software, printer.
- Each ticket costs an IT pro **15–30 minutes**.
- AI service desk market: **$4.8B (2025) → $27.8B (2034)**, CAGR 21.3%.
- Realistic first-year deflection: **20–40%** of L1 volume.

## What's inside

| Path | What it is |
|---|---|
| `kb/` | Knowledge base: 20 articles (10 auto-resolve, 10 human-review) |
| `demo/` | **Offline demo**, zero dependencies: classifier + ROI report |
| `graph/` | **Production version** on LangGraph: RAG + tool-calls + human-in-the-loop |
| `offer_one_pager_DE.md` | Sales one-pager (German) |
| `demo_script.md` | Demo call script + objection handling |

## Quick start

```bash
# 1. Offline demo — runs anywhere with Python 3
python3 demo/deflector.py            # → demo/report.md

# 2. Production graph (laptop/server, Python 3.10+)
cd graph
pip install -r requirements.txt
MOCK_MODE=1 python run_demo.py       # no API key needed — logic check
OPENAI_API_KEY=sk-... python run_demo.py   # real LLM
```

## Decision logic

```
classify ──> no match / low confidence ──> queue (general L1 queue)
   │
   ├── sensitivity = low        ──> auto_resolve ──> notify_user
   └── sensitivity = high/crit  ──> human_review ──> escalate ──> notify_user
```

**Principle:** the agent never guesses on sensitive requests. Anything touching
access, privileges, security, or money goes to a human with prepared context.

## Demo results (offline, no LLM)

45 labeled tickets:

| Metric | Value |
|---|---|
| Auto-resolved | 25 |
| Escalated to human | 18 |
| No match → queue | 2 |
| **Decision accuracy** | **100%** |
| **Routing accuracy** | **100%** |
| Sample deflection | 55.6% |

## Client ROI model (~500 employees, conservative)

| Metric | Value |
|---|---|
| L1 tickets / month | ~1,200 |
| Deflection (conservative) | 30% |
| Time saved | ~114 h/month (~0.7 FTE) |
| **Savings** | **~€5,130 / month** |
| Retainer | €4,000 / month |
| **ROI** | **×1.3/month (×15/year)** |

## Roadmap

- [ ] Real tool-calls: Jira SM, Zammad, GLPI, ServiceNow (via MCP)
- [ ] RAG over the client's real KB (embeddings + rerank)
- [ ] Human-in-the-loop UI (Slack/Teams approve buttons)
- [ ] Telemetry: deflection rate, CSAT, time-to-resolution
- [ ] Multilingual DE/EN

## License

MIT — see [LICENSE](LICENSE).
