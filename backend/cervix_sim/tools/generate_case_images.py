"""Genera los esquemas 2D sintéticos del banco de casos (SVG, sin datos de pacientes).

Uso (desde backend/):  python -m cervix_sim.tools.generate_case_images
Los esquemas son ilustraciones didácticas y no representan imágenes clínicas.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "static_cases"

# id -> (clase, semilla)
CASES = {
    "CS-001": ("NORMAL", 11), "CS-002": ("HSIL", 12), "CS-003": ("LSIL", 13), "CS-004": ("HSIL", 14),
    "CS-005": ("LSIL", 15), "CS-006": ("NORMAL", 16), "CS-007": ("HSIL", 17),
}


def _blob(cx: float, cy: float, base: float, jitter: float, points: int, rng: random.Random) -> str:
    start = rng.uniform(0, math.tau)
    pts = []
    for i in range(points):
        a = start + math.tau * i / points
        r = base * (1 + rng.uniform(-jitter, jitter))
        pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
    return " ".join(pts)


def build_svg(case_id: str, label: str, seed: int) -> str:
    rng = random.Random(seed)
    lesion = ""
    if label != "NORMAL":
        ang = rng.uniform(-math.pi * 0.9, -math.pi * 0.1)   # cuadrante superior
        dist = rng.uniform(70, 120)
        cx, cy = 400 + dist * math.cos(ang), 400 + dist * math.sin(ang)
        if label == "LSIL":
            poly = _blob(cx, cy, rng.uniform(55, 75), 0.10, 18, rng)
            lesion = f'<polygon points="{poly}" fill="#CBD5E3" opacity="0.42" filter="url(#soft)"/>'
        else:
            poly = _blob(cx, cy, rng.uniform(85, 115), 0.30, 11, rng)
            lesion = f'<polygon points="{poly}" fill="#E4EAF3" opacity="0.92" stroke="#F4F7FB" stroke-width="2"/>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800" role="img" aria-labelledby="t d">
<title id="t">Esquema cervical sintético {case_id}</title>
<desc id="d">Ilustración didáctica generada por el equipo de Cérvix-SIM. No es una imagen clínica.</desc>
<defs><filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="9"/></filter></defs>
<rect width="800" height="800" fill="#0B1220"/>
<circle cx="400" cy="400" r="340" fill="none" stroke="#3B4A63" stroke-width="2"/>
<circle cx="400" cy="400" r="305" fill="#4A5B78"/>
<circle cx="400" cy="400" r="255" fill="#93A4BF" opacity="0.85"/>
<circle cx="400" cy="400" r="190" fill="#46566F" stroke="#C9D3E3" stroke-width="2" stroke-dasharray="6 6"/>
{lesion}
<ellipse cx="400" cy="400" rx="58" ry="20" fill="#0B1220"/>
<g fill="#9FB0CB" font-family="Arial, sans-serif" font-size="22" text-anchor="middle">
<text x="400" y="38">12</text><text x="770" y="408">3</text><text x="400" y="780">6</text><text x="30" y="408">9</text></g>
<text x="24" y="780" fill="#7D8DA8" font-family="Arial, sans-serif" font-size="16" text-anchor="start">ESQUEMA SINTÉTICO · NO CLÍNICO</text>
</svg>
'''


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for case_id, (label, seed) in CASES.items():
        (OUT / f"{case_id}.svg").write_text(build_svg(case_id, label, seed), encoding="utf-8")
    print(f"{len(CASES)} esquemas generados en {OUT}")


if __name__ == "__main__":
    main()
