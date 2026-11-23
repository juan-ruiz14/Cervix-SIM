"""Cuestionario de usabilidad SUS (Brooke, 1996): 10 ítems, escala 1 a 5."""
from __future__ import annotations

from typing import List

from ..errors import AppError


def score_sus(answers: List[int]) -> float:
    if (not isinstance(answers, list) or len(answers) != 10
            or any(isinstance(a, bool) or not isinstance(a, int) or not 1 <= a <= 5 for a in answers)):
        raise AppError("INVALID_INPUT", "El cuestionario SUS requiere 10 respuestas entre 1 y 5.", 422)
    total = 0
    for i, a in enumerate(answers, start=1):
        total += (a - 1) if i % 2 == 1 else (5 - a)
    return total * 2.5
