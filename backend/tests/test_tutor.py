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


if __name__ == "__main__":
    unittest.main()
