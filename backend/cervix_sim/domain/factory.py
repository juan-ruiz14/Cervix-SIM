"""Motor de simulación: fábrica de escenarios (patrón Factory).

Cada nivel tiene una secuencia fija de casos (definida en el banco). La fábrica arma el
escenario de un caso con las pistas y el tiempo objetivo del nivel y oculta al resto del
sistema los detalles de armado. La vista pública NUNCA incluye la referencia docente
ni el veredicto del tutor.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from ..errors import AppError
from .cases import LEVELS, OPTIONS, Bank, CaseTemplate

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
    number: int = 1
    total: int = 1

    def public(self) -> dict:
        c = self.case
        return {
            "caso_id": c.id,
            "titulo": c.title,
            "nivel": self.level,
            "modalidad": c.modality,
            "modelo_url": f"/static/models/{c.model}",
            "caso_numero": self.number,
            "total_casos": self.total,
            "opciones": [{"codigo": k, "etiqueta": v} for k, v in OPTIONS.items()],
            "pistas": list(self.hints),
            "tiempo_objetivo_s": self.target_seconds,
        }


class ScenarioFactory:
    def __init__(self, bank: Bank):
        self._cases = {c.id: c for c in bank.cases}
        self._sequences = bank.sequences

    def sequence(self, level: str) -> Tuple[str, ...]:
        if level not in LEVELS:
            raise AppError("INVALID_INPUT", "Nivel de dificultad no válido.", 422)
        seq = self._sequences.get(level)
        if not seq:
            raise AppError("NO_CASES", "No hay casos disponibles para ese nivel.", 404)
        return seq

    def build(self, case_id: str, level: str, number: int = 1, total: int = 1) -> Scenario:
        case = self.get_case(case_id)
        rules = LEVEL_RULES[level]
        return Scenario(case=case, level=level, hints=case.findings[: rules["hints"]],
                        target_seconds=rules["target_seconds"], number=number, total=total)

    def get_case(self, case_id: str) -> CaseTemplate:
        try:
            return self._cases[case_id]
        except KeyError:
            raise AppError("CASE_NOT_FOUND", "El caso no existe.", 404) from None
