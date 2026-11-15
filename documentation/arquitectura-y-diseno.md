# Arquitectura y Diseño

## Arquitectura y Diseño del Sistema&#x20;

> **Nota de Fase:** El modelo web de Cérvix-SIM se encuentra actualmente en etapa de **diseño arquitectónico**. La implementación de código fuente permanece en el _Backlog_ a la espera del cierre formal de validación documental.

***

### Estructura Lógica de Componentes

La solución está diseñada bajo una arquitectura desacoplada para facilitar el mantenimiento y el cumplimiento de la restricción de costo cero:

1. **Capa de Presentación (Frontend Web):**
   * Interfaz interactiva y entorno visual gamificado.
   * Responsable de renderizar los casos clínicos y capturar las interacciones del usuario.
2. **Capa de Lógica y Simulación (Backend / Microservicios):**
   * Gestiona el flujo de los escenarios, el puntaje gamificado y el cálculo en tiempo real de las métricas de **Sesgo de Automatización (AOR)**.
3. **Módulo de Inteligencia Artificial (Agente Tutor):**
   * Conexión vía API hacia un modelo de lenguaje/visión encargado de generar la asistencia pedagógica y las sugerencias diagnósticas simuladas.
4. **Capa de Datos (Repositorio Clínico Anonimizado):**
   * Almacenamiento ligero de los casos de estudio, imágenes comprimidas y registros anónimos de desempeño.

***

### Diagramas del Sistema

_(Espacio reservado para insertar los diagramas de Casos de Uso, Arquitectura de Microservicios y Flujo de Datos aprobados por el equipo)._
