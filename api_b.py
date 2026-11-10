from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel
import asyncio
import httpx

router = APIRouter()

# ==========================================
# 1. MODELOS DE DATOS (Validación JSON)
# ==========================================
class ConsultaIA(BaseModel):
    vector_estado: dict

class Telemetria(BaseModel):
    aor_metrica: float
    sus_score: int
    id_sesion: str

class AccionClinica(BaseModel):
    id_accion: str
    parametros: dict

# ==========================================
# 2. PATRÓN OBSERVER (Telemetría Asíncrona)
# ==========================================
async def registrar_telemetria_db(datos: Telemetria):
    """
    Simula la inserción de métricas en la base de datos (PostgreSQL/SQLite).
    Garantiza que la latencia de escritura en DB no congele la simulación (< 0.5s).
    """
    # Aquí irá la instancia Singleton de SQLAlchemy o asyncpg
    await asyncio.sleep(0.1) 
    print(f"[Observer] Métricas AOR/SUS guardadas en DB para la sesión: {datos.id_sesion}")

# ==========================================
# 3. ENDPOINTS PRINCIPALES (Interfaces IO1, IO2, IO3)
# ==========================================

# IO1: Recepción de acciones clínicas
@router.post("/api/simulacion/accion")
async def registrar_accion(accion: AccionClinica):
    """Recibe y valida las decisiones del usuario interactuando con el entorno gamificado."""
    # Aquí se aplicaría el Patrón Factory Method para el motor de reglas
    return {"status": "actualizado", "feedback": "Acción procesada correctamente."}

# IO2: Comunicación con el Agente Tutor IA
@router.post("/api/tutor/evaluar")
async def consultar_tutor(consulta: ConsultaIA):
    """
    Consulta al microservicio IA segregado. 
    Implementa degradación controlada para proteger el rendimiento general.
    """
    # En producción esto debe leerse del archivo .env
    URL_MICROSERVICIO = "http://localhost:8001/ia/generar" 
    
    try:
        async with httpx.AsyncClient() as client:
            # Límite estricto de 3.0 segundos según documento de arquitectura
            respuesta = await asyncio.wait_for(
                client.post(URL_MICROSERVICIO, json={"datos": consulta.vector_estado}),
                timeout=3.0
            )
            return respuesta.json()
    except asyncio.TimeoutError:
        # Si la IA tarda más de 3 segundos, retorna un error 503 controlado
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agente Tutor congestionado. Continúe la simulación clínica con reglas base."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de red hacia el microservicio IA."
        )

# IO3: Guardado de telemetría sin latencia
@router.post("/api/telemetria/guardar")
async def guardar_telemetria(telemetria: Telemetria, background_tasks: BackgroundTasks):
    """
    Retorna una respuesta HTTPS 200 inmediata al navegador web,
    pero procesa el guardado en base de datos en un hilo de fondo (BackgroundTasks).
    """
    background_tasks.add_task(registrar_telemetria_db, telemetria)
    return {"mensaje": "Métricas de telemetría enviadas a procesamiento asíncrono."}
