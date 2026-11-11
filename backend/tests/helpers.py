"""Utilidades de prueba: servidor Uvicorn real en un hilo y cliente HTTP con urllib."""
import json
import socket
import threading
import time
import urllib.error
import urllib.request

import uvicorn

from cervix_sim.api import create_app
from cervix_sim.config import Settings
from cervix_sim.store import MemoryStore
from cervix_sim.tutor import TutorClient


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class LiveServer:
    def __init__(self, **overrides):
        TutorClient.reset()
        base = dict(tutor_mode="mock", admin_token="secreto-de-prueba", frontend_dir="", inexact_every=3,
                    tutor_max_requests=3)
        base.update(overrides)
        self.settings = Settings(**base)
        self.store = MemoryStore()
        self.app = create_app(self.settings, self.store)
        self.port = free_port()
        self.server = uvicorn.Server(uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="error"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self):
        self.thread.start()
        for _ in range(100):
            if self.server.started:
                return self
            time.sleep(0.05)
        raise RuntimeError("El servidor no arrancó")

    def __exit__(self, *exc):
        self.server.should_exit = True
        self.thread.join(timeout=5)
        TutorClient.reset()

    def call(self, method, path, body=None, headers=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method,
                                     headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, self._parse(r.read().decode()), self._headers(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, self._parse(e.read().decode()), self._headers(e.headers)

    @staticmethod
    def _parse(text):
        try:
            return json.loads(text or "null")
        except ValueError:
            return text  # p. ej. un SVG

    @staticmethod
    def _headers(h):
        return {k.lower(): v for k, v in h.items()}

    def wait_for(self, fn, timeout=3.0):
        end = time.time() + timeout
        while time.time() < end:
            value = fn()
            if value:
                return value
            time.sleep(0.05)
        return None


VALID_START = {"nombre": "Ana Prueba", "rol": "estudiante", "correo": "ana@example.com",
               "nivel": "basico", "consentimiento": True}
