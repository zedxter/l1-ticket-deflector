#!/usr/bin/env python3
"""
L1 Ticket Deflector — офлайн-демо (без внешних зависимостей).

Демонстрирует ключевую механику:
  1) классификация тикета по базе знаний (стемминг + фразы),
  2) решение "решить автоматически" / "эскалировать на человека (human review)",
  3) deflection rate и честная ROI-модель.

Запускается на любой машине с Python 3. Боевая версия: LangGraph + LLM (см. ../graph/).
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

# ---- Честная модель ROI (консервативные допущения рынка DACH) ----
MODEL = {
    "company_employees": 500,
    "monthly_l1_tickets": 1200,   # бенчмарк для ~500 сотрудников
    "deflection_rate": 0.30,      # консервативно 30% (рынок: 20–40%)
    "avg_handle_min": 19,         # среднее время ручной обработки L1
    "hourly_rate_eur": 45,        # fully-loaded стоимость IT-специалиста
    "retainer_eur": 4000,
}

RU_SUFFIXES = [
    "ирования", "рования", "ования", "ается", "яется", "иться", "аться",
    "ется", "ться", "циями", "овать", "ировать", "ация", "ации", "цией",
    "ость", "ости", "ное", "ные", "ным", "ами", "ями", "ах", "ях",
    "ов", "ев", "ий", "ый", "ой", "ая", "ое", "ые", "ам", "ям",
    "у", "ю", "а", "я", "ы", "и", "е", "о", "ь",
]
EN_SUFFIXES = ["ing", "tion", "ment", "ed", "es", "s"]


def stem(w):
    w = w.lower()
    for suf in RU_SUFFIXES:
        if len(w) - len(suf) >= 4 and w.endswith(suf):
            return w[: -len(suf)]
    for suf in EN_SUFFIXES:
        if len(w) - len(suf) >= 4 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def tokens(text):
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return [stem(t) for t in text.split() if t]


def kw_strength(kw_tokens):
    """Базовая сила одного ключа по его длине/специфичности."""
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
            strength += 0.5 * len(kt)  # бонус за фразу
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
            # верное решение: тикет найден (auto или human), а не ушёл в очередь
            dec_ok += 1 if r["article"] is not None else 0
            art_ok += 1 if r["article"] == exp else 0
    return art_ok, dec_ok, n


def decision_correct(r):
    exp = r.get("expect")
    if exp is None:
        return None
    if exp == "escalate":
        return r["decision"] == "escalate_unmatched"
    # верное решение = не ушло в общую очередь, а найдено (auto или human)
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

    # --- Честная ROI-модель ---
    m = MODEL
    auto_m = m["monthly_l1_tickets"] * m["deflection_rate"]
    min_saved = auto_m * m["avg_handle_min"]
    hours_saved = min_saved / 60
    savings_eur = hours_saved * m["hourly_rate_eur"]
    roi = savings_eur / m["retainer_eur"]
    fte = hours_saved / 160  # ~160 рабочих часов в месяц

    L = []
    a = L.append
    a("=" * 70)
    a("  L1 TICKET DEFLECTOR — ОТЧЁТ ДЕМО-ПРОГОНА")
    a("=" * 70)
    a("")
    a("  РЕЗУЛЬТАТЫ НА ДЕМО-ВЫБОРКЕ")
    a("  " + "-" * 66)
    a(f"  Всего тикетов обработано  : {total}")
    a(f"    ✅ Авто-решено           : {auto}")
    a(f"    🧑 Эскалировано человеку : {esc_human}  (high/critical sensitivity)")
    a(f"    ❓ Без совпадения        : {esc_unmatched}  (в общую очередь)")
    a("")
    a(f"  Deflection rate (выборка) : {sample_deflection:.1f}%")
    a(f"  Точность решения          : {dec_acc:.1f}%  (auto/escalate/queue — верно)")
    a(f"  Точность маршрутизации    : {routing_acc:.1f}%  (попадание в нужную статью KB)")
    a("")
    a("  " + "-" * 66)
    a("  ЧЕСТНАЯ ROI-МОДЕЛЬ (консервативные допущения DACH)")
    a("  " + "-" * 66)
    a(f"  Компания                  : ~{m['company_employees']} сотрудников")
    a(f"  L1-тикетов в месяц        : ~{m['monthly_l1_tickets']}")
    a(f"  Deflection (консервативно) : {m['deflection_rate']*100:.0f}%  (рынок: 20–40%)")
    a(f"  Ср. время ручной обработки : {m['avg_handle_min']} мин")
    a(f"  Ставка IT-специалиста     : {m['hourly_rate_eur']} €/час (fully loaded)")
    a("")
    a(f"  Авто-резолюций в месяц    : ~{auto_m:.0f}")
    a(f"  Сэкономлено времени       : ~{hours_saved:.0f} ч/мес  (~{fte:.1f} FTE)")
    a(f"  💰 Экономия клиента       : ~{savings_eur:,.0f} €/мес")
    a(f"  Стоимость ретейнера       : {m['retainer_eur']:,} €/мес")
    a(f"  📈 ROI                     : ×{roi:.1f} в месяц (×{roi*12:.0f} в год)")
    a("")
    a("  " + "-" * 66)
    a("  РАЗБОР ПО ТИКЕТАМ")
    a("  " + "-" * 66)
    for r in results:
        tag = {"auto_resolve": "AUTO ✅", "escalate_human": "HUMAN🧑",
               "escalate_unmatched": "QUEUE❓"}[r["decision"]]
        ok = "" if decision_correct(r) in (True, None) else "  ← внимание"
        a(f"  [{tag}] {r['id']} → {r['article'] or '—':<6} | {r['text'][:52]}{ok}")
    a("")
    a("=" * 70)
    a("  Демо: ключевые слова + стемминг (без LLM). Боевая версия — LangGraph:")
    a("  RAG по базе знаний, tool-calls в ITSM, human-in-the-loop, телеметрия.")
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
        f.write("# L1 Ticket Deflector — отчёт демо-прогона\n\n```\n")
        f.write(report)
        f.write("\n```\n")
    print(f"\nОтчёт сохранён: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
