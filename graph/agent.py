"""
L1 Ticket Deflector — граф на LangGraph.

Поток:
   classify ──> (нет совпадения) ──────────────> queue
      │
      ├──(low sensitivity)──> auto_resolve ──> notify_user
      │
      └──(high/critical)───> human_review ──> escalate ──> notify_user

Ключевая идея: агент НЕ галлюцинирует на чувствительных запросах —
всё, что касается доступов, привилегий, ИБ или бюджета, уходит человеку
(human-in-the-loop) с подготовленным контекстом.

Запуск (демо без ключа):   MOCK_MODE=1 python graph/run_demo.py
Боевой запуск:             OPENAI_API_KEY=... python graph/run_demo.py
"""
from __future__ import annotations

import json
import operator
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, StateGraph

from config import (AUTO_RESOLVE_SENSITIVITY, CONFIDENCE_THRESHOLD,
                    ESCALATION, MOCK_MODE, MODEL)

# --------------------------------------------------------------------------
# Состояние графа
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
    target: str | None            # кому эскалируем
    actions: Annotated[list, operator.add]  # журнал шагов
    user_reply: str | None
    est_minutes_saved: int


# --------------------------------------------------------------------------
# Инструменты (в боевой версии — реальные tool-calls в ITSM / AD / MDM)
# --------------------------------------------------------------------------
def itsm_create_ticket(kind: str, summary: str, **fields) -> str:
    """Создаёт заявку в ITSM (Jira SM / Freshservice / Zammad...)."""
    return f"[ITSM] создана заявка '{kind}': {summary} {fields or ''}"


def directory_reset_password(user: str) -> str:
    """Сброс пароля в каталоге (AD/Entra ID self-service)."""
    return f"[AD] self-service reset link отправлен пользователю {user}"


def mdm_push_install(app: str) -> str:
    return f"[MDM] push-установка '{app}' через Company Portal"


def notify(user: str, message: str, channel: str = "slack") -> str:
    return f"[{channel.upper()}] → {user}: {message}"


def escalate_to(team: str, context: str) -> str:
    return f"[ESCALATE → {team}] {context}"


# --------------------------------------------------------------------------
# LLM-классификатор (в MOCK_MODE — детерминированная заглушка)
# --------------------------------------------------------------------------
def _load_kb():
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(os.path.dirname(here), "kb", "knowledge_base.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def llm_classify(text: str) -> dict:
    """
    Возвращает: {article_id, title, resolution, sensitivity, confidence}

    В боевой версии здесь вызов LLM с RAG по базе знаний:
        - structured output (Pydantic) для article_id + confidence
        - top-k retrieval статей KB, LLM выбирает и оценивает уверенность
    В MOCK_MODE используем keyword-fallback из demo/deflector.py.
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
        # грубая нормализация score → confidence (в проде — logit LLM)
        conf = min(0.95, 0.5 + score / 10)
        return {"article_id": art["id"], "title": art["title"],
                "resolution": art["resolution"], "sensitivity": art["sensitivity"],
                "confidence": round(conf, 2), "est_minutes_saved": art["est_minutes_saved"]}

    # ---- Боевой путь ----
    from langchain_openai import ChatOpenAI
    from pydantic import BaseModel, Field

    class Routing(BaseModel):
        article_id: str = Field(description="ID статьи KB или 'none'")
        confidence: float = Field(ge=0, le=1)
        reasoning: str = ""

    kb = _load_kb()
    catalog = "\n".join(f"{a['id']} | {a['category']} | {a['title']}" for a in kb["articles"])
    prompt = (
        "Ты — L1 IT-агент. Подбери наиболее подходящую статью базы знаний для тикета.\n"
        f"Тикеты: {catalog}\n\nТикет: {text!r}\n"
        "Верни article_id (или 'none'), confidence и краткое reasoning."
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
# Узлы графа
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
            f"classify: {res.get('article_id') or 'нет совпадения'} "
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
        f"auto_resolve: применяю статью {state['article_id']}",
        itsm_create_ticket("auto", state["article_title"], article=state["article_id"]),
    ]
    # примеры реальных действий по категории (в проде — через MCP-инструменты)
    title = (state.get("article_title") or "").lower()
    if "парол" in title:
        actions.append(directory_reset_password(state["ticket_id"]))
    if "установка" in title or "по из каталог" in title:
        actions.append(mdm_push_install("requested-app"))
    return {"decision": "auto_resolve", "actions": actions}


def node_human_review(state: TicketState) -> TicketState:
    target = ESCALATION.get(state.get("sensitivity", "high"), "service_desk_l2")
    actions = [
        f"human_review: чувствительность={state.get('sensitivity')} → не решаю сам",
        escalate_to(target, f"тикет {state['ticket_id']} требует человека "
                            f"(статья {state['article_id']})"),
    ]
    return {"decision": "human_review", "target": target, "actions": actions,
            "user_reply": "Передано специалисту, срок реакции — 30 минут."}


def node_queue(state: TicketState) -> TicketState:
    return {"decision": "queue",
            "actions": ["queue: нет уверенного совпадения → общая очередь L1"],
            "user_reply": "Ваш запрос передан в службу поддержки."}


def node_notify_user(state: TicketState) -> TicketState:
    if state["decision"] == "auto_resolve":
        msg = f"Решено автоматически: {state.get('article_resolution')}"
        return {"user_reply": msg,
                "actions": [notify(state["ticket_id"], msg, "teams")]}
    return {"actions": [notify(state["ticket_id"], state.get("user_reply", ""), "teams")]}


# --------------------------------------------------------------------------
# Сборка графа
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
