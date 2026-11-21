"""Bus de eventos (patrón Observador).

Los eventos de interacción (decisión, consulta al tutor, SUS) son el sujeto
observable. Los observadores (telemetría y métricas) se suscriben y reaccionan.
Un observador que falle no interrumpe la simulación ni a los demás (D9).
"""
from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Callable, Dict, List

log = logging.getLogger("cervix_sim.events")


class EventBus:
    def __init__(self) -> None:
        self._subs: Dict[str, List[Callable[[dict], None]]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event: str, handler: Callable[[dict], None]) -> None:
        with self._lock:
            self._subs[event].append(handler)

    def publish(self, event: str, payload: dict) -> None:
        with self._lock:
            handlers = list(self._subs.get(event, ()))
        for handler in handlers:
            try:
                handler(payload)
            except Exception:  # noqa: BLE001 - la telemetría nunca debe romper el flujo
                log.exception("Observador falló en el evento %s", event)
