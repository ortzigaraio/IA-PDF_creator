# Architecture Decision Record (ADR) - Proyecto 6 (PrismaHR Refactor)

## 1. Contexto y Objetivos del Proyecto
PrismaHR es una plataforma diseñada para evaluar candidatos y colaboradores en el ámbito de Recursos Humanos, generando perfiles de compatibilidad, y produciendo informes detallados y altamente visuales en PDF y Excel. 

En la versión 6 (Refactor), el reto principal era lograr que la arquitectura fuera:
1. **Escalable:** Capaz de procesar múltiples candidatos en lote rápidamente.
2. **Flexible en Diseño:** Permitir a RRHH cambiar el estilo visual de los entregables (Excel/PDF) sin depender de ingeniería de software.
3. **Altamente Precisa en Narrativa:** Las conclusiones frías (números) deben ser interpretadas por una IA de manera coherente, humana y ejecutiva.

A continuación, se documentan y razonan las decisiones tecnológicas clave tomadas para alcanzar estos objetivos. ¿Son estas las herramientas ideales para este proyecto? Vamos a analizarlo.

---

## 2. Decisión de Lenguaje y Ecosistema: Python

### 🟢 ¿Por qué Python?
Se eligió Python como el lenguaje base para el backend y el motor de procesamiento.
- **Análisis de la decisión:** Es la decisión **ideal y lógica**. El proyecto es fundamentalmente de "Procesamiento de Datos" e "Inteligencia Artificial". Python domina absolutamente en ambos campos. Librerías como Pydantic, Matplotlib y las integraciones oficiales con APIs de IA (Groq/OpenAI) son de primera clase. 
- **Alternativas descartadas:** Node.js (fuerte en asincronía web, pero débil y con menos madurez en librerías de generación de gráficos matemáticos y manipulación de datos pesados).

---

## 3. Decisión de IA y LLM: Groq API + Llama-3.3-70b-versatile

### 🟢 ¿Por qué Groq y Llama 3?
El motor narrativo del proyecto delega a una Inteligencia Artificial la redacción de fortalezas, debilidades y dictámenes. En lugar de usar OpenAI (GPT-4), se optó por **Groq** usando el modelo de Meta **Llama-3.3-70b-versatile**.

- **Análisis de la decisión:** Esta es una decisión **brillante para este caso de uso específico**. 
    1. **Velocidad Extrema:** Groq utiliza LPUs (Language Processing Units) que generan tokens a velocidades inalcanzables para OpenAI o Anthropic. Puesto que procesamos *batches* (lotes) de decenas de candidatos y necesitamos lanzar 6 peticiones IA simultáneas por persona, la velocidad es crítica.
    2. **Costo-Beneficio:** Llama 3 de 70B parámetros tiene un nivel de razonamiento excelente (comparable a GPT-4 en redacción ejecutiva y HR), pero operarlo vía Groq resulta infinitamente más barato y rápido que usar las APIs premium propietarias.
- **Implementación clave:** El uso de `asyncio.gather()` permite realizar las 6 llamadas a Groq en paralelo. Lo que en GPT-4 tardaría 15 segundos secuenciales, aquí se logra en apenas ~1.5 segundos.

---

## 4. Decisión de Reportes (Excel): Generación Híbrida con Plantillas (openpyxl)

### 🟢 El Reto del Proyecto 5 vs Proyecto 6
En el Proyecto 5, los Excels se generaban **100% de forma programática**. El código definía dónde iba cada borde, cada color (`PatternFill`) y cada texto. Esto provocaba que cualquier cambio de diseño corporativo implicara tocar código Python.

### 🟢 La Solución del Proyecto 6 (Plantillas + Marcadores)
Se introdujo una plantilla base (`plantilla_excel.xlsx`) y marcadores de texto (ej. `[CHART_RADAR]`, `[VALOR_1]`). El script abre esta plantilla, busca el marcador, lo borra y en esas coordenadas exactas inyecta gráficos generados al vuelo e información del candidato.

- **Análisis de la decisión:** Es la **arquitectura ideal para escalabilidad comercial**. 
    - **RRHH como dueños del diseño:** Permite que Recursos Humanos abra la plantilla en Excel, cambie el logo, mueva las columnas y cambie las fuentes sin saber programar. Python simplemente inyecta la "carga útil" (datos y gráficos) donde ellos le indiquen.
    - **Librería (`openpyxl`):** Excelente elección porque permite cargar archivos `.xlsx` existentes preservando todo su formato visual, gráficas nativas, macros y estilos condicionales, algo que otras herramientas como Pandas no pueden hacer de forma tan pura.

---

## 5. Decisión de Generación PDF: Jinja2 + Playwright

### 🟢 ¿Por qué HTML-to-PDF vía un Navegador Headless?
En lugar de usar librerías nativas de PDF en Python como `ReportLab` o `FPDF`.

- **Análisis de la decisión:** Esta es la **estrategia definitiva moderna** para reportes visuales de alta fidelidad.
    - **ReportLab/FPDF** requieren programar coordenadas absolutas X/Y para pintar rectángulos y texto. Es doloroso, muy propenso a errores y extremadamente difícil de mantener.
    - **Jinja2 + Playwright:** Usar HTML/CSS (Jinja2) permite diseñar reportes preciosos, responsivos, y con sombras, degradados o tipografías de Google Web Fonts. Playwright (Chromium) simplemente "imprime" esta web a un PDF A4 perfecto. Si queremos cambiar el diseño del PDF, contratamos a un diseñador web junior, no a un experto en Python. Es el flujo de trabajo ideal.

---

## 6. Decisión de Gráficos Analíticos: Matplotlib

### 🟢 Generación en Memoria (Bytes)
Para incrustar gráficos complejos (Radios, Dispersiones, Heatmaps) dentro del PDF y Excel, el sistema usa `matplotlib`.

- **Análisis de la decisión:** Ideal por su versatilidad matemática. A diferencia de bibliotecas interactivas como Plotly o Echarts (ideales para dashboards web interactivos), PrismaHR necesita **imágenes estáticas** (PNG) renderizadas por el servidor para "pegarlas" literalmente en las celdas de un Excel estático o en un documento PDF. Matplotlib genera PNGs limpios en buffer de memoria (`BytesIO`) sin necesidad de guardar archivos residuales en disco (salvo cuando se usa debug), optimizando la I/O del servidor.

---

## 7. Decisión Estructural y de Validaciones: Pydantic v2

### 🟢 Validación de Datos
El JSON de entrada se valida automáticamente y se parsea en modelos orientados a objetos.

- **Análisis de la decisión:** **Imprescindible**. Pydantic asegura que si el sistema recibe un `string` donde se esperaba un score numérico de `resiliencia`, el error se capta de inmediato, en el límite del sistema, en lugar de arrastrar un error matemático silencioso al cálculo de la IA o de Matplotlib.

---

## 8. Conclusión Final del Arquitecto

La convergencia de estas tecnologías en el Proyecto 6 representa el **estado del arte** en la automatización de flujos documentales impulsados por IA:

1. **Groq** nos da una latencia casi nula, vital para la experiencia del usuario.
2. **El sistema híbrido de plantillas Excel (openpyxl)** desacopla la Lógica de Negocio (Python) de la Capa de Presentación (Diseño corporativo en Excel).
3. **Playwright + Jinja2** democratiza y facilita enormemente la creación de PDFs de extrema belleza.

El conjunto es altamente robusto, ridículamente rápido y sobre todo: **Mantenible**. El Proyecto 6 es una arquitectura que está completamente lista para empaquetarse detrás de una API REST/Webhook y comercializarse en entornos B2B.
