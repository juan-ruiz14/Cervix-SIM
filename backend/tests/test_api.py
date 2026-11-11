import json
import unittest

from cervix_sim.legal import LEGAL_NOTICE
from tests.helpers import VALID_START, LiveServer


def start(srv, **over):
    status, data, _ = srv.call("POST", "/api/sessions", {**VALID_START, **over})
    assert status == 201, (status, data)
    return data


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = LiveServer().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.srv.__exit__(None, None, None)

    # ---- básicos ---------------------------------------------------------
    def test_health_y_legal(self):
        status, data, headers = self.srv.call("GET", "/api/health")
        self.assertEqual((status, data["estado"], data["almacen"], data["tutor"]), (200, "ok", "memory", "mock"))
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(headers["x-content-type-options"], "nosniff")
        self.assertEqual(self.srv.call("GET", "/api/legal")[1]["aviso_legal"], LEGAL_NOTICE)

    def test_ruta_inexistente_devuelve_json_tipificado(self):
        status, data, _ = self.srv.call("GET", "/api/nada")
        self.assertEqual(status, 404)
        self.assertEqual(data["error"]["code"], "HTTP_404")

    def test_imagen_de_caso_se_sirve_como_svg(self):
        data = start(self.srv)
        status, body, headers = self.srv.call("GET", data["escenario"]["imagen_url"])
        self.assertEqual(status, 200)
        self.assertIn("<svg", body)
        self.assertEqual(headers["content-type"], "image/svg+xml")

    # ---- validación de entradas -----------------------------------------
    def test_validaciones_al_iniciar(self):
        casos = [
            ({"consentimiento": False}, 422, "CONSENT_REQUIRED"),
            ({"nombre": "A"}, 422, "INVALID_INPUT"),
            ({"correo": "no-es-correo"}, 422, "INVALID_INPUT"),
            ({"rol": "administrador"}, 422, "INVALID_INPUT"),
            ({"nivel": "experto"}, 422, "INVALID_INPUT"),
            ({"extra": 1}, 422, "INVALID_INPUT"),
        ]
        for over, st, code in casos:
            status, data, _ = self.srv.call("POST", "/api/sessions", {**VALID_START, **over})
            self.assertEqual((status, data["error"]["code"]), (st, code), over)
        status, data, _ = self.srv.call("POST", "/api/sessions", raw=b"{no es json")
        self.assertEqual((status, data["error"]["code"]), (422, "INVALID_INPUT"))
        self.assertEqual(self.srv.call("POST", "/api/sessions", raw=b"")[0], 422)

    def test_sesion_inexistente(self):
        for method, path in (("GET", "/api/sessions/x/scenario"), ("GET", "/api/sessions/x/results"),
                             ("POST", "/api/sessions/x/tutor")):
            status, data, _ = self.srv.call(method, path)
            self.assertEqual((status, data["error"]["code"]), (404, "SESSION_NOT_FOUND"), path)

    # ---- confidencialidad de la referencia ------------------------------
    def test_escenario_y_tutor_no_filtran_referencia_ni_condicion(self):
        data = start(self.srv, nivel="avanzado")
        sid = data["sesion_id"]
        text = json.dumps(data) + json.dumps(self.srv.call("GET", f"/api/sessions/{sid}/scenario")[1])
        self.assertNotIn("justificacion", text)
        self.assertNotIn("referencia", text)
        self.assertNotIn("nombre", data)
        status, reply, _ = self.srv.call("POST", f"/api/sessions/{sid}/tutor", {})
        self.assertEqual(status, 200)
        for forbidden in ("condicion", "inexacta", "calibrada", "codigo"):
            self.assertNotIn(forbidden, json.dumps(reply))
        self.assertIn("aviso_ia", reply)

    def test_resultados_requieren_decision(self):
        sid = start(self.srv)["sesion_id"]
        status, data, _ = self.srv.call("GET", f"/api/sessions/{sid}/results")
        self.assertEqual((status, data["error"]["code"]), (409, "NO_DECISION"))
        self.assertEqual(self.srv.call("POST", f"/api/sessions/{sid}/sus", {"respuestas": [3] * 10})[0], 409)

    # ---- flujo completo ---------------------------------------------------
    def test_flujo_completo_con_tutor(self):
        data = start(self.srv, nivel="intermedio")
        sid, esc = data["sesion_id"], data["escenario"]
        self.assertEqual(len(esc["pistas"]), 1)
        status, reply, _ = self.srv.call("POST", f"/api/sessions/{sid}/tutor", {"mensaje": "¿Qué ves en los bordes?"})
        self.assertEqual((status, reply["fuente"], reply["indice"]), (200, "mock", 1))
        status, dec, _ = self.srv.call("POST", f"/api/sessions/{sid}/decision", {"decision": "LSIL", "confianza": 4})
        self.assertEqual(status, 201)
        # una segunda decisión se rechaza y el tutor se cierra
        self.assertEqual(self.srv.call("POST", f"/api/sessions/{sid}/decision", {"decision": "HSIL", "confianza": 1})[1]
                         ["error"]["code"], "ALREADY_DECIDED")
        self.assertEqual(self.srv.call("POST", f"/api/sessions/{sid}/tutor", {})[1]["error"]["code"], "ALREADY_DECIDED")
        status, res, _ = self.srv.call("GET", f"/api/sessions/{sid}/results")
        self.assertEqual(status, 200)
        self.assertEqual(res["decision"]["codigo"], "LSIL")
        self.assertEqual(res["confianza"], 4)
        self.assertEqual(res["aviso_legal"], LEGAL_NOTICE)
        self.assertTrue(res["tutor"]["consultado"])
        self.assertIn(res["tutor"]["condicion"], ("calibrada", "inexacta"))
        self.assertIn(res["estado"], ("acuerdo_correcto", "sobredependencia", "contraste_ia_inexacta",
                                      "desacuerdo_ia_correcta"))
        self.assertEqual(res["correcta"], res["decision"]["codigo"] == res["referencia"]["codigo"])
        self.assertGreaterEqual(res["tiempo_respuesta_s"], 0)
        # SUS
        status, sus, _ = self.srv.call("POST", f"/api/sessions/{sid}/sus", {"respuestas": [5, 1] * 5})
        self.assertEqual((status, sus["puntaje"]), (201, 100.0))
        self.assertEqual(self.srv.call("POST", f"/api/sessions/{sid}/sus", {"respuestas": [3] * 10})[1]["error"]["code"],
                         "SUS_ALREADY_SUBMITTED")

    def test_sus_con_respuestas_invalidas(self):
        sid = start(self.srv)["sesion_id"]
        self.srv.call("POST", f"/api/sessions/{sid}/decision", {"decision": "NORMAL", "confianza": 3})
        for body in ({"respuestas": [3] * 9}, {"respuestas": [0] + [3] * 9}, {"respuestas": "x"}):
            self.assertEqual(self.srv.call("POST", f"/api/sessions/{sid}/sus", body)[0], 422, body)

    def test_decision_sin_tutor_y_validaciones(self):
        sid = start(self.srv)["sesion_id"]
        for body in ({"decision": "XX", "confianza": 3}, {"decision": "HSIL", "confianza": 0},
                     {"decision": "HSIL", "confianza": 6}, {"decision": "HSIL", "confianza": "3"},
                     {"decision": "HSIL"}):
            status, data, _ = self.srv.call("POST", f"/api/sessions/{sid}/decision", body)
            self.assertEqual((status, data["error"]["code"]), (422, "INVALID_INPUT"), body)
        self.assertEqual(self.srv.call("POST", f"/api/sessions/{sid}/decision", {"decision": "NORMAL", "confianza": 2})[0], 201)
        res = self.srv.call("GET", f"/api/sessions/{sid}/results")[1]
        self.assertFalse(res["tutor"]["consultado"])
        self.assertEqual(res["estado"], "sin_consulta")

    def test_limite_de_consultas_al_tutor(self):
        sid = start(self.srv)["sesion_id"]
        for i in range(3):
            self.assertEqual(self.srv.call("POST", f"/api/sessions/{sid}/tutor", {})[1]["indice"], i + 1)
        status, data, _ = self.srv.call("POST", f"/api/sessions/{sid}/tutor", {})
        self.assertEqual((status, data["error"]["code"]), (429, "TUTOR_LIMIT"))

    def test_la_sugerencia_es_coherente_en_toda_la_sesion(self):
        sid = start(self.srv)["sesion_id"]
        for _ in range(2):
            self.srv.call("POST", f"/api/sessions/{sid}/tutor", {})
        sugs = self.srv.store.find("sugerencias", {"session_id": sid})
        self.assertEqual(len({(s["label"], s["condition"]) for s in sugs}), 1)

    # ---- telemetría y panel docente ---------------------------------------
    def test_telemetria_en_segundo_plano_y_panel_docente(self):
        sid = start(self.srv, nivel="basico")["sesion_id"]
        self.srv.call("POST", f"/api/sessions/{sid}/tutor", {})
        self.srv.call("POST", f"/api/sessions/{sid}/decision", {"decision": "HSIL", "confianza": 5})
        metric = self.srv.wait_for(lambda: self.srv.store.find("metricas", {"session_id": sid}))
        self.assertTrue(metric, "el observador no registró la métrica")
        self.assertTrue(str(metric[0]["participant_id"]).startswith("P-"))
        self.assertNotIn("nombre", metric[0])
        self.assertNotIn("correo", metric[0])
        tipos = self.srv.wait_for(lambda: {e["type"] for e in self.srv.store.find("eventos", {"session_id": sid})}
                                  if len(self.srv.store.find("eventos", {"session_id": sid})) >= 3 else None)
        self.assertTrue({"session_started", "tutor_requested", "decision_registered"} <= tipos)
        # los datos personales solo están en `usuarios`
        usuarios = self.srv.store.find("usuarios")
        self.assertTrue(any(u["correo"] == "ana@example.com" for u in usuarios))
        status, resumen, _ = self.srv.call("GET", "/api/admin/summary", headers={"X-Admin-Token": "secreto-de-prueba"})
        self.assertEqual(status, 200)
        self.assertGreaterEqual(resumen["decisiones"], 1)
        self.assertNotIn("correo", json.dumps(resumen))
        self.assertEqual(set(resumen["por_nivel"]), {"basico", "intermedio", "avanzado"})

    def test_panel_docente_protegido(self):
        self.assertEqual(self.srv.call("GET", "/api/admin/summary")[1]["error"]["code"], "FORBIDDEN")
        self.assertEqual(self.srv.call("GET", "/api/admin/summary", headers={"X-Admin-Token": "otro"})[0], 403)

    def test_politica_de_sugerencias_inexactas_reproducible(self):
        # con inexact_every=3 aproximadamente una de cada tres sesiones recibe una sugerencia inexacta
        condiciones = []
        for _ in range(30):
            sid = start(self.srv)["sesion_id"]
            self.srv.call("POST", f"/api/sessions/{sid}/tutor", {})
            condiciones.append(self.srv.store.find("sugerencias", {"session_id": sid})[0]["condition"])
        self.assertTrue(0 < condiciones.count("inexacta") < 30, condiciones)
        self.assertIn("calibrada", condiciones)


class AdminDisabledTests(unittest.TestCase):
    def test_sin_token_configurado(self):
        with LiveServer(admin_token="") as srv:
            status, data, _ = srv.call("GET", "/api/admin/summary", headers={"X-Admin-Token": ""})
            self.assertEqual((status, data["error"]["code"]), (403, "ADMIN_DISABLED"))


class NeverInexactTests(unittest.TestCase):
    def test_inexact_every_cero_desactiva_las_inexactas(self):
        with LiveServer(inexact_every=0) as srv:
            for _ in range(12):
                sid = start(srv)["sesion_id"]
                srv.call("POST", f"/api/sessions/{sid}/tutor", {})
                self.assertEqual(srv.store.find("sugerencias", {"session_id": sid})[0]["condition"], "calibrada")


class CorsTests(unittest.TestCase):
    def test_cors_solo_para_origenes_permitidos(self):
        with LiveServer(allowed_origins=("https://cervix-sim.vercel.app",)) as srv:
            _, _, h = srv.call("GET", "/api/health", headers={"Origin": "https://cervix-sim.vercel.app"})
            self.assertEqual(h.get("access-control-allow-origin"), "https://cervix-sim.vercel.app")
            _, _, h = srv.call("GET", "/api/health", headers={"Origin": "https://malicioso.example"})
            self.assertNotIn("access-control-allow-origin", {k.lower() for k in h})


if __name__ == "__main__":
    unittest.main()
