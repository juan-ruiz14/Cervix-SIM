"""Banco de casos: definición, carga y validación básica."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

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
    title: str
    modality: str
    model: str              # archivo .glb dentro de static_models/
    reference: str          # referencia docente: NUNCA sale del servidor antes de la decisión
    ia_label: str           # veredicto predefinido del tutor para este caso
    ia_condition: str       # "calibrada" (= referencia) o "inexacta" (≠ referencia)
    findings: List[str]     # pistas didácticas, se muestran según el nivel
    rationale: str          # justificación docente, se muestra en los resultados
    source: str
    license: str
    anonymized: bool
    synthetic: bool
    version: str


@dataclass(frozen=True)
class Bank:
    cases: List[CaseTemplate]
    sequences: Dict[str, Tuple[str, ...]]   # nivel -> ids de casos, en orden fijo


def load_bank(path: str | Path) -> Bank:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        cases = [CaseTemplate(
            id=i["id"], title=i["title"], modality=i["modality"], model=i["model"],
            reference=i["reference"], ia_label=i["ia_veredicto"], ia_condition=i["ia_condicion"],
            findings=list(i["findings"]), rationale=i["rationale"], source=i["source"],
            license=i["license"], anonymized=bool(i["anonymized"]),
            synthetic=bool(i.get("synthetic", False)), version=i["version"],
        ) for i in raw["cases"]]
        sequences = {lvl: tuple(ids) for lvl, ids in raw["secuencias"].items()}
    except (OSError, ValueError, KeyError) as exc:
        raise AppError("CASES_UNAVAILABLE", "No se pudo cargar el banco de casos.", 500) from exc
    return Bank(cases=cases, sequences=sequences)


def load_cases(path: str | Path) -> List[CaseTemplate]:
    return load_bank(path).cases
