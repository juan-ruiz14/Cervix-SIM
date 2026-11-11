import json
import tempfile
import unittest
from pathlib import Path

from cervix_sim.config import Settings
from cervix_sim.tools.validate_cases import validate_bank


class BankTests(unittest.TestCase):
    def test_banco_real_es_valido(self):
        s = Settings()
        self.assertEqual(validate_bank(Path(s.cases_file), Path(s.cases_images_dir)), [])

    def _bank(self, tmp, **override):
        item = {"id": "CS-100", "level": "basico", "title": "t", "modality": "m", "image": "a.svg",
                "reference": "HSIL", "findings": ["x"], "rationale": "r", "source": "s", "license": "l",
                "anonymized": True, "version": "1.0.0"}
        item.update(override)
        base = {"cases": [item]}
        for lvl, cid in (("intermedio", "CS-101"), ("avanzado", "CS-102")):
            base["cases"].append({**item, "id": cid, "level": lvl})
        (tmp / "cases.json").write_text(json.dumps(base), encoding="utf-8")
        (tmp / "a.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
        return tmp / "cases.json", tmp

    def test_detecta_problemas(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            for override, expected in (({"anonymized": False}, "anonimizado"), ({"reference": "XX"}, "referencia"),
                                       ({"license": ""}, "licencia"), ({"version": "1"}, "versión"),
                                       ({"image": "falta.svg"}, "no existe")):
                f, img = self._bank(tmp, **override)
                problems = validate_bank(f, img)
                self.assertTrue(any(expected in p for p in problems), (override, problems))

    def test_svg_con_script_es_rechazado(self):
        with tempfile.TemporaryDirectory() as d:
            f, img = self._bank(Path(d))
            (img / "a.svg").write_text("<svg><script>alert(1)</script></svg>", encoding="utf-8")
            self.assertTrue(any("scripts" in p for p in validate_bank(f, img)))


if __name__ == "__main__":
    unittest.main()
