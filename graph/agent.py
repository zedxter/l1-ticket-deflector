"""
L1 Ticket Deflector — LangGraph agent.

Flow:
   classify ──> (no match) ─────────────────────> queue
      │
      ├──(low sensitivity)──> auto_resolve ──> notify_user
      │
      └──(high/critical)───> human_review ──> escalate ──> notify_user

Key idea: the agent does NOT hallucinate on sensitive requests —
anything touching access, privileges, security or budget goes to a human
(human-in-the-loop) with prepared context.

Run (demo, no key):   MOCK_MODE=1 python graph/run_demo.py
Production run:       OPENAI_API_KEY=... python graph/run_demo.py
"""
from __future__ import annotations

import json
import operator
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, StateGraph

from config import (AUTO_RESOLVE_SENSITIVITY, CONFIDENCE_THRESHOLD,
                    ESCALATION, MOCK_MODE, MODEL)

# --------------------------------------------------------------------------
# Graph state
# --------------------------------------------------------------------------
class TicketState(TypedDict, total=False):
    ticket_id: str
    text: str
    article_id: str | None
    article_title: str | None
    article_resolution: str | None
    sensitivity: str | None
    confidence: float
    decision: str | None          # auto_resolve | human_review | queue
    target: str | None            # who we escalate to
    actions: Annotated[list, operator.add]  # step log
    user_reply: str | None
    est_minutes_saved: int


# --------------------------------------------------------------------------
# Tools (in production: real tool-calls into ITSM / AD / MDM)
# --------------------------------------------------------------------------
def itsm_create_ticket(kind: str, summary: str, **fields) -> str:
    """Creates a request in the ITSM (Jira SM / Freshservice / Zammad...)."""
    return f"[ITSM] created '{kind}' request: {summary} {fields or ''}"


def directory_reset_password(user: str) -> str:
    """Password reset in the directory (AD/Entra ID self-service)."""
    return f"[AD] self-service reset link sent to user {user}"


def mdm_push_install(app: str) -> str:
    return f"[MDM] push-install of '{app}' via Company Portal"


def notify(user: str, message: str, channel: str = "slack") -> str:
    return f"[{channel.upper()}] -> {user}: {message}"


def escalate_to(team: str, context: str) -> str:
    return f"[ESCALATE -> {team}] {context}"


# --------------------------------------------------------------------------
# LLM classifier (in MOCK_MODE: deterministic stub)
# --------------------------------------------------------------------------
def _load_kb():
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(os.path.dirname(here), "kb", "knowledge_base.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def llm_classify(text: str) -> dict:
    """
    Returns: {article_id, title, resolution, sensitivity, confidence}

    In production this is an LLM call with RAG over the knowledge base:
        - structured output (Pydantic) for article_id + confidence
        - top-k retrieval of KB articles, LLM selects and scores confidence
    In MOCK_MODE we use the keyword fallback from demo/deflector.py.
    """
    if MOCK_MODE:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "demo"))
        from deflector import classify as kw_classify  # type: ignore
        kb = _load_kb()
        art, score = kw_classify(text, kb)
        if art is None:
            return {"article_id": None, "title": None, "resolution": None,
                    "sensitivity": None, "confidence": 0.0}
        # rough score -> confidence normalization (in prod: LLM logit)
        conf = min(0.95, 0.5 + score / 10)
        return {"article_id": art["id"], "title": art["title"],
                "resolution": art["resolution"], "sensitivity": art["sensitivity"],
                "confidence": round(conf, 2), "est_minutes_saved": art["est_minutes_saved"]}

    # ---- Production path ----
    from langchain_openai import ChatOpenAI
    from pydantic import BaseModel, Field

    class Routing(BaseModel):
        article_id: str = Field(description="KB article ID or 'none'")
        confidence: float = Field(ge=0, le=1)
        reasoning: str = ""

    kb = _load_kb()
    catalog = "\n".join(f"{a['id']} | {a['category']} | {a['title']}" for a in kb["articles"])
    prompt = (
        "You are an L1 IT agent. Pick the most relevant knowledge base article for the ticket.\n"
        f"Articles: {catalog}\n\nTicket: {text!r}\n"
        "Return article_id (or 'none'), confidence and a short reasoning."
    )
    llm = ChatOpenAI(model=MODEL, temperature=0).with_structured_output(Routing)
    out = llm.invoke(prompt)
    art = next((a for a in kb["articles"] if a["id"] == out.article_id), None)
    if art is None:
        return {"article_id": None, "title": None, "resolution": None,
                "sensitivity": None, "confidence": out.confidence}
    return {"article_id": art["id"], "title": art["title"],
            "resolution": art["resolution"], "sensitivity": art["sensitivity"],
            "confidence": out.confidence, "est_minutes_saved": art["est_minutes_saved"]}


# --------------------------------------------------------------------------
# Graph nodes
# --------------------------------------------------------------------------
def node_classify(state: TicketState) -> TicketState:
    res = llm_classify(state["text"])
    return {
        "article_id": res.get("article_id"),
        "article_title": res.get("title"),
        "article_resolution": res.get("resolution"),
        "sensitivity": res.get("sensitivity"),
        "confidence": res.get("confidence", 0.0),
        "est_minutes_saved": res.get("est_minutes_saved", 0),
        "actions": [
            f"classify: {res.get('article_id') or 'no match'} "
            f"(conf={res.get('confidence', 0.0):.2f})"
        ],
    }


def route_after_classify(state: TicketState) -> Literal["auto_resolve", "human_review", "queue"]:
    if not state.get("article_id") or state.get("confidence", 0) < CONFIDENCE_THRESHOLD:
        return "queue"
    if state.get("sensitivity") in AUTO_RESOLVE_SENSITIVITY:
        return "auto_resolve"
    return "human_review"


def node_auto_resolve(state: TicketState) -> TicketState:
    actions = [
        f"auto_resolve: applying article {state['article_id']}",
        itsm_create_ticket("auto", state["article_title"], article=state["article_id"]),
    ]
    # example real actions per category (in prod: via MCP tools)
    title = (state.get("article_title") or "").lower()
    if "password" in title:
        actions.append(directory_reset_password(state["ticket_id"]))
    if "install" in title or "software" in title:
        actions.append(mdm_push_install("requested-app"))
    return {"decision": "auto_resolve", "actions": actions}


def node_human_review(state: TicketState) -> TicketState:
    target = ESCALATION.get(state.get("sensitivity", "high"), "service_desk_l2")
    actions = [
        f"human_review: sensitivity={state.get('sensitivity')} -> not resolving myself",
        escalate_to(target, f"ticket {state['ticket_id']} needs a human "
                            f"(article {state['article_id']})"),
    ]
    return {"decision": "human_review", "target": target, "actions": actions,
            "user_reply": "Handed to a specialist, response time 30 minutes."}


def node_queue(state: TicketState) -> TicketState:
    return {"decision": "queue",
            "actions": ["queue: no confident match -> general L1 queue"],
            "user_reply": "Your request has been passed to the service desk."}


def node_notify_user(state: TicketState) -> TicketState:
    if state["decision"] == "auto_resolve":
        msg = f"Resolved automatically: {state.get('article_resolution')}"
        return {"user_reply": msg,
                "actions": [notify(state["ticket_id"], msg, "teams")]}
    return {"actions": [notify(state["ticket_id"], state.get("user_reply", ""), "teams")]}


# --------------------------------------------------------------------------
# Graph assembly
# --------------------------------------------------------------------------
def build_graph():
    g = StateGraph(TicketState)
    g.add_node("classify", node_classify)
    g.add_node("auto_resolve", node_auto_resolve)
    g.add_node("human_review", node_human_review)
    g.add_node("queue", node_queue)
    g.add_node("notify_user", node_notify_user)

    g.set_entry_point("classify")
    g.add_conditional_edges("classify", route_after_classify,
                            {"auto_resolve": "auto_resolve",
                             "human_review": "human_review",
                             "queue": "queue"})
    g.add_edge("auto_resolve", "notify_user")
    g.add_edge("human_review", "notify_user")
    g.add_edge("queue", "notify_user")
    g.add_edge("notify_user", END)
    return g.compile()


def handle(ticket_id: str, text: str) -> dict:
    app = build_graph()
    return app.invoke({"ticket_id": ticket_id, "text": text, "actions": []})


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        out = handle("CLI", " ".join(sys.argv[1:]))
        print(json.dumps(out, ensure_ascii=False, indent=2))
