"""Validación del banco de casos antes de publicarlo (UC-06, UC-08, Req 005, R-04).

Uso (desde backend/):
    python -m cervix_sim.tools.validate_cases            # solo revisa
    python -m cervix_sim.tools.validate_cases --strip    # además limpia EXIF de imágenes raster (requiere pillow)
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

REQUIRED = ("id", "level", "title", "modality", "image", "reference", "findings", "rationale",
            "source", "license", "anonymized", "version")
RASTER = {".png", ".jpg", ".jpeg", ".webp"}
SVG_FORBIDDEN = re.compile(r"<script|\son\w+\s*=|javascript:|href\s*=\s*[\"']https?:", re.I)
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def validate_bank(cases_file: Path, images_dir: Path, strip: bool = False) -> List[str]:
    problems: List[str] = []
    try:
        data = json.loads(Path(cases_file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"No se pudo leer {cases_file}: {exc}"]
    seen = set()
    levels_found = set()
    for item in data.get("cases", []):
        cid = item.get("id", "<sin id>")
        missing = [k for k in REQUIRED if k not in item]
        if missing:
            problems.append(f"{cid}: faltan campos {missing}")
            continue
        if cid in seen:
            problems.append(f"{cid}: id duplicado")
        seen.add(cid)
        if item["level"] not in LEVELS:
            problems.append(f"{cid}: nivel no válido «{item['level']}»")
        levels_found.add(item["level"])
        if item["reference"] not in OPTIONS:
            problems.append(f"{cid}: referencia no válida «{item['reference']}»")
        if item["anonymized"] is not True:
            problems.append(f"{cid}: el caso no está marcado como anonimizado")
        if not str(item["license"]).strip() or not str(item["source"]).strip():
            problems.append(f"{cid}: falta fuente o licencia")
        if not SEMVER.match(str(item["version"])):
            problems.append(f"{cid}: versión «{item['version']}» no sigue x.y.z")
        if not item["findings"] or not all(isinstance(f, str) and f.strip() for f in item["findings"]):
            problems.append(f"{cid}: pistas vacías o no válidas")
        img = Path(images_dir) / item["image"]
        if not img.is_file():
            problems.append(f"{cid}: no existe la imagen {item['image']}")
            continue
        ext = img.suffix.lower()
        if ext == ".svg":
            if SVG_FORBIDDEN.search(img.read_text(encoding="utf-8", errors="ignore")):
                problems.append(f"{cid}: el SVG contiene scripts, eventos o enlaces externos")
        elif ext in RASTER:
            problems.extend(_check_raster(cid, img, strip))
        else:
            problems.append(f"{cid}: formato de imagen no permitido «{ext}»")
    for level in LEVELS:
        if level not in levels_found:
            problems.append(f"No hay casos para el nivel «{level}»")
    return problems


def _check_raster(cid: str, img: Path, strip: bool) -> List[str]:
    try:
        from PIL import Image
    except ImportError:
        return [f"{cid}: instala pillow para revisar metadatos de {img.name} (pip install -r requirements-tools.txt)"]
    with Image.open(img) as im:
        has_meta = bool(im.getexif()) or any(k in im.info for k in ("exif", "icc_profile", "xmp"))
        if not has_meta:
            return []
        if not strip:
            return [f"{cid}: {img.name} contiene metadatos (EXIF/XMP). Ejecuta con --strip"]
        clean = Image.new(im.mode, im.size)
        clean.putdata(list(im.getdata()))
    clean.save(img)
    return []


def main(argv=None) -> int:
    from ..config import Settings
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--strip", action="store_true", help="eliminar metadatos de imágenes raster")
    args = parser.parse_args(argv)
    s = Settings()
    problems = validate_bank(Path(s.cases_file), Path(s.cases_images_dir), strip=args.strip)
    if problems:
        print("Problemas encontrados:")
        for p in problems:
            print(" -", p)
        return 1
    print("Banco de casos válido.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
