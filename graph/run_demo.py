#!/usr/bin/env python3
"""
Запуск боевого графа на демо-тикетах.
MOCK_MODE=1 — без API-ключа (проверка логики).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent import handle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TICKETS = os.path.join(os.path.dirname(HERE), "demo", "tickets.json")


def main():
    data = json.load(open(TICKETS, encoding="utf-8"))
    tickets = data["tickets"][:12]  # короткий прогон для наглядности
    auto = human = queue = 0
    for t in tickets:
        out = handle(t["id"], t["text"])
        d = out.get("decision")
        auto += d == "auto_resolve"
        human += d == "human_review"
        queue += d == "queue"
        print(f"\n=== {t['id']} | {t['text'][:60]}")
        print(f"    decision : {d}")
        print(f"    target   : {out.get('target')}")
        print(f"    reply    : {out.get('user_reply')}")
        for a in out.get("actions", []):
            print(f"      · {a}")
    print(f"\nИтого: auto={auto}, human={human}, queue={queue} из {len(tickets)}")


if __name__ == "__main__":
    main()
