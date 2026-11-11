"""Agente Tutor IA: cliente del servicio externo (patrón Singleton, decisión D2/D3).

- Una única instancia por proceso, para no abrir llamadas innecesarias en capas gratuitas.
- El backend decide la etiqueta de la sugerencia (calibrada o inexacta). El modelo de
  lenguaje solo redacta. Al modelo nunca se le entrega la referencia docente.
- Si Ollama no responde a tiempo o falla, se usa un texto de respaldo (CE-07, R-02).
- Sin dependencias externas: usa urllib de la biblioteca estándar.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

from .domain.cases import OPTIONS

log = logging.getLogger("cervix_sim.tutor")

# Pistas didácticas por clase. Se usan igual para sugerencias calibradas e inexactas,
# de modo que el texto no delata la condición.
LABEL_CUES = {
    "NORMAL": "no observo áreas de contraste anormales y la distribución se ve uniforme",
    "LSIL": "el área señalada es tenue y sus bordes se ven difusos",
    "HSIL": "el área señalada es densa y sus bordes se ven irregulares",
}


@dataclass(frozen=True)
class TutorReply:
    text: str
    source: str        # "ollama" | "respaldo" | "mock"
    latency_ms: int


def fallback_text(label: str, message: Optional[str] = None) -> str:
    name = OPTIONS[label]
    cue = LABEL_CUES[label]
    if message:
        return (f"Sobre tu consulta: mantengo mi hipótesis de «{name}», porque {cue}. "
                "Contrasta esa idea con la distribución y los bordes del área señalada antes de decidir.")
    return (f"Mi hipótesis inicial es «{name}», porque {cue}. "
            "Contrasta esta sugerencia con los bordes y la densidad del área señalada. "
            "¿Qué hallazgos apoyan tu decisión?")


class TutorClient:
    _instance: Optional["TutorClient"] = None
    _guard = threading.Lock()

    def __init__(self, mode: str, ollama_url: str, model: str, timeout: float) -> None:
        self.mode = mode
        self.ollama_url = ollama_url
        self.model = model
        self.timeout = timeout

    @classmethod
    def instance(cls, settings) -> "TutorClient":
        with cls._guard:
            if cls._instance is None:
                cls._instance = cls(settings.tutor_mode, settings.ollama_url,
                                    settings.ollama_model, settings.tutor_timeout)
            return cls._instance

    @classmethod
    def reset(cls) -> None:  # solo para pruebas
        with cls._guard:
            cls._instance = None

    def suggest(self, scenario_title: str, level: str, label: str,
                message: Optional[str] = None) -> TutorReply:
        start = time.monotonic()
        if self.mode != "mock":
            try:
                text = self._ask_ollama(scenario_title, level, label, message)
                return TutorReply(text, "ollama", int((time.monotonic() - start) * 1000))
            except Exception as exc:  # noqa: BLE001
                if self.mode == "ollama":
                    log.warning("Ollama no disponible, se usa respaldo: %s", exc)
                else:
                    log.info("Ollama no disponible (modo auto), se usa respaldo: %s", exc)
                source = "respaldo"
            return TutorReply(fallback_text(label, message), source, int((time.monotonic() - start) * 1000))
        return TutorReply(fallback_text(label, message), "mock", int((time.monotonic() - start) * 1000))

    def _ask_ollama(self, title: str, level: str, label: str, message: Optional[str]) -> str:
        name, cue = OPTIONS[label], LABEL_CUES[label]
        prompt = (
            "Eres un tutor educativo de un simulador académico sobre imágenes esquemáticas del cuello uterino. "
            "No emites diagnósticos y esto no es una herramienta médica. Responde en español, en máximo 3 frases, "
            f"con tono amable. Sostén esta hipótesis: «{name}», apoyándote en que {cue}. "
            "Termina invitando al estudiante a contrastar la sugerencia con la evidencia de la imagen.\n"
            f"Caso: {title} (nivel {level}).\n"
        )
        if message:
            prompt += f"Consulta del estudiante: {message[:500]}\n"
        body = json.dumps({"model": self.model, "prompt": prompt, "stream": False,
                           "options": {"temperature": 0.4, "num_predict": 200}}).encode("utf-8")
        req = urllib.request.Request(f"{self.ollama_url}/api/generate", data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 - URL configurada por el equipo
            data = json.loads(resp.read().decode("utf-8"))
        text = (data.get("response") or "").strip()
        if not text:
            raise ValueError("Respuesta vacía del modelo")
        return text[:1200]
