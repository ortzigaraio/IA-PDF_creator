# Decisiones técnicas (ADR) · PrismaHR v7

Registro de las decisiones de arquitectura y su porqué. Sustituye al ADR del proyecto 6.

## 1. Las reglas deciden, la IA redacta

**Antes (v6):** 6 llamadas a la IA por persona con texto libre. La IA decidía el nivel de riesgo y elegía fortalezas y puntos críticos. La llamada de "fortalezas" ni siquiera recibía los datos de la persona.

**Ahora:** `scoring.py` calcula compatibilidad, veredicto, riesgo, fortalezas y áreas de mejora con reglas fijas y probadas. La IA recibe esas conclusiones y solo las redacta.

**Por qué:**
- Resultados reproducibles y explicables: la misma entrada da siempre el mismo veredicto.
- Cumplimiento: el Reglamento Europeo de IA (sistemas de alto riesgo en el ámbito laboral) y el RGPD (art. 22) exigen transparencia y supervisión humana.
- Se puede auditar: cada informe deja un JSON en `salida/auditoria/`.

## 2. Una llamada con salida estructurada

**Antes:** 6 peticiones con texto libre que luego se troceaban con `###` o por saltos de línea, de forma frágil.

**Ahora:** 1 petición por persona que devuelve un objeto `Narrativa` validado con Pydantic. Si no es válido, se reintenta; si la IA falla, se usan textos de plantilla y el lote no se detiene.

**Por qué:** menos coste y latencia, textos coherentes entre secciones (los escribe una sola respuesta) y nada de parseo frágil.

## 3. Multiproveedor

Una interfaz común (`prismahr/llm/base.py`) con cuatro implementaciones sobre los SDK oficiales (Groq, Anthropic, OpenAI, Gemini) y un modo `plantillas` sin IA. Se cambia con una variable del `.env`.

**Por qué:** evita depender de un solo proveedor y permite elegir por coste, calidad o ubicación de los datos.

## 4. Minimización de datos personales

La IA nunca recibe el nombre real: se sustituye por `[NOMBRE]`, también dentro de las observaciones del evaluador, y se repone al final.

**Limitación:** si las observaciones mencionan a otras personas o datos identificativos, esos sí se envían. Hay que redactarlas pensando en ello.

## 5. PDF: Jinja2 + Chromium (Playwright), sin dependencias de internet

**Antes:** la plantilla cargaba Tailwind y Google Fonts desde internet en cada PDF, e insertaba el texto de la IA sin escapar (`|safe`).

**Ahora:** CSS propio y fuentes del sistema, y autoescape activado.

**Alternativas valoradas:** WeasyPrint o Typst son más ligeros y no necesitan navegador, pero obligarían a rehacer el diseño. Chromium se mantiene porque el diseño ya existe y el resultado es fiel.

## 6. Salidas

Se mantienen el PDF individual y el Excel consolidado. El Excel individual se elimina por decisión del producto. La plantilla `plantilla_excel.xlsx` de la v6 nunca llegó a usarse en el código y también se elimina.

## 7. Estructura

```
prismahr/            paquete principal
  config.py          configuración (.env)
  models.py          validación de entrada y modelos de salida
  scoring.py         reglas de negocio (sin IA)
  narrativa.py       redacción: prompt, seudónimos, respaldo
  llm/               proveedores de IA
  charts.py          gráficos (matplotlib)
  pdf.py             PDF individual
  excel_consolidado.py
  pipeline.py        orquestación concurrente
templates/informe.html
datos/ejemplo.json   datos ficticios
tests/
```

## Pendiente de decidir

- **Fórmula de compatibilidad.** Se mantiene la fórmula heredada, `100 − media(|diferencia|)`, que tiene dos efectos:
  1. Superar el objetivo también resta puntos.
  2. Es muy generosa: con una desviación media de unos 26 puntos todavía sale "Formación técnica recomendada".

  Habría que recalibrarla, por ejemplo penalizando solo lo que queda por debajo del objetivo y ponderando por el peso de cada dimensión, y ajustar los umbrales.
