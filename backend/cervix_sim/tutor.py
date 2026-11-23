"""Agente Tutor IA: cliente del servicio externo (patrón Singleton, decisión D2/D3).

- Una única instancia por proceso, para no abrir llamadas innecesarias en capas gratuitas.
- El backend decide la etiqueta de la sugerencia (calibrada o inexacta). El modelo de
  lenguaje solo redacta. Al modelo nunca se le entrega la referencia docente.
- Proveedores: Gemini (API de Google) u Ollama. Modo auto = Gemini si hay GEMINI_API_KEY, si no Ollama.
- Si el proveedor no responde a tiempo o falla, se usa un texto de respaldo (CE-07, R-02).
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
    "LSIL": "la zona alterada es tenue y sus bordes se ven difusos",
    "HSIL": "la zona alterada es extensa y sus bordes se ven irregulares",
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
                "Contrasta esa idea con la distribución y los bordes de la superficie antes de decidir.")
    return (f"Mi hipótesis inicial es «{name}», porque {cue}. "
            "Contrasta esta sugerencia con los bordes y el relieve de la superficie al girar el modelo. "
            "¿Qué hallazgos apoyan tu decisión?")


class TutorClient:
    _instance: Optional["TutorClient"] = None
    _guard = threading.Lock()

    def __init__(self, mode: str, ollama_url: str, model: str, timeout: float, *,
                 gemini_key: str = "", gemini_model: str = "gemini-3.8-flash",
                 gemini_base_url: str = "https://generativelanguage.googleapis.com",
                 gemini_fallback_model: str = "", gemini_retries: int = 2,
                 gemini_retry_delay: float = 0.8) -> None:
        self.mode = mode
        self.ollama_url = ollama_url
        self.model = model
        self.timeout = timeout
        self.gemini_key = gemini_key
        self.gemini_model = gemini_model
        self.gemini_base_url = gemini_base_url.rstrip("/")
        self.gemini_fallback_model = gemini_fallback_model
        self.gemini_retries = max(0, gemini_retries)
        self.gemini_retry_delay = max(0.0, gemini_retry_delay)

    @classmethod
    def instance(cls, settings) -> "TutorClient":
        with cls._guard:
            if cls._instance is None:
                cls._instance = cls(settings.tutor_mode, settings.ollama_url, settings.ollama_model,
                                    settings.tutor_timeout, gemini_key=settings.gemini_api_key,
                                    gemini_model=settings.gemini_model,
                                    gemini_base_url=settings.gemini_base_url,
                                    gemini_fallback_model=settings.gemini_fallback_model,
                                    gemini_retries=settings.gemini_retries,
                                    gemini_retry_delay=settings.gemini_retry_delay)
            return cls._instance

    @classmethod
    def reset(cls) -> None:  # solo para pruebas
        with cls._guard:
            cls._instance = None

    def _provider(self) -> Optional[str]:
        """Proveedor efectivo según el modo; None = solo texto de respaldo."""
        if self.mode == "mock":
            return None
        if self.mode == "gemini":
            return "gemini"
        if self.mode == "ollama":
            return "ollama"
        return "gemini" if self.gemini_key else "ollama"  # auto

    def suggest(self, scenario_title: str, level: str, label: str,
                message: Optional[str] = None) -> TutorReply:
        start = time.monotonic()
        elapsed = lambda: int((time.monotonic() - start) * 1000)  # noqa: E731
        provider = self._provider()
        if provider is None:
            return TutorReply(fallback_text(label, message), "mock", elapsed())
        try:
            prompt = self._prompt(scenario_title, level, label, message)
            text = self._ask_gemini(prompt) if provider == "gemini" else self._ask_ollama(prompt)
            return TutorReply(text, provider, elapsed())
        except Exception as exc:  # noqa: BLE001
            # Nunca se registra la clave: va en una cabecera y los errores de urllib no la incluyen.
            log.warning("%s no disponible, se usa respaldo: %s", provider, exc)
            return TutorReply(fallback_text(label, message), "respaldo", elapsed())

    @staticmethod
    def _prompt(title: str, level: str, label: str, message: Optional[str]) -> str:
        name, cue = OPTIONS[label], LABEL_CUES[label]
        prompt = (
            "Eres un tutor educativo de un simulador académico sobre modelos 3D didácticos del cuello uterino. "
            "No emites diagnósticos y esto no es una herramienta médica. Responde en español, en máximo 3 frases, "
            f"con tono amable. Sostén esta hipótesis: «{name}», apoyándote en que {cue}. "
            "Termina invitando al estudiante a contrastar la sugerencia con la evidencia del modelo.\n"
            f"Caso: {title} (nivel {level}).\n"
        )
        if message:
            prompt += f"Consulta del estudiante: {message[:500]}\n"
        return prompt

    def _post_json(self, url: str, payload: dict, headers: dict, timeout: Optional[float] = None) -> dict:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json", **headers}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:  # noqa: S310 - URL configurada por el equipo
            return json.loads(resp.read().decode("utf-8"))

    def _ask_ollama(self, prompt: str) -> str:
        data = self._post_json(f"{self.ollama_url}/api/generate",
                               {"model": self.model, "prompt": prompt, "stream": False,
                                "options": {"temperature": 0.4, "num_predict": 200}}, {})
        text = (data.get("response") or "").strip()
        if not text:
            raise ValueError("Respuesta vacía del modelo")
        return text[:1200]

    # Errores transitorios de Google (saturación, cuota por minuto, red): conviene reintentar.
    _TRANSIENT_HTTP = {429, 500, 502, 503, 504}

    def _ask_gemini(self, prompt: str) -> str:
        if not self.gemini_key:
            raise ValueError("Falta GEMINI_API_KEY")
        models = [self.gemini_model]
        if self.gemini_fallback_model and self.gemini_fallback_model != self.gemini_model:
            models.append(self.gemini_fallback_model)
        deadline = time.monotonic() + self.timeout * 2  # presupuesto total; el estudiante no espera más
        last: Exception = RuntimeError("Gemini sin intentos")
        for model in models:
            for attempt in range(self.gemini_retries + 1):
                remaining = deadline - time.monotonic()
                if remaining <= 0.5:
                    raise last
                try:
                    return self._gemini_once(model, prompt, min(self.timeout, remaining))
                except urllib.error.HTTPError as exc:
                    last = exc
                    transient = exc.code in self._TRANSIENT_HTTP
                except (urllib.error.URLError, TimeoutError, OSError) as exc:
                    last, transient = exc, True
                except ValueError as exc:  # respuesta vacía o bloqueada: otro modelo puede responder
                    last, transient = exc, False
                log.info("Gemini %s intento %d falló: %s", model, attempt + 1, last)
                if not transient:
                    break  # 400/401/403/404 o vacío: reintentar el mismo modelo no sirve
                if attempt < self.gemini_retries:
                    time.sleep(min(self.gemini_retry_delay * (attempt + 1), max(0.0, deadline - time.monotonic())))
        raise last

    def _gemini_once(self, model: str, prompt: str, timeout: float) -> str:
        url = f"{self.gemini_base_url}/v1beta/models/{model}:generateContent"
        data = self._post_json(url, {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 800},
        }, {"x-goog-api-key": self.gemini_key}, timeout)
        candidates = data.get("candidates") or []
        parts = (candidates[0].get("content") or {}).get("parts") or [] if candidates else []
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()
        if not text:  # sin candidatos (p. ej. bloqueo de seguridad) o respuesta vacía
            raise ValueError("Respuesta vacía de Gemini")
        return text[:1200]
