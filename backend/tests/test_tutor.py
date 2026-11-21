import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from cervix_sim.config import Settings
from cervix_sim.tutor import TutorClient, fallback_text
from tests.helpers import free_port


def fake_ollama(reply: dict, delay: float = 0.0):
    seen = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append(body)
            time.sleep(delay)
            payload = json.dumps(reply).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass  # el cliente ya agotó su tiempo de espera

        def log_message(self, *a):
            pass

    port = free_port()
    srv = HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port, seen


def fake_gemini(reply: dict, status: int = 200):
    seen = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append({"path": self.path, "key": self.headers.get("x-goog-api-key"), "body": body})
            payload = json.dumps(reply).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *a):
            pass

    port = free_port()
    srv = HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port, seen


def gemini_settings(port, **kw):
    return Settings(gemini_api_key=kw.pop("key", "CLAVE-SECRETA"), gemini_model="modelo-x",
                    gemini_base_url=f"http://127.0.0.1:{port}", **kw)


class TutorTests(unittest.TestCase):
    def setUp(self):
        TutorClient.reset()

    def tearDown(self):
        TutorClient.reset()

    def test_singleton(self):
        s = Settings(tutor_mode="mock")
        self.assertIs(TutorClient.instance(s), TutorClient.instance(s))

    def test_mock(self):
        r = TutorClient.instance(Settings(tutor_mode="mock")).suggest("Caso", "basico", "HSIL")
        self.assertEqual(r.source, "mock")
        self.assertIn("alto grado", r.text)

    def test_ollama_ok_no_filtra_la_referencia(self):
        srv, port, seen = fake_ollama({"response": "  Texto del modelo  "})
        try:
            t = TutorClient.instance(Settings(tutor_mode="ollama", ollama_url=f"http://127.0.0.1:{port}"))
            r = t.suggest("Caso CS-1", "basico", "LSIL", "¿Por qué?")
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertEqual((r.text, r.source), ("Texto del modelo", "ollama"))
        self.assertIn("bajo grado", seen[0]["prompt"])
        self.assertIn("¿Por qué?", seen[0]["prompt"])
        self.assertFalse(seen[0]["stream"])

    def test_ollama_caido_usa_respaldo(self):
        t = TutorClient.instance(Settings(tutor_mode="auto", ollama_url=f"http://127.0.0.1:{free_port()}"))
        r = t.suggest("Caso", "basico", "NORMAL")
        self.assertEqual(r.source, "respaldo")
        self.assertEqual(r.text, fallback_text("NORMAL"))

    def test_tiempo_agotado_usa_respaldo(self):
        srv, port, _ = fake_ollama({"response": "tarde"}, delay=1.5)
        try:
            t = TutorClient.instance(Settings(tutor_mode="auto", ollama_url=f"http://127.0.0.1:{port}",
                                              tutor_timeout=0.3))
            start = time.monotonic()
            r = t.suggest("Caso", "basico", "HSIL")
            elapsed = time.monotonic() - start
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertEqual(r.source, "respaldo")
        self.assertLess(elapsed, 1.2)

    def test_respuesta_vacia_usa_respaldo(self):
        srv, port, _ = fake_ollama({"response": "   "})
        try:
            t = TutorClient.instance(Settings(tutor_mode="auto", ollama_url=f"http://127.0.0.1:{port}"))
            self.assertEqual(t.suggest("Caso", "basico", "HSIL").source, "respaldo")
        finally:
            srv.shutdown()
            srv.server_close()

    # ---- Gemini ---------------------------------------------------------
    def test_gemini_ok_clave_en_cabecera_y_sin_referencia(self):
        srv, port, seen = fake_gemini({"candidates": [{"content": {"parts": [{"text": " Texto "}, {"text": "de Gemini "}]}}]})
        try:
            t = TutorClient.instance(gemini_settings(port, tutor_mode="gemini"))
            r = t.suggest("Caso CS-1", "basico", "LSIL", "¿Por qué?")
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertEqual((r.text, r.source), ("Texto de Gemini", "gemini"))
        self.assertEqual(seen[0]["path"], "/v1beta/models/modelo-x:generateContent")
        self.assertEqual(seen[0]["key"], "CLAVE-SECRETA")
        prompt = seen[0]["body"]["contents"][0]["parts"][0]["text"]
        self.assertIn("bajo grado", prompt)
        self.assertIn("¿Por qué?", prompt)
        self.assertNotIn("CLAVE-SECRETA", json.dumps(seen[0]["body"]))
        self.assertNotIn("referencia", prompt.lower())

    def test_auto_usa_gemini_si_hay_clave_y_ollama_si_no(self):
        srv, port, seen = fake_gemini({"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})
        try:
            self.assertEqual(TutorClient.instance(gemini_settings(port)).suggest("C", "basico", "HSIL").source, "gemini")
            TutorClient.reset()
            sin_clave = gemini_settings(port, key="", ollama_url=f"http://127.0.0.1:{free_port()}")
            self.assertEqual(TutorClient.instance(sin_clave).suggest("C", "basico", "HSIL").source, "respaldo")
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertEqual(len(seen), 1)  # sin clave no se llama a Gemini

    def test_gemini_sin_clave_usa_respaldo(self):
        t = TutorClient.instance(Settings(tutor_mode="gemini", gemini_api_key=""))
        r = t.suggest("Caso", "basico", "NORMAL")
        self.assertEqual((r.source, r.text), ("respaldo", fallback_text("NORMAL")))

    def test_gemini_errores_usan_respaldo_sin_filtrar_la_clave(self):
        casos = ((429, {"error": {"message": "cuota"}}), (500, {}), (200, {"candidates": []}),
                 (200, {"candidates": [{"finishReason": "SAFETY"}]}),
                 (200, {"candidates": [{"content": {"parts": [{"text": "  "}]}}]}))
        for status, reply in casos:
            TutorClient.reset()
            srv, port, _ = fake_gemini(reply, status)
            try:
                with self.assertLogs("cervix_sim.tutor", level="WARNING") as logs:
                    r = TutorClient.instance(gemini_settings(port, tutor_mode="gemini")).suggest("C", "basico", "HSIL")
            finally:
                srv.shutdown()
                srv.server_close()
            self.assertEqual((r.source, r.text), ("respaldo", fallback_text("HSIL")), (status, reply))
            self.assertNotIn("CLAVE-SECRETA", "".join(logs.output))


if __name__ == "__main__":
    unittest.main()
