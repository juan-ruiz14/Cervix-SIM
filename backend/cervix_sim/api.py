"""API REST (Starlette + Pydantic). Capa de aplicación de la arquitectura.

Todas las respuestas de error usan {"error": {"code", "message"}} (CE-07).
Las llamadas al servicio son bloqueantes (urllib, almacén), por eso se ejecutan
en un hilo para no detener el bucle de eventos.
"""
from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import __version__
from .config import Settings
from .domain.cases import load_cases
from .domain.events import EventBus
from .domain.factory import ScenarioFactory
from .errors import AppError
from .legal import AI_NOTICE, LEGAL_NOTICE
from .service import SimulationService
from .store import Store, build_store
from .telemetry import wire
from .tutor import TutorClient

log = logging.getLogger("cervix_sim.api")
EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class StartBody(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    nombre: str = Field(min_length=2, max_length=80)
    rol: Literal["estudiante", "profesional"]
    correo: str = Field(max_length=120, pattern=EMAIL_RE)
    nivel: Literal["basico", "intermedio", "avanzado"]
    consentimiento: bool


class TutorBody(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    mensaje: Optional[str] = Field(default=None, max_length=500)


class DecisionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(max_length=20)
    confianza: int = Field(strict=True, ge=1, le=5)


class SusBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    respuestas: List[int]


def _json(data, status: int = 200) -> JSONResponse:
    return JSONResponse(data, status_code=status)


def _error(code: str, message: str, status: int, **extra) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message, **extra}}, status_code=status)


async def _body(request: Request, model, allow_empty: bool = False):
    raw = await request.body()
    if not raw.strip():
        if allow_empty:
            return model()
        raise AppError("INVALID_INPUT", "Falta el cuerpo de la solicitud.", 422)
    try:
        return model.model_validate_json(raw)
    except ValidationError as exc:
        fields = [{"campo": ".".join(str(p) for p in e["loc"]), "mensaje": e["msg"]} for e in exc.errors()]
        raise AppError("INVALID_INPUT", "Revisa los datos enviados.", 422, campos=fields) from exc


def create_app(settings: Optional[Settings] = None, store: Optional[Store] = None) -> Starlette:
    settings = settings or Settings.from_env()
    store = store or build_store(settings)
    cases = load_cases(settings.cases_file)
    bus = EventBus()
    wire(bus, store)
    tutor = TutorClient.instance(settings)
    service = SimulationService(store, bus, tutor, ScenarioFactory(cases), settings)

    # ---- rutas ---------------------------------------------------------
    async def health(request: Request):
        return _json({"estado": "ok", "version": __version__, "tutor": tutor.mode, "almacen": store.kind})

    async def legal(request: Request):
        return _json({"aviso_legal": LEGAL_NOTICE, "aviso_ia": AI_NOTICE})

    async def start(request: Request):
        b = await _body(request, StartBody)
        data = await run_in_threadpool(service.start_session, b.nombre, b.rol, b.correo, b.nivel, b.consentimiento)
        return _json(data, 201)

    async def scenario(request: Request):
        return _json(await run_in_threadpool(service.get_scenario, request.path_params["session_id"]))

    async def ask_tutor(request: Request):
        b = await _body(request, TutorBody, allow_empty=True)
        data = await run_in_threadpool(service.request_tutor, request.path_params["session_id"], b.mensaje or None)
        data["aviso_ia"] = AI_NOTICE
        return _json(data)

    async def decide(request: Request):
        b = await _body(request, DecisionBody)
        data = await run_in_threadpool(service.register_decision, request.path_params["session_id"],
                                       b.decision, b.confianza)
        return _json(data, 201)

    async def results(request: Request):
        return _json(await run_in_threadpool(service.get_results, request.path_params["session_id"]))

    async def sus(request: Request):
        b = await _body(request, SusBody)
        return _json(await run_in_threadpool(service.submit_sus, request.path_params["session_id"], b.respuestas), 201)

    async def admin_summary(request: Request):
        if not settings.admin_token:
            raise AppError("ADMIN_DISABLED", "El panel docente está deshabilitado (falta ADMIN_TOKEN).", 403)
        given = request.headers.get("x-admin-token", "")
        if not secrets.compare_digest(given.encode(), settings.admin_token.encode()):
            raise AppError("FORBIDDEN", "No tienes permiso para ver este recurso.", 403)
        return _json(await run_in_threadpool(service.admin_summary))

    routes = [
        Route("/api/health", health),
        Route("/api/legal", legal),
        Route("/api/sessions", start, methods=["POST"]),
        Route("/api/sessions/{session_id}/scenario", scenario),
        Route("/api/sessions/{session_id}/tutor", ask_tutor, methods=["POST"]),
        Route("/api/sessions/{session_id}/decision", decide, methods=["POST"]),
        Route("/api/sessions/{session_id}/results", results),
        Route("/api/sessions/{session_id}/sus", sus, methods=["POST"]),
        Route("/api/admin/summary", admin_summary),
    ]
    if Path(settings.cases_images_dir).is_dir():
        routes.append(Mount("/static/cases", StaticFiles(directory=settings.cases_images_dir), name="cases"))
    if settings.frontend_dir and Path(settings.frontend_dir).is_dir():
        routes.append(Mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend"))

    # ---- errores -------------------------------------------------------
    async def on_app_error(request: Request, exc: AppError):
        return _error(exc.code, exc.message, exc.status, **exc.extra)

    async def on_http_error(request: Request, exc: StarletteHTTPException):
        return _error(f"HTTP_{exc.status_code}", "Recurso no encontrado." if exc.status_code == 404
                      else "Solicitud no permitida.", exc.status_code)

    async def on_unexpected(request: Request, exc: Exception):
        log.exception("Error no controlado")
        return _error("INTERNAL_ERROR", "Ocurrió un error inesperado. Intenta de nuevo.", 500)

    # ---- cabeceras de seguridad ---------------------------------------
    async def security_headers(request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; img-src 'self' data:; style-src 'self' https://fonts.googleapis.com; "
                "font-src https://fonts.gstatic.com; script-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        return response

    from starlette.middleware.base import BaseHTTPMiddleware
    middleware = [Middleware(BaseHTTPMiddleware, dispatch=security_headers)]
    if settings.allowed_origins:
        middleware.append(Middleware(CORSMiddleware, allow_origins=list(settings.allowed_origins),
                                     allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-Admin-Token"]))

    @asynccontextmanager
    async def lifespan(app: Starlette):
        yield
        await run_in_threadpool(service.close)  # termina la telemetría pendiente antes de apagar

    app = Starlette(
        routes=routes, middleware=middleware, lifespan=lifespan,
        exception_handlers={AppError: on_app_error, StarletteHTTPException: on_http_error, Exception: on_unexpected},
    )
    app.state.service, app.state.store, app.state.settings = service, store, settings
    return app
