import json
import tempfile
import unittest
from pathlib import Path

from cervix_sim.config import Settings
from cervix_sim.tools.validate_cases import validate_bank


class BankTests(unittest.TestCase):
    def test_banco_real_es_valido(self):
        s = Settings()
        self.assertEqual(validate_bank(Path(s.cases_file), Path(s.models_dir)), [])

    def _bank(self, tmp, mutate=None):
        def item(cid, ref="HSIL", ia="HSIL", cond="calibrada"):
            return {"id": cid, "title": "t", "modality": "m", "model": f"{cid}.glb", "reference": ref,
                    "ia_veredicto": ia, "ia_condicion": cond, "findings": ["x"], "rationale": "r",
                    "source": "s", "license": "l", "anonymized": True, "version": "1.0.0"}
        bank = {"cases": [item("A"), item("B"), item("C", "NORMAL", "LSIL", "inexacta")],
                "secuencias": {l: ["A", "B", "C"] for l in ("basico", "intermedio", "avanzado")}}
        if mutate:
            mutate(bank)
        (tmp / "cases.json").write_text(json.dumps(bank), encoding="utf-8")
        for cid in ("A", "B", "C"):
            (tmp / f"{cid}.glb").write_bytes(b"glTF" + b"\0" * 20)
        return tmp / "cases.json", tmp

    def _problems(self, mutate=None):
        with tempfile.TemporaryDirectory() as d:
            f, m = self._bank(Path(d), mutate)
            return validate_bank(f, m)

    def test_banco_de_prueba_valido(self):
        self.assertEqual(self._problems(), [])

    def test_detecta_problemas_de_caso(self):
        casos = (({"anonymized": False}, "anonimizado"), ({"reference": "XX"}, "referencia"),
                 ({"license": ""}, "licencia"), ({"version": "1"}, "versión"),
                 ({"model": "falta.glb"}, "no existe"), ({"model": "A.png"}, ".glb"),
                 ({"ia_veredicto": "XX"}, "veredicto"), ({"ia_condicion": "x"}, "condición"),
                 ({"ia_condicion": "inexacta"}, "no coincide"))
        for override, expected in casos:
            problems = self._problems(lambda b, o=override: b["cases"][0].update(o))
            self.assertTrue(any(expected in p for p in problems), (override, problems))

    def test_glb_corrupto(self):
        with tempfile.TemporaryDirectory() as d:
            f, m = self._bank(Path(d))
            (m / "A.glb").write_bytes(b"nope")
            self.assertTrue(any("no es un GLB" in p for p in validate_bank(f, m)))

    def test_secuencias(self):
        def uno(b): b["secuencias"]["basico"] = ["A", "B", "B"]
        def inexistente(b): b["secuencias"]["avanzado"] = ["A", "B", "Z"]
        def sin_inexacta(b): b["secuencias"]["intermedio"] = ["A", "B"]
        def dos_inexactas(b): b["cases"][0].update(ia_veredicto="LSIL", ia_condicion="inexacta")
        def falta(b): del b["secuencias"]["basico"]
        for fn, expected in ((uno, "repite"), (inexistente, "desconocidos"), (sin_inexacta, "exactamente 1"),
                             (dos_inexactas, "exactamente 1"), (falta, "No hay secuencia")):
            self.assertTrue(any(expected in p for p in self._problems(fn)), fn.__name__)

    def test_banco_real_cumple_la_hoja_de_casos(self):
        data = json.loads(Path(Settings().cases_file).read_text(encoding="utf-8"))
        self.assertEqual(data["secuencias"], {"basico": ["CS-001", "CS-003", "CS-004"],
                                              "intermedio": ["CS-004", "CS-003", "CS-001"],
                                              "avanzado": ["CS-009", "CS-007", "CS-004"]})
        by = {c["id"]: c for c in data["cases"]}
        self.assertEqual({k: (v["reference"], v["ia_veredicto"]) for k, v in by.items()},
                         {"CS-001": ("NORMAL", "NORMAL"), "CS-003": ("HSIL", "HSIL"), "CS-004": ("NORMAL", "LSIL"),
                          "CS-007": ("NORMAL", "NORMAL"), "CS-009": ("HSIL", "HSIL")})


if __name__ == "__main__":
    unittest.main()
