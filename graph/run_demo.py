#!/usr/bin/env python3
"""
Runs the production graph over the demo tickets.
MOCK_MODE=1 — no API key (logic check).
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
    tickets = data["tickets"][:12]  # short run for readability
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
            print(f"      - {a}")
    print(f"\nTotal: auto={auto}, human={human}, queue={queue} of {len(tickets)}")


if __name__ == "__main__":
    main()
