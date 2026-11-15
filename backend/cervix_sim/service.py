"""Servicio de simulación: orquesta los casos de uso UC-01 a UC-05.

Reglas de oro de la arquitectura (decisiones D3 y D10):
- La referencia docente y la condición de la sugerencia (calibrada/inexacta) viven solo
  en el servidor y se revelan después de registrar la decisión.
- Los datos de identificación (nombre, correo) quedan en `usuarios`; todo lo demás usa
  un identificador seudónimo de participante.
"""
from __future__ import annotations

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

    def _suggestion(self, session_id: str, case_id: str) -> Optional[dict]:
        found = self.store.find("sugerencias", {"session_id": session_id, "case_id": case_id}, sort="created_at")
        return found[0] if found else None

    def _scenario(self, s: dict) -> dict:
        total = len(s["case_ids"])
        data = self.factory.build(s["case_ids"][s["idx"]], s["level"], s["idx"] + 1, total).public()
        data["transcurrido_s"] = max(0, int(time.time() - s["case_started_ts"]))
        data["decidido"] = s["decided"]
        return data

    # ---- UC-01: seleccionar nivel y escenario -----------------------------
    def start_session(self, nombre: str, rol: str, correo: str, nivel: str, consentimiento: bool) -> dict:
        if not consentimiento:
            raise AppError("CONSENT_REQUIRED", "Debes aceptar el tratamiento de datos para continuar.", 422)
        case_ids = list(self.factory.sequence(nivel))  # secuencia fija por nivel
        participant_id = "P-" + uuid.uuid4().hex[:8]
        now = now_iso()
        self.store.insert("usuarios", {"_id": participant_id, "nombre": nombre, "correo": correo,
                                       "rol": rol, "consentimiento": True, "created_at": now})
        session_id = uuid.uuid4().hex
        s = {
            "_id": session_id, "participant_id": participant_id, "level": nivel,
            "case_ids": case_ids, "idx": 0, "case_started_ts": time.time(), "started_at": now,
            "tutor_requests": 0, "decided": False, "created_at": now,
        }
        self.store.insert("sesiones", s)
        self._emit("session_started", {"session_id": session_id, "participant_id": participant_id})
        return {"sesion_id": session_id, "participante_id": participant_id,
                "aviso_legal": LEGAL_NOTICE, "escenario": self._scenario(s)}

    def get_scenario(self, session_id: str) -> dict:
        return self._scenario(self._session(session_id))

    def _current_case(self, s: dict):
        return self.factory.get_case(s["case_ids"][s["idx"]])

    # ---- UC-03: agente tutor ---------------------------------------------
    def request_tutor(self, session_id: str, message: Optional[str]) -> dict:
        s = self._session(session_id)
        if s["decided"]:
            raise AppError("ALREADY_DECIDED", "La decisión de este caso ya fue registrada.", 409)
        if s["tutor_requests"] >= self.settings.tutor_max_requests:
            raise AppError("TUTOR_LIMIT", "Alcanzaste el máximo de consultas al tutor en este caso.", 429)
        case = self._current_case(s)
        # El veredicto del tutor está predefinido por caso en el banco; el modelo de lenguaje solo lo redacta.
        reply = self.tutor.suggest(case.title, s["level"], case.ia_label, message)
        turn = s["tutor_requests"] + 1
        self.store.insert("sugerencias", {
            "session_id": session_id, "case_id": case.id, "turn": turn, "label": case.ia_label,
            "condition": case.ia_condition, "text": reply.text, "source": reply.source,
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
                raise AppError("ALREADY_DECIDED", "La decisión de este caso ya fue registrada.", 409)
            self.store.update("sesiones", session_id, {"decided": True})
        case = self._current_case(s)
        sug = self._suggestion(session_id, case.id)
        decision_id = uuid.uuid4().hex
        elapsed = round(time.time() - s["case_started_ts"], 1)
        self.store.insert("decisiones", {
            "_id": decision_id, "session_id": session_id, "participant_id": s["participant_id"],
            "case_id": case.id, "case_index": s["idx"], "decision": decision, "confidence": confidence,
            "response_time_s": elapsed, "created_at": now_iso(),
        })
        self._emit("decision_registered", {
            "decision_id": decision_id, "session_id": session_id, "participant_id": s["participant_id"],
            "case_id": case.id, "level": s["level"], "decision": decision, "confidence": confidence,
            "response_time_s": elapsed, "reference": case.reference,
            "suggestion": {"label": sug["label"], "condition": sug["condition"]} if sug else None,
        })
        total = len(s["case_ids"])
        return {"decision_id": decision_id, "caso_numero": s["idx"] + 1, "total_casos": total,
                "hay_siguiente": s["idx"] + 1 < total}

    def next_case(self, session_id: str) -> dict:
        with self._lock:
            s = self._session(session_id)
            if not s["decided"]:
                raise AppError("NO_DECISION", "Registra tu decisión antes de pasar al siguiente caso.", 409)
            if s["idx"] + 1 >= len(s["case_ids"]):
                raise AppError("NO_MORE_CASES", "Ya completaste todos los casos de esta sesión.", 409)
            s.update({"idx": s["idx"] + 1, "decided": False, "tutor_requests": 0,
                      "case_started_ts": time.time()})
            self.store.update("sesiones", session_id, {"idx": s["idx"], "decided": False,
                                                       "tutor_requests": 0, "case_started_ts": s["case_started_ts"]})
        return self._scenario(s)

    # ---- UC-05: panel de resultados --------------------------------------
    def get_results(self, session_id: str) -> dict:
        s = self._session(session_id)
        total = len(s["case_ids"])
        decisions = {d["case_id"]: d for d in self.store.find("decisiones", {"session_id": session_id})}
        if not (s["decided"] and s["idx"] + 1 == total and len(decisions) == total):
            raise AppError("NO_DECISION", "Aún no completas los casos de esta sesión.", 409)
        items, states = [], []
        for n, cid in enumerate(s["case_ids"], start=1):
            case, d = self.factory.get_case(cid), decisions[cid]
            sug = self._suggestion(session_id, cid)
            ev = evaluate_decision(d["decision"], case.reference,
                                   {"label": sug["label"], "condition": sug["condition"]} if sug else None)
            tutor = {"consultado": False}
            if sug:
                tutor = {"consultado": True, "codigo": sug["label"], "etiqueta": OPTIONS[sug["label"]],
                         "condicion": sug["condition"], "siguio": ev["followed_ai"], "correcta": ev["ai_correct"]}
            state = classify(ev)
            states.append(state)
            items.append({
                "numero": n, "caso": {"id": case.id, "titulo": case.title},
                "decision": {"codigo": d["decision"], "etiqueta": OPTIONS[d["decision"]]},
                "confianza": d["confidence"], "tiempo_respuesta_s": d["response_time_s"],
                "correcta": ev["correct"],
                "referencia": {"codigo": case.reference, "etiqueta": OPTIONS[case.reference],
                               "justificacion": case.rationale},
                "tutor": tutor, "estado": state,
            })
        aciertos = sum(1 for i in items if i["correcta"])
        consultas = [i for i in items if i["tutor"]["consultado"]]
        inexactas = [i for i in consultas if not i["tutor"]["correcta"]]
        seguidas = [i for i in inexactas if i["tutor"]["siguio"]]
        priority = ("sobredependencia", "contraste_ia_inexacta", "desacuerdo_ia_correcta",
                    "acuerdo_correcto", "sin_consulta")
        return {
            "aviso_legal": LEGAL_NOTICE,
            "nivel": s["level"],
            "casos": items,
            "resumen": {
                "aciertos": aciertos, "total": total,
                "exactitud_pct": round(100.0 * aciertos / total, 1),
                "tiempo_total_s": round(sum(i["tiempo_respuesta_s"] for i in items), 1),
                "confianza_media": round(sum(i["confianza"] for i in items) / total, 2),
                "tutor": {"consultas": len(consultas), "inexactas_mostradas": len(inexactas),
                          "seguidas_inexactas": len(seguidas)},
            },
            "estado": next(p for p in priority if p in states),
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

    def submit_comment(self, session_id: str, text: str) -> dict:
        """Comentario libre y opcional al final de la sesión (una vez por sesión)."""
        s = self._session(session_id)
        if not s["decided"]:
            raise AppError("NO_DECISION", "Completa la simulación antes de dejar un comentario.", 409)
        text = (text or "").strip()
        if not text:
            raise AppError("EMPTY_COMMENT", "Escribe un comentario antes de enviarlo.", 422)
        with self._lock:
            if self.store.find("comentarios", {"session_id": session_id}):
                raise AppError("COMMENT_ALREADY_SUBMITTED", "Ya enviaste tu comentario.", 409)
            self.store.insert("comentarios", {"session_id": session_id, "participant_id": s["participant_id"],
                                              "text": text, "created_at": now_iso()})
        self._emit("comment_submitted", {"session_id": session_id, "participant_id": s["participant_id"]})
        return {"recibido": True}

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
        comments = self.store.find("comentarios", sort="created_at")
        agg.update({
            "sesiones": self.store.count("sesiones"),
            "por_nivel": niveles,
            "sus": {"respuestas": len(scores),
                    "promedio": round(sum(scores) / len(scores), 1) if scores else None},
            "comentarios": {"total": len(comments),
                            "recientes": [{"participante": c["participant_id"], "texto": c["text"],
                                           "fecha": c["created_at"]} for c in comments[-20:]]},
        })
        return agg
