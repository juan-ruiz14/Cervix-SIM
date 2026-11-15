# Gestión de Riesgos del Proyecto (PMBOK)

La gestión de riesgos de **Cérvix-SIM** sigue los procesos establecidos en la **Guía del PMBOK** (identificación, análisis cualitativo, planificación de respuestas y monitoreo), abordando tanto los riesgos técnicos de arquitectura e Inteligencia Artificial como los riesgos metodológicos y éticos propios de un simulador académico.

---

## 1. Categorización de Riesgos (RBS)

Los riesgos del proyecto se clasifican en cuatro categorías principales:
1. **Técnicos y de Arquitectura:** Disponibilidad del modelo de IA (Ollama), persistencia de datos, tiempos de respuesta y portabilidad de entornos.
2. **Metodológicos y Académicos:** Validez clínica de los casos sintéticos y definición operativa de las métricas experimentales (AOR y calibración).
3. **Seguridad, Privacidad y Ética:** Confidencialidad de la respuesta correcta durante la sesión, anonimización de participantes y uso exclusivamente educativo.
4. **Gestión y Colaboración:** Control de versiones en equipo, integración de módulos y cumplimiento del cronograma por cortes.

---

## 2. Matriz de Riesgos y Plan de Respuesta

| ID | Riesgo Identificado | Categoría | Prob. | Impacto | Estrategia PMBOK | Plan de Respuesta y Control Implementado |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **R-01** | **Latencia alta o caída del Agente Tutor IA (Ollama)** durante una sesión activa. | Técnica | Media | Alto | **Mitigar** | Implementación de un límite de espera (*timeout*) de **10 segundos** en `tutor.py` con degradación controlada hacia un texto de respaldo, además de un modo simulado (`TUTOR_MODE=mock`) para operación sin GPU. |
| **R-02** | **Inconsistencia clínica en casos sintéticos o ambigüedad en la fórmula del AOR** antes del estudio piloto. | Metodológica | Media | Alto | **Mitigar** | Validación estructural automática mediante `validate_cases.py` y revisión obligatoria del banco de casos (`cases.json`) y de la definición operativa del AOR con el docente antes de aplicar pruebas con estudiantes. |
| **R-03** | **Filtración de la referencia docente al navegador** antes de que el participante tome su decisión. | Seguridad Experimental | Baja | Muy Alto | **Evitar** | El backend actúa como único intermediario y retiene la respuesta correcta y la condición de exactitud de la sugerencia IA hasta recibir la confirmación en `POST /api/sessions/{id}/decision`. |
| **R-04** | **Pérdida de datos de sesiones al reiniciar el servidor** si se ejecuta sin base de datos externa. | Técnica | Media | Medio | **Mitigar** | Arquitectura de almacenamiento desacoplada (`store.py`) que permite usar memoria volátil en desarrollo y conectar **MongoDB Atlas** en producción mediante la variable `MONGODB_URI`. |
| **R-05** | **Incompatibilidades de entorno o fallos en contenedores** (`Dockerfile` / `docker-compose.yml` no probados en desarrollo). | Despliegue | Media | Medio | **Mitigar** | Separación estricta entre lógica de dominio y framework web (Starlette + JS puro), permitiendo despliegue directo sin contenedores en **Render** (backend) y **Vercel / GitHub Pages** (frontend). |
| **R-06** | **Uso indebido como herramienta de diagnóstico médico real** o vinculación de identidad personal con resultados. | Ética y Privacidad | Baja | Muy Alto | **Evitar** | Despliegue obligatorio de advertencias legales (`GET /api/legal`), uso exclusivo de esquemas sintéticos y asignación de identificadores seudónimos desacoplados de los datos de contacto. |
| **R-07** | **Conflictos de código o sobrescritura de avances** entre los integrantes del equipo en GitHub. | Gestión | Media | Medio | **Mitigar** | Trabajo aislado por ramas funcionales (`Backend`, `IA`, `Frontend`, documentación), integración controlada mediante *Pull Requests* y verificación por flujo de CI (`.github/workflows/ci.yml`). |

---

## 3. Monitoreo y Trazabilidad de Entregables (PMBOK)

El seguimiento de los riesgos y el control del proyecto se respaldan en los artefactos formales generados durante los cortes académicos del repositorio:

### Corte 1 — Inicio y Planificación (`Corte_1/`)
* **Acta de Constitución del Proyecto:** Formalización del alcance inicial, objetivos, restricciones y criterios de éxito.
* **Plan de Gestión del Alcance y EDT/WBS:** Desglose estructurado de entregables técnicos y documentales para evitar desviaciones (*scope creep*).
* **Plan de Gestión del Cronograma:** Definición de hitos y secuencia de actividades por fase.
* **Ingeniería de Requisitos:** Priorización mediante **Matriz MoSCoW** y control de cumplimiento en la **Matriz de Trazabilidad de Requisitos**.
* **Modelado Base:** Diagramas de Casos de Uso y Modelo Entidad-Relación (ER).

### Corte 2 — Calidad, Arquitectura y Diseño (`Corte_2/` y `docs/`)
* **Plan de Gestión de Calidad:** Definición de métricas de proceso, compuertas de pruebas y criterios de aceptación.
* **Arquitectura del Sistema y del Software:** Documentación de decisiones técnicas, patrones aplicados y mecanismos de tolerancia a fallos.
* **Diseño Detallado:** Especificación de componentes de software y estructura de persistencia de datos.
* **Control de Cronograma:** Seguimiento actualizado del avance físico y documental del proyecto.
