from fastapi import FastAPI, BackgroundTasks, HTTPException, status
from pydantic import BaseModel
import asyncio
import time

# Inicialización de la aplicación FastAPI (Capa de Lógica de Negocio)
app = FastAPI(
    title="Cérvix-SIM API",
    description="Backend de simulación gamificada y telemetría AOR/SUS",
    version="1.0"
)

# ---------------------------------------------------------
# MODELOS DE DATOS (Pydantic para validación de JSON)
# ---------------------------------------------------------
class AccionClinica(BaseModel):
    id_accion: str
    parametros_caso: dict
    tiempo_respuesta_ms: int

class ConsultaIA(BaseModel):
    vector_estado: dict

class Telemetria(BaseModel):
    aor_metrica: float
    sus_score: int
    id_sesion: str

# ---------------------------------------------------------
# SIMULACIÓN DE CONEXIONES SINGLETON (Base de Datos e IA)
# ---------------------------------------------------------
# En la implementación real, aquí se instancia el patrón Singleton 
# para PostgreSQL y el cliente HTTP del microservicio IA.

async def escribir_bd_asincrono(datos_telemetria: Telemetria):
    """
    Simula el patrón Observer: Escritura en DB en segundo plano.
    Garantiza que la latencia de escritura sea < 0.5 segundos.
    """
    # Lógica de inserción en PostgreSQL (SQLAlchemy o asyncpg)
    await asyncio.sleep(0.1) # Simulación de tiempo de escritura
    print(f"[Observer] Telemetría guardada exitosamente: {datos_telemetria.id_sesion}")

async def invocar_microservicio_ia(datos: dict):
    """
    Simula la llamada al microservicio externo del Tutor IA (Llama 3).
    """
    # Aquí iría el httpx.AsyncClient llamando a la API de IA
    await asyncio.sleep(1.5)  # Simula el procesamiento del LLM
    return {"sugerencia": "Se recomienda realizar colposcopia debido a hallazgos anormales."}

# ---------------------------------------------------------
# ENDPOINTS (Interfaces Externas IO1, IO2, IO3, IO4)
# ---------------------------------------------------------

# IO4: Estado del servicio (Mitigación de Riesgo R1 - Despertar nube gratuita)
@app.get("/api/salud", status_code=status.HTTP_200_OK)
async def estado_servicio():
    return {"status": "listo", "message": "Servidor Cérvix-SIM activo"}

# IO1: Enviar acción clínica
@app.post("/api/simulacion/accion", status_code=status.HTTP_200_OK)
async def registrar_accion(accion: AccionClinica):
    # Aquí se aplicaría el Patrón Factory Method para validar reglas del caso
    return {
        "status_simulacion": "actualizado",
        "regla_valida": True,
        "retroalimentacion": "Acción registrada en el motor."
    }

# IO2: Consultar Tutor IA (Degradación Controlada)
@app.post("/api/tutor/evaluar")
async def consultar_tutor(consulta: ConsultaIA):
    try:
        # Se impone el timeout estricto de 3.0 segundos exigido en la arquitectura
        resultado_ia = await asyncio.wait_for(
            invocar_microservicio_ia(consulta.vector_estado), 
            timeout=3.0
        )
        return resultado_ia
    except asyncio.TimeoutError:
        # Falla controlada si la IA tarda demasiado o se cae (Error 503)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tutor IA no disponible temporalmente. Continúe con las reglas base."
        )

# IO3: Registrar telemetría (Patrón Observer Asíncrono)
@app.post("/api/telemetria/guardar", status_code=status.HTTP_200_OK)
async def guardar_telemetria(telemetria: Telemetria, background_tasks: BackgroundTasks):
    # Delega la tarea a un hilo secundario (BackgroundTasks) para no bloquear la interfaz 3D
    background_tasks.add_task(escribir_bd_asincrono, telemetria)
    return {"message": "Registro de telemetría enviado a segundo plano."}
