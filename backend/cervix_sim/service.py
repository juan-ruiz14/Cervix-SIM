"""Servicio de simulación: orquesta los casos de uso UC-01 a UC-05.

Reglas de oro de la arquitectura (decisiones D3 y D10):
- La referencia docente y la condición de la sugerencia (calibrada/inexacta) viven solo
  en el servidor y se revelan después de registrar la decisión.
- Los datos de identificación (nombre, correo) quedan en `usuarios`; todo lo demás usa
  un identificador seudónimo de participante.
"""
from __future__ import annotations

import hashlib
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from .config import Settings
from .domain.cases import OPTIONS
from .domain.events import EventBus
from .domain.factory import ScenarioFactory
from .domain.metrics import aggregate, classify, evaluate_decision
from .domain.sus import score_sus
from .errors import AppError
from .legal import LEGAL_NOTICE
from .store import Store
from .telemetry import now_iso
from .tutor import TutorClient


class SimulationService:
    def __init__(self, store: Store, bus: EventBus, tutor: TutorClient,
                 factory: ScenarioFactory, settings: Settings) -> None:
        self.store, self.bus, self.tutor = store, bus, tutor
        self.factory, self.settings = factory, settings
        self._lock = threading.Lock()
        # La telemetría corre en segundo plano para no frenar la interfaz (D4).
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="telemetria")

    def _emit(self, event: str, payload: dict) -> None:
        self._pool.submit(self.bus.publish, event, payload)

    def close(self) -> None:
        self._pool.shutdown(wait=True)

    # ---- helpers ---------------------------------------------------------
    def _session(self, session_id: str) -> dict:
        s = self.store.get("sesiones", session_id)
        if not s:
            raise AppError("SESSION_NOT_FOUND", "La sesión no existe o expiró.", 404)
        return s

    def _first_suggestion(self, session_id: str) -> Optional[dict]:
        found = self.store.find("sugerencias", {"session_id": session_id}, sort="created_at")
        return found[0] if found else None

    def _choose_suggestion(self, session_id: str, case) -> tuple[str, str]:
        """Política de sugerencia: determinista por sesión y caso (reproducible)."""
        h = int(hashlib.sha256(f"{session_id}:{case.id}".encode()).hexdigest(), 16)
        n = self.settings.inexact_every
        if n > 0 and h % n == 0:
            others = sorted(code for code in OPTIONS if code != case.reference)
            return others[(h // n) % len(others)], "inexacta"
        return case.reference, "calibrada"

    # ---- UC-01: seleccionar nivel y escenario -----------------------------
    def start_session(self, nombre: str, rol: str, correo: str, nivel: str, consentimiento: bool) -> dict:
        if not consentimiento:
            raise AppError("CONSENT_REQUIRED", "Debes aceptar el tratamiento de datos para continuar.", 422)
        scenario = self.factory.create(nivel)
        participant_id = "P-" + uuid.uuid4().hex[:8]
        now = now_iso()
        self.store.insert("usuarios", {"_id": participant_id, "nombre": nombre, "correo": correo,
                                       "rol": rol, "consentimiento": True, "created_at": now})
        session_id = uuid.uuid4().hex
        self.store.insert("sesiones", {
            "_id": session_id, "participant_id": participant_id, "level": nivel,
            "case_id": scenario.case.id, "case_started_ts": time.time(), "started_at": now,
            "tutor_requests": 0, "decided": False, "created_at": now,
        })
        self._emit("session_started", {"session_id": session_id, "participant_id": participant_id})
        return {"sesion_id": session_id, "participante_id": participant_id,
                "aviso_legal": LEGAL_NOTICE,
                "escenario": {**scenario.public(), "transcurrido_s": 0}}

    def get_scenario(self, session_id: str) -> dict:
        s = self._session(session_id)
        data = self.factory.rebuild(s["case_id"], s["level"]).public()
        data["transcurrido_s"] = max(0, int(time.time() - s["case_started_ts"]))
        return data

    # ---- UC-03: agente tutor ---------------------------------------------
    def request_tutor(self, session_id: str, message: Optional[str]) -> dict:
        s = self._session(session_id)
        if s["decided"]:
            raise AppError("ALREADY_DECIDED", "La decisión de esta sesión ya fue registrada.", 409)
        if s["tutor_requests"] >= self.settings.tutor_max_requests:
            raise AppError("TUTOR_LIMIT", "Alcanzaste el máximo de consultas al tutor en esta sesión.", 429)
        case = self.factory.get_case(s["case_id"])
        first = self._first_suggestion(session_id)
        label, condition = (first["label"], first["condition"]) if first else self._choose_suggestion(session_id, case)
        reply = self.tutor.suggest(case.title, s["level"], label, message)
        turn = s["tutor_requests"] + 1
        self.store.insert("sugerencias", {
            "session_id": session_id, "case_id": case.id, "turn": turn, "label": label,
            "condition": condition, "text": reply.text, "source": reply.source,
            "latency_ms": reply.latency_ms, "user_message": message, "created_at": now_iso(),
        })
        self.store.update("sesiones", session_id, {"tutor_requests": turn})
        self._emit("tutor_requested", {"session_id": session_id, "participant_id": s["participant_id"]})
        return {"texto": reply.text, "fuente": reply.source, "indice": turn,
                "restantes": self.settings.tutor_max_requests - turn}

    # ---- UC-04: decisión y métricas --------------------------------------
    def register_decision(self, session_id: str, decision: str, confidence: int) -> dict:
        if decision not in OPTIONS:
            raise AppError("INVALID_INPUT", "La interpretación elegida no es válida.", 422)
        with self._lock:
            s = self._session(session_id)
            if s["decided"]:
                raise AppError("ALREADY_DECIDED", "La decisión de esta sesión ya fue registrada.", 409)
            self.store.update("sesiones", session_id, {"decided": True})
        case = self.factory.get_case(s["case_id"])
        sug = self._first_suggestion(session_id)
        decision_id = uuid.uuid4().hex
        elapsed = round(time.time() - s["case_started_ts"], 1)
        self.store.insert("decisiones", {
            "_id": decision_id, "session_id": session_id, "participant_id": s["participant_id"],
            "case_id": case.id, "decision": decision, "confidence": confidence,
            "response_time_s": elapsed, "created_at": now_iso(),
        })
        self.store.update("sesiones", session_id, {"decision_id": decision_id})
        self._emit("decision_registered", {
            "decision_id": decision_id, "session_id": session_id, "participant_id": s["participant_id"],
            "case_id": case.id, "level": s["level"], "decision": decision, "confidence": confidence,
            "response_time_s": elapsed, "reference": case.reference,
            "suggestion": {"label": sug["label"], "condition": sug["condition"]} if sug else None,
        })
        return {"decision_id": decision_id}

    # ---- UC-05: panel de resultados --------------------------------------
    def get_results(self, session_id: str) -> dict:
        s = self._session(session_id)
        if not s["decided"] or "decision_id" not in s:
            raise AppError("NO_DECISION", "Aún no registras una decisión en esta sesión.", 409)
        d = self.store.get("decisiones", s["decision_id"])
        case = self.factory.get_case(s["case_id"])
        sug = self._first_suggestion(session_id)
        ev = evaluate_decision(d["decision"], case.reference,
                               {"label": sug["label"], "condition": sug["condition"]} if sug else None)
        tutor = {"consultado": False}
        if sug:
            tutor = {"consultado": True, "codigo": sug["label"], "etiqueta": OPTIONS[sug["label"]],
                     "condicion": sug["condition"], "siguio": ev["followed_ai"], "correcta": ev["ai_correct"]}
        return {
            "aviso_legal": LEGAL_NOTICE,
            "caso": {"id": case.id, "titulo": case.title, "nivel": s["level"]},
            "decision": {"codigo": d["decision"], "etiqueta": OPTIONS[d["decision"]]},
            "confianza": d["confidence"],
            "tiempo_respuesta_s": d["response_time_s"],
            "correcta": ev["correct"],
            "exactitud_pct": 100.0 if ev["correct"] else 0.0,
            "referencia": {"codigo": case.reference, "etiqueta": OPTIONS[case.reference],
                           "justificacion": case.rationale},
            "tutor": tutor,
            "estado": classify(ev),
        }

    def submit_sus(self, session_id: str, answers: list) -> dict:
        s = self._session(session_id)
        if not s["decided"]:
            raise AppError("NO_DECISION", "Completa la simulación antes del cuestionario SUS.", 409)
        score = score_sus(answers)
        with self._lock:
            if self.store.find("sus", {"session_id": session_id}):
                raise AppError("SUS_ALREADY_SUBMITTED", "Ya enviaste el cuestionario SUS.", 409)
            self.store.insert("sus", {"session_id": session_id, "participant_id": s["participant_id"],
                                      "answers": answers, "score": score, "created_at": now_iso()})
        self._emit("sus_submitted", {"session_id": session_id, "participant_id": s["participant_id"]})
        return {"puntaje": score}

    # ---- panel docente / administrador (sin datos personales) ------------
    def admin_summary(self) -> dict:
        docs = self.store.find("metricas")
        agg = aggregate(docs)
        niveles = {}
        for level in ("basico", "intermedio", "avanzado"):
            sub = aggregate([d for d in docs if d.get("level") == level])
            niveles[level] = {"decisiones": sub["decisiones"], "exactitud_pct": sub["exactitud_pct"],
                              "aor_pct": sub["tutor"]["aor_pct"]}
        scores = [d["score"] for d in self.store.find("sus")]
        agg.update({
            "sesiones": self.store.count("sesiones"),
            "por_nivel": niveles,
            "sus": {"respuestas": len(scores),
                    "promedio": round(sum(scores) / len(scores), 1) if scores else None},
        })
        return agg
