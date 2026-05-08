# Comparativa de Proyectos PrismaHR (Versiones 4, 5 y 6)

Este documento detalla las diferencias arquitectónicas y funcionales entre las versiones 4, 5 y 6 del motor de análisis PrismaHR, así como el uso de la Inteligencia Artificial Generativa y la implementación del JSON de entrada con `frases_predeterminadas`.

## 1. Evolución y Diferencias entre Versiones

La evolución de estos proyectos demuestra una transición de un script monolítico hacia una arquitectura de software robusta, modular y de alto rendimiento.

### Proyecto 4 (PrismaHR v2)
- **Estructura:** Arquitectura monolítica. Toda la lógica de negocio, las llamadas a la IA y la generación de PDF residen en un solo archivo principal (`motor_prisma.py`).
- **Rendimiento:** Ejecución secuencial. Llama a la IA para cada bloque de texto uno por uno, lo que hace el procesamiento más lento.
- **Salida:** Genera únicamente un **PDF de 2 páginas** por candidato utilizando HTML, Jinja2 y Playwright con un gráfico radar incrustado.
- **Entrada de Datos:** Transición inicial de Excel a un formato JSON estático.

### Proyecto 5 (PrismaHR Pro)
*El mayor salto cualitativo en la arquitectura del sistema.*
- **Estructura:** Código refactorizado y altamente modular (carpeta `src/`). Se separan responsabilidades: modelos de datos, orquestador (`main.py`), cliente de IA (`ai_client.py`), y generadores de contenido (`content_generator.py`).
- **Rendimiento (Velocidad x6):** Introduce **concurrencia asíncrona** (`asyncio.gather()`). Lanza las 6 llamadas a la API de la IA simultáneamente, reduciendo el tiempo de generación de ~12 segundos a solo ~2 segundos por candidato.
- **Salida Mejorada:** Además del PDF, genera:
  - **Excels Individuales:** Dashboards interactivos y analíticos para cada candidato.
  - **Excel Consolidado:** Un archivo maestro de todo el equipo con rankings, comparativas y mapas de calor (generados con Matplotlib).
- **Validación Estricta:** Implementa `Pydantic v2` para tipado estricto y validación automática del JSON de entrada.

### Proyecto 6 (PrismaHR Refactor)
- **Estructura:** Mantiene la potente arquitectura modular del Proyecto 5.
- **Novedades:** Incluye herramientas auxiliares como `generar_plantilla.py` y archivos base como `plantilla_excel.xlsx` para facilitar la creación dinámica de las plantillas de Excel, apuntando a una mayor personalización corporativa.
- **Refinamiento:** Mayor estabilidad en el motor principal y preparación para escalabilidad de nuevos módulos.

---

## 2. Uso de la Inteligencia Artificial Generativa

El sistema utiliza la API de **Groq** (con el modelo rápido `llama-3.3-70b-versatile`) como su motor narrativo. Mientras que el código Python realiza los cálculos matemáticos duros (compatibilidad, percentiles, diferencias frente al perfil objetivo), la IA se encarga de **transformar esos números fríos en un informe cualitativo y narrativo**.

Para cada candidato, la IA genera dinámicamente **6 bloques de contenido**:

1. **3 Bloques Narrativos Principales:** Análisis detallado de sus Fortalezas, su perfil de Liderazgo y un Veredicto Final elaborado.
2. **Justificación Descriptiva:** Un resumen narrativo que defiende el porqué del dictamen automático (ej: por qué merece una Promoción vs. un Plan de Mejora).
3. **Fortalezas Clave:** Extracción de los 3 puntos fuertes más destacables del candidato.
4. **Puntos Críticos:** Identificación de 2 debilidades clave a vigilar, redactadas como alertas constructivas.
5. **Catalizadores de Crecimiento:** Identificación de 2 áreas donde el candidato tiene mayor potencial de mejora inmediata.
6. **Alerta de Riesgo:** Evaluación predictiva de riesgos silenciosos en RRHH, como el síndrome de *burnout* o el riesgo de fuga de talento.

---

## 3. Integración de `frases_predeterminadas` y Próximos Pasos

Tu propuesta de estructurar el JSON con `frases_predeterminadas` es totalmente compatible. De hecho, **la arquitectura de los Proyectos 5 y 6 ya incorpora esta estructura de datos exacta**.

### Estado Actual:
El modelo de datos ya admite el campo:
```json
"frases_predeterminadas": ["Lideró proyecto X"]
```
Actualmente, el sistema toma estas frases y se las añade al contexto final de la petición (prompt) a la IA indicándole: *"Comentarios Evaluación: Lideró proyecto X"*.

### La Idea de "Expansión e Invención":
Para lograr que la IA no solo repita la frase, sino que **desarrolle un storytelling corporativo inventando aportaciones que encajen perfectamente en los recuadros de la plantilla HTML**, la solución es sencilla y elegante:

**Modificación requerida (en `src/content_generator.py`):**
Se debe enriquecer el *Prompt* del sistema para la IA con una directiva específica, por ejemplo:
> *"A partir de la siguiente frase predeterminada proporcionada ('Lideró proyecto X'), actúa como un experto en Recursos Humanos y expande creativamente esta información. Inventa un contexto corporativo realista y detalla aportaciones de valor que justifiquen esta frase. Redacta el resultado con un tono ejecutivo y persuasivo, asegurándote de que el texto final tenga la longitud y estructura perfectas para rellenar los recuadros visuales de nuestra plantilla HTML."*

Esta pequeña modificación en el prompt del Proyecto 6 es suficiente para desbloquear todo el potencial de generación expansiva que buscas para tus plantillas.
