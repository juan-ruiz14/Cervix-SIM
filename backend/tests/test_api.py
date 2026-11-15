import json
import unittest

from cervix_sim.legal import LEGAL_NOTICE
from tests.helpers import VALID_START, LiveServer


def start(srv, **over):
    status, data, _ = srv.call("POST", "/api/sessions", {**VALID_START, **over})
    assert status == 201, (status, data)
    return data


def finish(srv, sid, decisions=("NORMAL", "HSIL", "NORMAL"), confidence=3, tutor=False):
    """Recorre los 3 casos de una sesión y devuelve las decisiones registradas."""
    out = []
    for i, d in enumerate(decisions):
        if tutor:
            srv.call("POST", f"/api/sessions/{sid}/tutor", {})
        status, dec, _ = srv.call("POST", f"/api/sessions/{sid}/decision", {"decision": d, "confianza": confidence})
        assert status == 201, (status, dec)
        out.append(dec)
        if dec["hay_siguiente"]:
            status, esc, _ = srv.call("POST", f"/api/sessions/{sid}/next")
            assert status == 200, (status, esc)
    return out


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

    def test_modelo_3d_se_sirve_como_glb(self):
        data = start(self.srv)
        esc = data["escenario"]
        self.assertEqual((esc["caso_numero"], esc["total_casos"]), (1, 3))
        status, body, headers = self.srv.call("GET", esc["modelo_url"])
        self.assertEqual(status, 200)
        self.assertEqual(self.srv.call_raw("GET", esc["modelo_url"])[:4], b"glTF")

    def test_secuencias_fijas_por_nivel(self):
        esperado = {"basico": ["CS-001", "CS-003", "CS-004"], "intermedio": ["CS-004", "CS-003", "CS-001"],
                    "avanzado": ["CS-009", "CS-007", "CS-004"]}
        for nivel, ids in esperado.items():
            data = start(self.srv, nivel=nivel)
            sid, vistos = data["sesion_id"], [data["escenario"]["caso_id"]]
            for _ in range(2):
                self.srv.call("POST", f"/api/sessions/{sid}/decision", {"decision": "NORMAL", "confianza": 3})
                status, esc, _ = self.srv.call("POST", f"/api/sessions/{sid}/next")
                self.assertEqual(status, 200)
                vistos.append(esc["caso_id"])
            self.assertEqual(vistos, ids, nivel)

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

    def test_resultados_requieren_los_tres_casos(self):
        sid = start(self.srv)["sesion_id"]
        status, data, _ = self.srv.call("GET", f"/api/sessions/{sid}/results")
        self.assertEqual((status, data["error"]["code"]), (409, "NO_DECISION"))
        self.assertEqual(self.srv.call("POST", f"/api/sessions/{sid}/sus", {"respuestas": [3] * 10})[0], 409)
        self.srv.call("POST", f"/api/sessions/{sid}/decision", {"decision": "NORMAL", "confianza": 3})
        # con 1 de 3 casos aún no hay resultados
        self.assertEqual(self.srv.call("GET", f"/api/sessions/{sid}/results")[1]["error"]["code"], "NO_DECISION")

    def test_next_exige_decision_y_tiene_fin(self):
        sid = start(self.srv)["sesion_id"]
        self.assertEqual(self.srv.call("POST", f"/api/sessions/{sid}/next")[1]["error"]["code"], "NO_DECISION")
        finish(self.srv, sid)
        self.assertEqual(self.srv.call("POST", f"/api/sessions/{sid}/next")[1]["error"]["code"], "NO_MORE_CASES")

    # ---- flujo completo ---------------------------------------------------
    def test_flujo_completo_con_tutor(self):
        data = start(self.srv, nivel="intermedio")
        sid, esc = data["sesion_id"], data["escenario"]
        self.assertEqual(len(esc["pistas"]), 1)
        status, reply, _ = self.srv.call("POST", f"/api/sessions/{sid}/tutor", {"mensaje": "¿Qué ves en los bordes?"})
        self.assertEqual((status, reply["fuente"], reply["indice"]), (200, "mock", 1))
        status, dec, _ = self.srv.call("POST", f"/api/sessions/{sid}/decision", {"decision": "LSIL", "confianza": 4})
        self.assertEqual((status, dec["caso_numero"], dec["hay_siguiente"]), (201, 1, True))
        # una segunda decisión del mismo caso se rechaza y el tutor se cierra
        self.assertEqual(self.srv.call("POST", f"/api/sessions/{sid}/decision", {"decision": "HSIL", "confianza": 1})[1]
                         ["error"]["code"], "ALREADY_DECIDED")
        self.assertEqual(self.srv.call("POST", f"/api/sessions/{sid}/tutor", {})[1]["error"]["code"], "ALREADY_DECIDED")
        status, esc2, _ = self.srv.call("POST", f"/api/sessions/{sid}/next")
        self.assertEqual((esc2["caso_numero"], esc2["decidido"]), (2, False))
        # el contador del tutor se reinicia por caso
        self.assertEqual(self.srv.call("POST", f"/api/sessions/{sid}/tutor", {})[1]["indice"], 1)
        finish_rest = [("HSIL", 3), ("NORMAL", 5)]
        for i, (d, c) in enumerate(finish_rest):
            self.srv.call("POST", f"/api/sessions/{sid}/decision", {"decision": d, "confianza": c})
            if i == 0:
                self.srv.call("POST", f"/api/sessions/{sid}/next")
        status, res, _ = self.srv.call("GET", f"/api/sessions/{sid}/results")
        self.assertEqual(status, 200)
        self.assertEqual(res["aviso_legal"], LEGAL_NOTICE)
        self.assertEqual([c["caso"]["id"] for c in res["casos"]], ["CS-004", "CS-003", "CS-001"])
        self.assertEqual([c["decision"]["codigo"] for c in res["casos"]], ["LSIL", "HSIL", "NORMAL"])
        self.assertEqual([c["correcta"] for c in res["casos"]], [False, True, True])
        self.assertEqual(res["resumen"]["aciertos"], 2)
        self.assertEqual(res["resumen"]["total"], 3)
        self.assertEqual(res["resumen"]["exactitud_pct"], 66.7)
        # CS-004: el tutor sugirió LSIL (inexacta) y el usuario la siguió -> sobredependencia
        c4 = res["casos"][0]
        self.assertEqual((c4["tutor"]["codigo"], c4["tutor"]["condicion"], c4["tutor"]["siguio"]),
                         ("LSIL", "inexacta", True))
        self.assertEqual(c4["estado"], "sobredependencia")
        self.assertEqual(res["estado"], "sobredependencia")
        self.assertEqual(res["resumen"]["tutor"], {"consultas": 2, "inexactas_mostradas": 1, "seguidas_inexactas": 1})
        for c in res["casos"]:
            self.assertIn("justificacion", c["referencia"])
            self.assertGreaterEqual(c["tiempo_respuesta_s"], 0)
        # SUS
        status, sus, _ = self.srv.call("POST", f"/api/sessions/{sid}/sus", {"respuestas": [5, 1] * 5})
        self.assertEqual((status, sus["puntaje"]), (201, 100.0))
        self.assertEqual(self.srv.call("POST", f"/api/sessions/{sid}/sus", {"respuestas": [3] * 10})[1]["error"]["code"],
                         "SUS_ALREADY_SUBMITTED")

    def test_sus_con_respuestas_invalidas(self):
        sid = start(self.srv)["sesion_id"]
        finish(self.srv, sid)
        for body in ({"respuestas": [3] * 9}, {"respuestas": [0] + [3] * 9}, {"respuestas": "x"}):
            self.assertEqual(self.srv.call("POST", f"/api/sessions/{sid}/sus", body)[0], 422, body)

    def test_comentario_final(self):
        sid = start(self.srv)["sesion_id"]
        url = f"/api/sessions/{sid}/comment"
        # antes de decidir no se permite
        self.assertEqual(self.srv.call("POST", url, {"texto": "hola"})[1]["error"]["code"], "NO_DECISION")
        finish(self.srv, sid)
        # validaciones: vacío, solo espacios, demasiado largo, campos extra
        for body in ({"texto": ""}, {"texto": "   "}, {"texto": "x" * 1001}, {"texto": "ok", "otro": 1}, {}):
            self.assertEqual(self.srv.call("POST", url, body)[0], 422, body)
        status, data, _ = self.srv.call("POST", url, {"texto": "  Muy buena experiencia  "})
        self.assertEqual((status, data["recibido"]), (201, True))
        self.assertEqual(self.srv.call("POST", url, {"texto": "otro"})[1]["error"]["code"], "COMMENT_ALREADY_SUBMITTED")

    def test_decision_sin_tutor_y_validaciones(self):
        sid = start(self.srv)["sesion_id"]
        for body in ({"decision": "XX", "confianza": 3}, {"decision": "HSIL", "confianza": 0},
                     {"decision": "HSIL", "confianza": 6}, {"decision": "HSIL", "confianza": "3"},
                     {"decision": "HSIL"}):
            status, data, _ = self.srv.call("POST", f"/api/sessions/{sid}/decision", body)
            self.assertEqual((status, data["error"]["code"]), (422, "INVALID_INPUT"), body)
        finish(self.srv, sid, confidence=2)
        res = self.srv.call("GET", f"/api/sessions/{sid}/results")[1]
        self.assertTrue(all(not c["tutor"]["consultado"] for c in res["casos"]))
        self.assertEqual(res["estado"], "sin_consulta")
        self.assertEqual(res["resumen"]["tutor"]["consultas"], 0)

    def test_limite_de_consultas_al_tutor(self):
        sid = start(self.srv)["sesion_id"]
        for i in range(3):
            self.assertEqual(self.srv.call("POST", f"/api/sessions/{sid}/tutor", {})[1]["indice"], i + 1)
        status, data, _ = self.srv.call("POST", f"/api/sessions/{sid}/tutor", {})
        self.assertEqual((status, data["error"]["code"]), (429, "TUTOR_LIMIT"))

    def test_veredicto_del_tutor_predefinido_por_caso(self):
        # El veredicto sale del banco, no del azar: solo CS-004 es inexacta (sugiere LSIL).
        esperado = {"CS-001": ("NORMAL", "calibrada"), "CS-003": ("HSIL", "calibrada"),
                    "CS-004": ("LSIL", "inexacta"), "CS-007": ("NORMAL", "calibrada"),
                    "CS-009": ("HSIL", "calibrada")}
        for nivel in ("basico", "avanzado"):
            sid = start(self.srv, nivel=nivel)["sesion_id"]
            finish(self.srv, sid, tutor=True)
            for s in self.srv.store.find("sugerencias", {"session_id": sid}):
                self.assertEqual((s["label"], s["condition"]), esperado[s["case_id"]], s["case_id"])

    # ---- telemetría y panel docente ---------------------------------------
    def test_telemetria_en_segundo_plano_y_panel_docente(self):
        sid = start(self.srv, nivel="basico")["sesion_id"]
        finish(self.srv, sid, tutor=True)
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
        self.assertGreaterEqual(resumen["decisiones"], 3)
        self.assertNotIn("correo", json.dumps(resumen))
        self.assertEqual(set(resumen["por_nivel"]), {"basico", "intermedio", "avanzado"})

    def test_panel_docente_protegido(self):
        self.assertEqual(self.srv.call("GET", "/api/admin/summary")[1]["error"]["code"], "FORBIDDEN")
        self.assertEqual(self.srv.call("GET", "/api/admin/summary", headers={"X-Admin-Token": "otro"})[0], 403)


class AdminDisabledTests(unittest.TestCase):
    def test_sin_token_configurado(self):
        with LiveServer(admin_token="") as srv:
            status, data, _ = srv.call("GET", "/api/admin/summary", headers={"X-Admin-Token": ""})
            self.assertEqual((status, data["error"]["code"]), (403, "ADMIN_DISABLED"))


class CorsTests(unittest.TestCase):
    def test_cors_solo_para_origenes_permitidos(self):
        with LiveServer(allowed_origins=("https://cervix-sim.vercel.app",)) as srv:
            _, _, h = srv.call("GET", "/api/health", headers={"Origin": "https://cervix-sim.vercel.app"})
            self.assertEqual(h.get("access-control-allow-origin"), "https://cervix-sim.vercel.app")
            _, _, h = srv.call("GET", "/api/health", headers={"Origin": "https://malicioso.example"})
            self.assertNotIn("access-control-allow-origin", {k.lower() for k in h})


if __name__ == "__main__":
    unittest.main()
