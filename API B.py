from fastapi import FastAPI, BackgroundTasks, HTTPException, status
from pydantic import BaseModel
import asyncio
import httpx
from database.connection import db_instance

app = FastAPI(title="Cérvix-SIM API Principal", version="1.0")

# Modelos JSON
class ConsultaIA(BaseModel):
    vector_estado: dict

class Telemetria(BaseModel):
    aor_metrica: float
    sus_score: int
    id_sesion: str

# Patrón Observer: Ejecución asíncrona en segundo plano
async def registrar_telemetria_db(datos: Telemetria):
    conn = db_instance.get_connection()
    await asyncio.sleep(0.1) # Simula escritura rápida (< 0.5s)
    print(f"[Observer] Telemetría guardada en DB: {datos.id_sesion}")

@app.get("/api/salud")
async def estado_servicio():
    # Endpoint para despertar el servidor en Render Cloud
    return {"status": "listo", "bd_status": db_instance.get_connection()}

@app.post("/api/tutor/evaluar")
async def consultar_tutor(consulta: ConsultaIA):
    try:
        # Llamada al microservicio IA segregado con Timeout estricto de 3s
        async with httpx.AsyncClient() as client:
            respuesta = await asyncio.wait_for(
                client.post("http://localhost:8001/ia/generar", json={"datos": consulta.vector_estado}),
                timeout=3.0
            )
            return respuesta.json()
    except asyncio.TimeoutError:
        # Degradación Controlada: El examen no se bloquea si la IA falla
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tutor IA inactivo. Continúe con las reglas base del simulador."
        )

@app.post("/api/telemetria/guardar")
async def guardar_telemetria(telemetria: Telemetria, bg_tasks: BackgroundTasks):
    # Delega la escritura a un hilo secundario (Observer)
    bg_tasks.add_task(registrar_telemetria_db, telemetria)
    return {"mensaje": "Telemetría procesada sin bloquear interfaz gráfica."}
