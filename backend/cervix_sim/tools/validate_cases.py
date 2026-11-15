"""Validación del banco de casos 3D antes de publicarlo (UC-06, UC-08, Req 005, R-04).

Uso (desde backend/):
    python -m cervix_sim.tools.validate_cases
Sale con código 1 si encuentra problemas.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List

from ..domain.cases import LEVELS, OPTIONS

REQUIRED = ("id", "title", "modality", "model", "reference", "ia_veredicto", "ia_condicion", "findings",
            "rationale", "source", "license", "anonymized", "version")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
GLB_MAGIC = b"glTF"
MAX_GLB_MB = 25  # límite de subida por la web de GitHub


def validate_bank(cases_file: Path, models_dir: Path) -> List[str]:
    problems: List[str] = []
    try:
        data = json.loads(Path(cases_file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"No se pudo leer {cases_file}: {exc}"]
    seen, by_id = set(), {}
    for item in data.get("cases", []):
        cid = item.get("id", "<sin id>")
        missing = [k for k in REQUIRED if k not in item]
        if missing:
            problems.append(f"{cid}: faltan campos {missing}")
            continue
        if cid in seen:
            problems.append(f"{cid}: id duplicado")
        seen.add(cid)
        by_id[cid] = item
        if item["reference"] not in OPTIONS:
            problems.append(f"{cid}: referencia no válida «{item['reference']}»")
        if item["ia_veredicto"] not in OPTIONS:
            problems.append(f"{cid}: veredicto del tutor no válido «{item['ia_veredicto']}»")
        if item["ia_condicion"] not in ("calibrada", "inexacta"):
            problems.append(f"{cid}: condición del tutor no válida «{item['ia_condicion']}»")
        elif (item["ia_veredicto"] == item["reference"]) != (item["ia_condicion"] == "calibrada"):
            problems.append(f"{cid}: la condición del tutor no coincide con su veredicto y la referencia")
        if item["anonymized"] is not True:
            problems.append(f"{cid}: el caso no está marcado como anonimizado")
        if not str(item["license"]).strip() or not str(item["source"]).strip():
            problems.append(f"{cid}: falta fuente o licencia")
        if not SEMVER.match(str(item["version"])):
            problems.append(f"{cid}: versión «{item['version']}» no sigue x.y.z")
        if not item["findings"] or not all(isinstance(f, str) and f.strip() for f in item["findings"]):
            problems.append(f"{cid}: pistas vacías o no válidas")
        glb = Path(models_dir) / item["model"]
        if glb.suffix.lower() != ".glb":
            problems.append(f"{cid}: el modelo debe ser un archivo .glb")
        elif not glb.is_file():
            problems.append(f"{cid}: no existe el modelo {item['model']}")
        else:
            if glb.read_bytes()[:4] != GLB_MAGIC:
                problems.append(f"{cid}: {item['model']} no es un GLB válido")
            if glb.stat().st_size > MAX_GLB_MB * 1024 * 1024:
                problems.append(f"{cid}: {item['model']} supera {MAX_GLB_MB} MB")
    seqs = data.get("secuencias", {})
    for level in LEVELS:
        seq = seqs.get(level)
        if not seq:
            problems.append(f"No hay secuencia para el nivel «{level}»")
            continue
        if len(seq) != len(set(seq)):
            problems.append(f"{level}: la secuencia repite casos")
        unknown = [c for c in seq if c not in by_id]
        if unknown:
            problems.append(f"{level}: casos desconocidos {unknown}")
            continue
        inexact = [c for c in seq if by_id[c].get("ia_condicion") == "inexacta"]
        if len(inexact) != 1:
            problems.append(f"{level}: debe haber exactamente 1 sugerencia inexacta del tutor (hay {len(inexact)})")
    return problems


def main(argv=None) -> int:
    from ..config import Settings
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    s = Settings()
    problems = validate_bank(Path(s.cases_file), Path(s.models_dir))
    if problems:
        print("Problemas encontrados:")
        for p in problems:
            print(" -", p)
        return 1
    print("Banco de casos válido.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
