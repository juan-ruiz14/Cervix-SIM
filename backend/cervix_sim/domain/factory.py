"""Motor de simulación: fábrica de escenarios (patrón Factory).

Según el nivel de dificultad elegido, construye el escenario con las pistas y el
tiempo objetivo correspondientes y oculta al resto del sistema los detalles de
armado. La vista pública NUNCA incluye la referencia docente.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional

from ..errors import AppError
from .cases import LEVELS, OPTIONS, CaseTemplate

LEVEL_RULES = {
    "basico": {"hints": 3, "target_seconds": 300},
    "intermedio": {"hints": 1, "target_seconds": 240},
    "avanzado": {"hints": 0, "target_seconds": 180},
}


@dataclass(frozen=True)
class Scenario:
    case: CaseTemplate
    level: str
    hints: List[str]
    target_seconds: int

    def public(self) -> dict:
        c = self.case
        return {
            "caso_id": c.id,
            "titulo": c.title,
            "nivel": self.level,
            "modalidad": c.modality,
            "imagen_url": f"/static/cases/{c.image}",
            "opciones": [{"codigo": k, "etiqueta": v} for k, v in OPTIONS.items()],
            "pistas": list(self.hints),
            "tiempo_objetivo_s": self.target_seconds,
        }


class ScenarioFactory:
    def __init__(self, cases: List[CaseTemplate], rng: Optional[random.Random] = None):
        self._cases = list(cases)
        self._rng = rng or random.Random()

    def create(self, level: str) -> Scenario:
        if level not in LEVELS:
            raise AppError("INVALID_INPUT", "Nivel de dificultad no válido.", 422)
        pool = [c for c in self._cases if c.level == level]
        if not pool:
            raise AppError("NO_CASES", "No hay casos disponibles para ese nivel.", 404)
        case = self._rng.choice(pool)
        rules = LEVEL_RULES[level]
        return Scenario(case=case, level=level, hints=case.findings[: rules["hints"]],
                        target_seconds=rules["target_seconds"])

    def rebuild(self, case_id: str, level: str) -> Scenario:
        """Reconstruye el escenario de una sesión ya iniciada (mismo caso y nivel)."""
        case = self.get_case(case_id)
        rules = LEVEL_RULES[level]
        return Scenario(case=case, level=level, hints=case.findings[: rules["hints"]],
                        target_seconds=rules["target_seconds"])

    def get_case(self, case_id: str) -> CaseTemplate:
        for c in self._cases:
            if c.id == case_id:
                return c
        raise AppError("CASE_NOT_FOUND", "El caso no existe.", 404)
