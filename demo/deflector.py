#!/usr/bin/env python3
"""
L1 Ticket Deflector — offline demo (no external dependencies).

Demonstrates the core mechanics:
  1) ticket classification against a knowledge base (stemming + phrases),
  2) the "auto-resolve" vs "escalate to a human (human review)" decision,
  3) deflection rate and an honest ROI model.

Runs on any machine with Python 3. Production version: LangGraph + LLM (see ../graph/).
"""
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
KB_PATH = os.path.join(ROOT, "kb", "knowledge_base.json")
TICKETS_PATH = os.path.join(BASE, "tickets.json")
REPORT_PATH = os.path.join(BASE, "report.md")

HUMAN_REVIEW_SENSITIVITY = {"high", "critical"}
MATCH_THRESHOLD = 1.0

# ---- Honest ROI model (conservative DACH market assumptions) ----
MODEL = {
    "company_employees": 500,
    "monthly_l1_tickets": 1200,   # benchmark for ~500 employees
    "deflection_rate": 0.30,      # conservative 30% (market: 20-40%)
    "avg_handle_min": 19,         # average manual L1 handling time
    "hourly_rate_eur": 45,        # fully-loaded cost of an IT specialist
    "retainer_eur": 4000,
}

EN_SUFFIXES = ["ing", "tion", "ment", "ed", "es", "s"]


def stem(w):
    w = w.lower()
    for suf in EN_SUFFIXES:
        if len(w) - len(suf) >= 4 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def tokens(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return [stem(t) for t in text.split() if t]


def kw_strength(kw_tokens):
    """Base strength of a single keyword by its length/specificity."""
    length = sum(len(t) for t in kw_tokens)
    s = 1.0
    if length >= 6:
        s += 1.0
    if length >= 9:
        s += 1.0
    return s


def match_article(text_tokens, article):
    text_set = set(text_tokens)
    best = 0.0
    matched = 0
    for kw in article["keywords"]:
        kt = tokens(kw)
        if not kt:
            continue
        present = all(t in text_set for t in kt)
        if not present:
            continue
        matched += 1
        strength = kw_strength(kt)
        if len(kt) > 1:
            strength += 0.5 * len(kt)  # phrase bonus
        best = max(best, strength)
    if matched == 0:
        return 0.0
    return best + 0.4 * (matched - 1)


def classify(text, kb):
    tt = tokens(text)
    best, best_score = None, 0.0
    for art in kb["articles"]:
        s = match_article(tt, art)
        if s > best_score:
            best, best_score = art, s
    if best is None or best_score < MATCH_THRESHOLD:
        return None, best_score
    return best, best_score


def process(kb, tickets):
    results = []
    for t in tickets:
        art, score = classify(t["text"], kb)
        if art is None:
            results.append({
                "id": t["id"], "text": t["text"], "decision": "escalate_unmatched",
                "article": None, "score": score, "minutes_saved": 0,
                "expect": t.get("expect"),
            })
            continue
        needs_human = art["sensitivity"] in HUMAN_REVIEW_SENSITIVITY
        results.append({
            "id": t["id"], "text": t["text"],
            "decision": "escalate_human" if needs_human else "auto_resolve",
            "article": art["id"], "title": art["title"], "score": score,
            "sensitivity": art["sensitivity"],
            "minutes_saved": 0 if needs_human else art["est_minutes_saved"],
            "expect": t.get("expect"),
        })
    return results


def accuracy(results):
    art_ok = dec_ok = n = 0
    for r in results:
        exp = r.get("expect")
        if exp is None:
            continue
        n += 1
        if exp == "escalate":
            dec_ok += 1 if r["decision"] == "escalate_unmatched" else 0
        else:
            # correct decision: ticket matched (auto or human), not sent to the queue
            dec_ok += 1 if r["article"] is not None else 0
            art_ok += 1 if r["article"] == exp else 0
    return art_ok, dec_ok, n


def decision_correct(r):
    exp = r.get("expect")
    if exp is None:
        return None
    if exp == "escalate":
        return r["decision"] == "escalate_unmatched"
    # correct decision = not sent to the general queue, but matched (auto or human)
    return r["article"] is not None


def build_report(results):
    total = len(results)
    auto = sum(1 for r in results if r["decision"] == "auto_resolve")
    esc_human = sum(1 for r in results if r["decision"] == "escalate_human")
    esc_unmatched = sum(1 for r in results if r["decision"] == "escalate_unmatched")
    minutes = sum(r["minutes_saved"] for r in results)
    sample_deflection = auto / total * 100 if total else 0

    dec = [decision_correct(r) for r in results]
    dec = [d for d in dec if d is not None]
    dec_acc = sum(dec) / len(dec) * 100 if dec else 0
    art_ok = sum(1 for r in results if r.get("expect") not in (None, "escalate")
                 and r["article"] == r["expect"])
    art_n = sum(1 for r in results if r.get("expect") not in (None, "escalate"))
    routing_acc = art_ok / art_n * 100 if art_n else 0

    # --- Honest ROI model ---
    m = MODEL
    auto_m = m["monthly_l1_tickets"] * m["deflection_rate"]
    min_saved = auto_m * m["avg_handle_min"]
    hours_saved = min_saved / 60
    savings_eur = hours_saved * m["hourly_rate_eur"]
    roi = savings_eur / m["retainer_eur"]
    fte = hours_saved / 160  # ~160 working hours per month

    L = []
    a = L.append
    a("=" * 70)
    a("  L1 TICKET DEFLECTOR - DEMO RUN REPORT")
    a("=" * 70)
    a("")
    a("  RESULTS ON THE DEMO DATASET")
    a("  " + "-" * 66)
    a(f"  Tickets processed         : {total}")
    a(f"    [AUTO] Resolved          : {auto}")
    a(f"    [HUMAN] Escalated        : {esc_human}  (high/critical sensitivity)")
    a(f"    [QUEUE] No match         : {esc_unmatched}  (general L1 queue)")
    a("")
    a(f"  Deflection rate (sample)  : {sample_deflection:.1f}%")
    a(f"  Decision accuracy         : {dec_acc:.1f}%  (auto/escalate/queue correct)")
    a(f"  Routing accuracy          : {routing_acc:.1f}%  (correct KB article)")
    a("")
    a("  " + "-" * 66)
    a("  HONEST ROI MODEL (conservative DACH assumptions)")
    a("  " + "-" * 66)
    a(f"  Company                   : ~{m['company_employees']} employees")
    a(f"  L1 tickets per month      : ~{m['monthly_l1_tickets']}")
    a(f"  Deflection (conservative) : {m['deflection_rate']*100:.0f}%  (market: 20-40%)")
    a(f"  Avg manual handling time  : {m['avg_handle_min']} min")
    a(f"  IT specialist rate        : {m['hourly_rate_eur']} EUR/hour (fully loaded)")
    a("")
    a(f"  Auto-resolutions / month  : ~{auto_m:.0f}")
    a(f"  Time saved                : ~{hours_saved:.0f} h/month  (~{fte:.1f} FTE)")
    a(f"  Client savings            : ~{savings_eur:,.0f} EUR/month")
    a(f"  Retainer                  : {m['retainer_eur']:,} EUR/month")
    a(f"  ROI                       : x{roi:.1f} per month (x{roi*12:.0f} per year)")
    a("")
    a("  " + "-" * 66)
    a("  PER-TICKET BREAKDOWN")
    a("  " + "-" * 66)
    for r in results:
        tag = {"auto_resolve": "AUTO ", "escalate_human": "HUMAN",
               "escalate_unmatched": "QUEUE"}[r["decision"]]
        ok = "" if decision_correct(r) in (True, None) else "  <- attention"
        a(f"  [{tag}] {r['id']} -> {r['article'] or '-':<6} | {r['text'][:52]}{ok}")
    a("")
    a("=" * 70)
    a("  Demo: keywords + stemming (no LLM). Production version - LangGraph:")
    a("  RAG over the KB, tool-calls into ITSM, human-in-the-loop, telemetry.")
    a("=" * 70)

    return "\n".join(L), {
        "total": total, "auto": auto, "esc_human": esc_human,
        "esc_unmatched": esc_unmatched, "sample_deflection": sample_deflection,
        "dec_acc": dec_acc, "routing_acc": routing_acc,
        "savings_eur": savings_eur, "roi": roi,
    }


def main():
    kb = json.load(open(KB_PATH, encoding="utf-8"))
    data = json.load(open(TICKETS_PATH, encoding="utf-8"))
    results = process(kb, data["tickets"])
    report, stats = build_report(results)
    print(report)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# L1 Ticket Deflector - demo run report\n\n```\n")
        f.write(report)
        f.write("\n```\n")
    print(f"\nReport saved: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
