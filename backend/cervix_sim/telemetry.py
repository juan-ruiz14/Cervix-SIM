"""Observadores de telemetría (UC-04, Req 003).

Se suscriben al bus de eventos y escriben en segundo plano: el registro de
métricas nunca bloquea la interacción del usuario.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .domain.events import EventBus
from .domain.metrics import classify, evaluate_decision
from .store import Store


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class MetricsObserver:
    """Calcula y guarda la métrica de cada decisión (entidad «Métricas de simulación»)."""

    def __init__(self, store: Store) -> None:
        self.store = store

    def on_decision(self, p: dict) -> None:
        ev = evaluate_decision(p["decision"], p["reference"], p.get("suggestion"))
        self.store.upsert("metricas", {
            "_id": p["decision_id"], "session_id": p["session_id"], "participant_id": p["participant_id"],
            "case_id": p["case_id"], "level": p["level"], "confidence": p["confidence"],
            "response_time_s": p["response_time_s"], "estado": classify(ev), **ev,
            "created_at": now_iso(),
        })


class EventLogObserver:
    """Registro de eventos de interacción para trazabilidad (sin datos personales)."""

    def __init__(self, store: Store) -> None:
        self.store = store

    def __call__(self, event: str):
        def handler(p: dict) -> None:
            self.store.insert("eventos", {"type": event, "session_id": p.get("session_id"),
                                          "participant_id": p.get("participant_id"), "created_at": now_iso()})
        return handler


def wire(bus: EventBus, store: Store) -> None:
    metrics, log = MetricsObserver(store), EventLogObserver(store)
    bus.subscribe("decision_registered", metrics.on_decision)
    for event in ("decision_registered", "tutor_requested", "sus_submitted", "session_started"):
        bus.subscribe(event, log(event))
