import unittest

from cervix_sim.domain.cases import OPTIONS, load_cases
from cervix_sim.domain.events import EventBus
from cervix_sim.domain.factory import ScenarioFactory
from cervix_sim.domain.metrics import aggregate, classify, evaluate_decision
from cervix_sim.domain.sus import score_sus
from cervix_sim.config import Settings
from cervix_sim.errors import AppError


class MetricsTests(unittest.TestCase):
    def test_sin_sugerencia(self):
        ev = evaluate_decision("HSIL", "HSIL", None)
        self.assertTrue(ev["correct"])
        self.assertFalse(ev["ai_shown"])
        self.assertEqual(classify(ev), "sin_consulta")

    def test_sobredependencia_es_evento_aor(self):
        ev = evaluate_decision("LSIL", "HSIL", {"label": "LSIL", "condition": "inexacta"})
        self.assertTrue(ev["aor_event"])
        self.assertFalse(ev["correct"])
        self.assertEqual(classify(ev), "sobredependencia")

    def test_acuerdo_correcto_no_es_aor(self):
        ev = evaluate_decision("HSIL", "HSIL", {"label": "HSIL", "condition": "calibrada"})
        self.assertFalse(ev["aor_event"])
        self.assertEqual(classify(ev), "acuerdo_correcto")

    def test_contraste_ia_inexacta(self):
        ev = evaluate_decision("HSIL", "HSIL", {"label": "NORMAL", "condition": "inexacta"})
        self.assertEqual(classify(ev), "contraste_ia_inexacta")
        self.assertFalse(ev["aor_event"])

    def test_desacuerdo_ia_correcta(self):
        ev = evaluate_decision("NORMAL", "HSIL", {"label": "HSIL", "condition": "calibrada"})
        self.assertEqual(classify(ev), "desacuerdo_ia_correcta")

    def test_agregado_y_tasa_aor(self):
        base = dict(response_time_s=10.0, confidence=4)
        docs = [
            {**base, **evaluate_decision("LSIL", "HSIL", {"label": "LSIL", "condition": "inexacta"})},  # AOR
            {**base, **evaluate_decision("HSIL", "HSIL", {"label": "NORMAL", "condition": "inexacta"})},  # contrastó
            {**base, **evaluate_decision("HSIL", "HSIL", {"label": "HSIL", "condition": "calibrada"})},
            {**base, **evaluate_decision("NORMAL", "NORMAL", None)},
        ]
        agg = aggregate(docs)
        self.assertEqual(agg["decisiones"], 4)
        self.assertEqual(agg["exactitud_pct"], 75.0)
        self.assertEqual(agg["tutor"]["inexactas_mostradas"], 2)
        self.assertEqual(agg["tutor"]["seguidas_inexactas"], 1)
        self.assertEqual(agg["tutor"]["aor_pct"], 50.0)

    def test_agregado_vacio(self):
        agg = aggregate([])
        self.assertIsNone(agg["exactitud_pct"])
        self.assertIsNone(agg["tutor"]["aor_pct"])


class SusTests(unittest.TestCase):
    def test_maximo_y_neutro(self):
        self.assertEqual(score_sus([5, 1] * 5), 100.0)
        self.assertEqual(score_sus([3] * 10), 50.0)
        self.assertEqual(score_sus([1, 5] * 5), 0.0)

    def test_invalidos(self):
        for bad in ([1] * 9, [1] * 11, [0] + [3] * 9, [6] + [3] * 9, ["a"] * 10, [True] * 10, None):
            with self.assertRaises(AppError):
                score_sus(bad)


class FactoryTests(unittest.TestCase):
    def setUp(self):
        self.cases = load_cases(Settings().cases_file)
        self.factory = ScenarioFactory(self.cases)

    def test_pistas_por_nivel(self):
        self.assertEqual(len(self.factory.create("basico").hints), 3)
        self.assertEqual(len(self.factory.create("intermedio").hints), 1)
        self.assertEqual(len(self.factory.create("avanzado").hints), 0)

    def test_vista_publica_no_filtra_la_referencia(self):
        for level in ("basico", "intermedio", "avanzado"):
            pub = self.factory.create(level).public()
            self.assertNotIn("referencia", pub)
            self.assertNotIn("reference", pub)
            self.assertNotIn("justificacion", pub)
            self.assertEqual({o["codigo"] for o in pub["opciones"]}, set(OPTIONS))

    def test_nivel_invalido_y_sin_casos(self):
        with self.assertRaises(AppError):
            self.factory.create("experto")
        with self.assertRaises(AppError):
            ScenarioFactory([]).create("basico")

    def test_caso_inexistente(self):
        with self.assertRaises(AppError):
            self.factory.get_case("CS-999")


class EventBusTests(unittest.TestCase):
    def test_un_observador_que_falla_no_rompe_a_los_demas(self):
        bus, got = EventBus(), []
        bus.subscribe("x", lambda p: (_ for _ in ()).throw(RuntimeError("falla")))
        bus.subscribe("x", got.append)
        bus.publish("x", {"a": 1})
        self.assertEqual(got, [{"a": 1}])


if __name__ == "__main__":
    unittest.main()
