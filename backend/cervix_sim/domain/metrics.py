"""Métricas de interacción humano-IA (UC-04).

Definición operativa de AOR (sesgo de automatización) usada por el sistema:
    AOR = (veces que el usuario siguió una sugerencia inexacta del tutor)
          / (sugerencias inexactas mostradas)
Un solo caso no confirma un sesgo; la tasa tiene sentido al agregar sesiones.
El equipo y el docente deben confirmar esta definición.
"""
from __future__ import annotations

from typing import Dict, Iterable, Optional


def evaluate_decision(decision: str, reference: str, suggestion: Optional[Dict]) -> Dict:
    correct = decision == reference
    if not suggestion:
        return {"correct": correct, "ai_shown": False, "followed_ai": None,
                "ai_correct": None, "aor_event": False, "condition": None}
    ai_correct = suggestion["label"] == reference
    followed = decision == suggestion["label"]
    return {"correct": correct, "ai_shown": True, "followed_ai": followed,
            "ai_correct": ai_correct, "aor_event": followed and not ai_correct,
            "condition": suggestion["condition"]}


def classify(ev: Dict) -> str:
    """Estado cualitativo que usa el panel para elegir el mensaje."""
    if not ev["ai_shown"]:
        return "sin_consulta"
    if ev["followed_ai"]:
        return "sobredependencia" if not ev["ai_correct"] else "acuerdo_correcto"
    return "contraste_ia_inexacta" if not ev["ai_correct"] else "desacuerdo_ia_correcta"


def _pct(num: float, den: float) -> Optional[float]:
    return round(100.0 * num / den, 1) if den else None


def aggregate(docs: Iterable[Dict]) -> Dict:
    docs = list(docs)
    n = len(docs)
    ai_shown = [d for d in docs if d.get("ai_shown")]
    wrong_ai = [d for d in ai_shown if not d.get("ai_correct")]
    followed_wrong = [d for d in wrong_ai if d.get("followed_ai")]
    followed = [d for d in ai_shown if d.get("followed_ai")]
    return {
        "decisiones": n,
        "exactitud_pct": _pct(sum(1 for d in docs if d["correct"]), n),
        "tiempo_medio_s": round(sum(d["response_time_s"] for d in docs) / n, 1) if n else None,
        "confianza_media": round(sum(d["confidence"] for d in docs) / n, 2) if n else None,
        "tutor": {
            "consultas": len(ai_shown),
            "inexactas_mostradas": len(wrong_ai),
            "seguidas_inexactas": len(followed_wrong),
            "aor_pct": _pct(len(followed_wrong), len(wrong_ai)),
            "tasa_seguimiento_pct": _pct(len(followed), len(ai_shown)),
        },
    }
