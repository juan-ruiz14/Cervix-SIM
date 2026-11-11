"""Banco de casos: definición, carga y validación básica."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from ..errors import AppError

LEVELS = ("basico", "intermedio", "avanzado")

# Opciones de interpretación que ve el usuario (código -> etiqueta).
OPTIONS: Dict[str, str] = {
    "NORMAL": "Sin lesión (normal)",
    "LSIL": "Lesión de bajo grado (LSIL)",
    "HSIL": "Lesión de alto grado (HSIL)",
}


@dataclass(frozen=True)
class CaseTemplate:
    id: str
    level: str
    title: str
    modality: str
    image: str
    reference: str          # referencia docente: NUNCA sale del servidor antes de la decisión
    findings: List[str]     # pistas didácticas, se muestran según el nivel
    rationale: str          # justificación docente, se muestra en los resultados
    source: str
    license: str
    anonymized: bool
    synthetic: bool
    version: str


def load_cases(path: str | Path) -> List[CaseTemplate]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AppError("CASES_UNAVAILABLE", "No se pudo cargar el banco de casos.", 500) from exc
    cases = []
    for item in raw["cases"]:
        cases.append(CaseTemplate(
            id=item["id"], level=item["level"], title=item["title"], modality=item["modality"],
            image=item["image"], reference=item["reference"], findings=list(item["findings"]),
            rationale=item["rationale"], source=item["source"], license=item["license"],
            anonymized=bool(item["anonymized"]), synthetic=bool(item.get("synthetic", False)),
            version=item["version"],
        ))
    return cases
