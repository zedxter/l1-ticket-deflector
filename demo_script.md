# Demo call script (10–12 minutes)

Goal: show a working agent and the ROI in 10 minutes, without diving into tech.
Audience: Head of IT / IT Support Manager (200–2000 employees, DACH).

## 1. Hook (30 sec)
> "How many L1 tickets does your team handle per month? And how many of those are
> passwords, VPN, access, printers? Usually 50–70%. Let me show you how to take a
> third of them off the queue automatically — in a 6-week pilot."

## 2. The problem in numbers (1 min)
- 1,200 tickets/month × 19 min = ~380 h/month of routine.
- That's ~2.4 FTE spent on repetitive work.

## 3. Live demo (4 min)
Run `python3 demo/deflector.py` (or show `demo/report.md`):
- show how the agent **sorts 45 real tickets**;
- highlight the three buckets: AUTO / HUMAN / QUEUE;
- show that **phishing and access grants are NOT auto-resolved** —
  this removes the fear of "AI doing something dumb".

> "See: where a human is needed, the agent doesn't guess — it escalates with
> context. That's human-in-the-loop."

## 4. ROI (2 min)
- Deflection 30% (conservative) → ~114 h/month → **~€5,130/month**.
- Retainer €4,000/month → **ROI ×1.3/month, ×15/year**.
- Plus: employees get an answer in seconds, not hours.

## 5. Architecture (1 min, optional)
Show `graph/agent.py`: LangGraph, RAG over the KB, tool-calls into ITSM, escalation.
> "It sits on top of your Jira/Freshservice, works in Slack/Teams. All EU, GDPR."

## 6. Close (1 min)
> "I propose a 6-week pilot in one department. Discovery is 2–5k, then we go by
> the numbers. When's a good time to start?"

## Objections

| Objection | Answer |
|---|---|
| "We already have Zendesk AI" | "Great. We complement it — we work with your KB and your systems, EU hosting, human review. Compare deflection on your data in 2 weeks." |
| "AI will make mistakes" | "That's why sensitive cases go to a human. Auto-resolution is only for low-sensitivity categories, with logs and rollback." |
| "Too expensive" | "A 4k retainer against 5.1k/month in savings — positive ROI from month one. The pilot can be limited to one department." |
| "Data" | "On-prem/GDPR. Data never leaves your perimeter. I can show you the diagram." |

## Keep ready
- `demo/report.md` — open it in advance.
- `offer_one_pager_DE.md` — send after the call.
- GitHub repo of the demo — as proof of work.
