# Gestión de Riesgos (PMBOK)

## Gestión de Riesgos del Proyecto&#x20;

Siguiendo los lineamientos del **PMBOK (6ta Edición)**, el equipo identificó y asignó responsables para los riesgos críticos que podrían comprometer la viabilidad técnica o financiera de **Cérvix-SIM**.

***

### Matriz de Riesgos Técnicos

| ID       | Riesgo Identificado                                  | Causa Raíz                                                                                                                           | Impacto                                | Responsable                                  | Plan de Mitigación                                                                                                                                   |
| -------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------- | -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **R-01** | **Agotamiento de cuota en servicios gratuitos**      | Carga de imágenes médicas de alta resolución que exceden los límites de almacenamiento o transferencia de la capa gratuita ($0 COP). | **Alto** (Caída o bloqueo del sistema) | **Juan Pablo Ruiz** _(Analista de Sistemas)_ | Implementar un protocolo obligatorio de **compresión y optimización automática de imágenes** previo a su almacenamiento y despliegue en el servidor. |
| **R-02** | **Sesgo o alucinación no controlada en el Tutor IA** | Respuestas imprecisas del modelo frente a casos clínicos complejos.                                                                  | **Medio**                              | **Daniel Rodríguez** _(Desarrollador)_       | Diseño de _prompts_ estructurados con contexto clínico controlado y validación previa de escenarios.                                                 |
| **R-03** | **Desviación en tiempos de entrega**                 | Subestimación del esfuerzo en análisis o desarrollo.                                                                                 | **Alto**                               | **Juan David Uribe** _(Director)_            | Seguimiento semanal mediante **Trello** y control cuantitativo de horas en **Process Dashboard (TSP)**.                                              |
