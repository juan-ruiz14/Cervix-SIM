# Especificación de Requisitos de Software (ISO/IEC/IEEE 29148)

Este documento resume los requisitos funcionales, no funcionales y restricciones del sistema **Cérvix-SIM**, trazados con la Matriz MoSCoW y los Casos de Uso del proyecto.

## 1. Actores del Sistema
* **Participante (Estudiante):** Realiza el flujo completo de simulación, interactúa con el visor 3D, consulta al tutor IA, emite su diagnóstico y responde la encuesta SUS.
* **Docente / Investigador:** Consulta los indicadores agregados de calibración de confianza, índice AOR y usabilidad mediante el endpoint administrativo protegido.
* **Agente Tutor IA (Ollama / Mock):** Provee recomendaciones textuales contextualizadas al escenario clínico sin exponer directamente la etiqueta docente.

## 2. Requisitos Funcionales (RF)

| ID | Requisito | Prioridad (MoSCoW) | Descripción |
| :--- | :--- | :--- | :--- |
| **RF-01** | Gestión de Sesión Seudónima | Must Have | El sistema debe permitir iniciar una sesión previa aceptación del aviso legal, generando un identificador seudónimo único sin vincular datos personales al historial clínico simulado. |
| **RF-02** | Visualización de Escenario 3D | Must Have | El sistema debe cargar un caso sintético desde el banco validado y permitir su exploración interactiva en el visor 3D (`model3d.js`). |
| **RF-03** | Consulta al Agente Tutor IA | Must Have | El participante podrá solicitar asistencia al tutor IA durante la evaluación del caso, recibiendo una sugerencia controlada por el backend. |
| **RF-04** | Registro de Decisión y Confianza | Must Have | El sistema debe registrar el diagnóstico seleccionado por el usuario y su porcentaje/nivel de confianza antes de liberar la retroalimentación docente. |
| **RF-05** | Retroalimentación y Encuesta SUS | Should Have | Tras decidir, el sistema mostrará la comparación entre la decisión del estudiante, la sugerencia de la IA y la referencia docente, habilitando el cuestionario SUS. |
| **RF-06** | Resumen Agregado Docente | Should Have | El sistema debe exponer un resumen estadístico de sesiones, precisión, calibración y AOR autenticado mediante `X-Admin-Token`. |

## 3. Requisitos No Funcionales (RNF)
* **RNF-01 (Seguridad e Integridad Experimental):** Ningún payload enviado al cliente antes de `POST /api/sessions/{id}/decision` debe contener la respuesta correcta del caso.
* **RNF-02 (Disponibilidad y Tolerancia a Fallos):** El tiempo máximo de espera del Agente Tutor IA es de **10 segundos**; superado ese umbral, se activará una respuesta de respaldo (*fallback*).
* **RNF-03 (Portabilidad y Despliegue):** El backend debe operar en Python 3.10+ con soporte para persistencia en memoria o MongoDB Atlas, y empaquetado mediante Docker.
* **RNF-04 (Cumplimiento Ético):** La interfaz debe mostrar de forma visible la advertencia de uso exclusivamente académico y con datos sintéticos.
