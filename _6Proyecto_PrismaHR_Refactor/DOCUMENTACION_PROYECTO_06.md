# PrismaHR Refactor — Documentación Técnica del Proyecto 06

## 1. Objetivo del Proyecto

**PrismaHR Pro** es un sistema de evaluación de compatibilidad laboral impulsado por IA que genera informes técnicos detallados en **PDF** y **Excel** para procesos de Recursos Humanos.

### Propósito Principal
Analizar el perfil de candidatos o colaboradores comparando sus competencias contra el perfil objetivo definido por cada empresa, produciendo un dictamen ejecutivo con recomendaciones personalizadas.

### 7 Dimensiones Evaluadas
| Dimensión | Descripción |
|-----------|-------------|
| Adaptabilidad | Capacidad de ajustarse a cambios |
| Comunicación | Habilidades comunicativas |
| Creatividad | Capacidad de innovación |
| Disciplina | Autocontrol y orden |
| Empatía | Inteligencia interpersonal |
| Iniciativa | Proactividad laboral |
| Resiliencia | Gestión del estrés |

---

## 2. Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                      motor_prisma.py                            │
│                  (Punto de entrada)                             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PrismaEngine                                 │
│            Motor central que orquesta el flujo                  │
└──────────┬──────────────┬──────────────┬──────────────────────┘
           │              │              │
           ▼              ▼              ▼
┌─────────────────┐ ┌───────────┐ ┌──────────────────────────┐
│  AI Client      │ │ Processor │ │ Content Generator        │
│  (Groq API)     │ │ (Lógica)  │ │ (6 prompts asíncronos)   │
└────────┬────────┘ └─────┬─────┘ └──────────┬───────────────┘
         │                 │                   │
         ▼                 ▼                   ▼
┌─────────────────┐ ┌───────────┐ ┌──────────────────────────┐
│ PDF Generator   │ │ Excel     │ │ Charts                    │
│ (Jinja2+Play)   │ │ Templates │ │ (Matplotlib PNG bytes)   │
│                 │ │ +Consolid │ │                          │
└─────────────────┘ └───────────┘ └──────────────────────────┘
```

---

## 3. Lógica del Código — Módulo por Módulo

### 3.1 Configuración (`config.py`)
Gestiona variables de entorno con **Pydantic Settings**:
- `GROQ_API_KEY`: Clave de API de Groq
- `GROQ_MODEL`: Modelo LLM (default: `llama-3.3-70b-versatile`)
- `OUTPUT_EXCEL_DIR`: Directorio de salida Excel
- `OUTPUT_PDF_DIR`: Directorio de salida PDF

### 3.2 Modelos de Datos (`models.py`)
Usa **Pydantic v2** para validación:
- `DimensionesModel`: Scores 0-100 por dimensión con aliases para tildes
- `UsuarioModel`: Perfil completo del candidato
- `EmpresaInfo`: Configuración de empresa y perfil objetivo
- `ContenidoModel`: Contenido generado por IA
- `ResultadoModel`: Resultado final del procesamiento

### 3.3 Procesador (`processor.py`)
Contiene la **lógica de negocio pura**:

#### Fórmula de Compatibilidad
```
Compatibilidad = 100 - (Promedio_Diferencias × 10)
```

Donde:
- Valores usuario: escala 0-100 → normalizados a 0-1
- Pesos objetivo: escala 0-10 → multiplicados por 10
- Diferencia = |Valor_Usuario - Valor_Objetivo|

#### Decisión de Veredicto
| Rango | Veredicto |
|-------|-----------|
| ≥85% | PROMOCIÓN DIRECTA |
| 72-84% | FORMACIÓN TÉCNICA RECOMENDADA |
| 55-71% | CONSOLIDACIÓN |
| <55% | PLAN DE MEJORA INMEDIATO |

#### Percentiles Contextuales
Compara cada candidato contra su equipo:
```
Percentil = (candidatos_con_score_menor / total) × 100
```

### 3.4 Cliente IA (`ai_client.py`)
Wrapper sobre Groq SDK con:
- **Retry automático**: hasta 3 intentos con backoff exponencial
- **Ejecución asíncrona**: usa ThreadPoolExecutor para no bloquear el event loop

### 3.5 Generador de Contenido (`content_generator.py`)
Lanza **6 prompts en paralelo** con `asyncio.gather()`:

1. `_bloques()`: 3 bloques de análisis (Fortalezas, Liderazgo, Veredicto)
2. `_descripcion()`: Justificación breve del dictamen
3. `_fortalezas()`: 3 fortalezas clave
4. `_puntos_criticos()`: 2 puntos de atención
5. `_catalizadores()`: 2 catalizadores de crecimiento
6. `_alerta_riesgo()`: Evaluación de burnout/fuga de talento

### 3.6 Generador PDF (`pdf_generator.py`)
Usa **Jinja2 + Playwright**:
1. Renderiza plantilla HTML con datos inyectados
2. Genera gráfico radar en base64
3. Playwright convierte HTML → PDF (A4)

### 3.7 Gráficos (`charts.py`)
Funciones puras que retornan **bytes PNG**:

| Función | Descripción |
|---------|-------------|
| `radar_bytes()` | Gráfico radar usuario vs objetivo |
| `radar_base64()` | Versión base64 para HTML |
| `barras_comparativas_bytes()` | Barras lado a lado |
| `scatter_prioridades_bytes()` | Matriz de prioridades |
| `coxcomb_bytes()` | Gráfico de áreas polares |
| `gaps_bytes()` | Barras horizontales de gaps |
| `ranking_equipo_bytes()` | Ranking horizontal |
| `heatmap_equipo_bytes()` | Mapa de calor del equipo |

### 3.8 Excel Individual (Sistema Híbrido de Plantillas en V6)
El **Proyecto 6** introduce un gran cambio en la generación de Excels respecto a la V5: el paso de una generación 100% programática a un **sistema híbrido basado en plantillas**.

* **En Proyecto 5**: El código construía el Excel desde cero celda por celda (`src/excel/individual.py`).
* **En Proyecto 6**: Se usa un archivo base (`plantilla_excel.xlsx` generado mediante `generar_plantilla.py`). El script `motor_prisma.py` carga esta plantilla y busca **marcadores de texto dinámicos** (ej. `[CHART_RADAR]`, `[LOGO_EMPRESA]`, `[VAL1]`) para inyectar datos y gráficos (`matplotlib`) generados al vuelo. Esto permite que el área de RRHH o diseño pueda modificar colores y layouts en el Excel sin tocar código Python.

Las 5 hojas principales generadas (o rellenadas desde la plantilla) son:
1. **Dashboard**: KPIs + gráficos embebidos (Radar, Barras, Scatter, Coxcomb).
2. **Radar Comparativo**: Tabla + gráfico radar nativo interactivo.
3. **Análisis de Gaps**: Tabla + gráfico de barras de gaps.
4. **Algoritmo de Cálculo**: Explicación paso a paso de la fórmula.
5. **Fortalezas y Debilidades**: Contenido cualitativo inyectado desde la IA.

### 3.9 Excel Consolidado
Mantiene el reporte maestro del equipo con:
- **Ranking del Equipo**: Ordenado por compatibilidad.
- **Heatmap del Equipo**: Mapa de calor de competencias.

---

## 4. Pipeline del Proyecto — Flujo de Trabajo

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          INICIO: motor_prisma.py                         │
│                    python motor_prisma.py                                │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PASO 1: CARGA DE DATOS                                                   │
│  ├─ Leer JSON con empresas y clientes                                     │
│  └─ Crear directorios de salida                                           │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PASO 2: LANZAR NAVEGADOR (Playwright)                                    │
│  └─ Chromium compartido para todos los PDFs                              │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │   PARA CADA EMPRESA     │
                    └────────────┬────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PASO 3: RECOLECTAR SCORES GLOBALES                                      │
│  └─ Acumular scores por dimensión de todo el equipo                      │
│     (necesario para percentiles contextuales)                            │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │   PARA CADA CLIENTE     │
                    └────────────┬────────────┘
                                 │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────────┐  ┌────────────────────┐  ┌──────────────────────────┐
│ 3A. Parse Usuario │  │ 3B. Calcular       │  │ 3C. Calcular Compatibil. │
│ - ID, Nombre      │  │    Percentiles     │  │ - Extraer features       │
│ - Dimensiones     │  │ (vs equipo local)  │  │ - Comparar vs objetivo   │
│ - Frases predet.  │  │                    │  │ - Fórmula: 100 - diff×10 │
└───────────────────┘  └────────────────────┘  └──────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PASO 4: GENERAR CONTENIDO IA (PARALELO)                                 │
│  └─ 6 llamadas async a Groq simultaneouses                                │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PASO 5: DECIDIR VEREDITO                                                │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────────┐  ┌────────────────────┐  ┌──────────────────────────┐
│  GENERAR PDF      │  │  GENERAR EXCEL     │  │  ACUMULAR EN LISTA       │
│  - Render HTML    │  │  INDIVIDUAL      │  │  (para consolidado)      │
│  - Convertir PDF  │  │  - Cargar Plantilla│  │                          │
│  (Playwright)     │  │  - Reemplazar      │  │                          │
│                   │  │    marcadores      │  │                          │
└───────────────────┘  └────────────────────┘  └──────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │  FIN DE CLIENTES        │
                    └────────────┬────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PASO 6: GENERAR EXCEL CONSOLIDADO                                       │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │  FIN DE EMPRESAS        │
                    └────────────┬────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  FIN: Cerrar navegador, mostrar resumen                                 │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Consideraciones Técnicas y Limitaciones Conocidas

- **Integración de Logos en Excel**: El sistema intenta inyectar dinámicamente el logo de la empresa (`logo_url` del JSON) en la etiqueta `[LOGO_EMPRESA]` del Excel. Es **muy recomendable** alojar estas imágenes en servidores directos (S3, Imgur, hosting propio). Algunas URLs públicas (como las de Wikimedia/Wikipedia) devuelven un error HTTP 400 al intentar descargarlas mediante `urllib`. El sistema captura el error y continúa sin interrumpirse, pero el logo no se renderizará en el Excel.
- **Rutas y Modulos**: En la V6, `motor_prisma.py` actúa como orquestador central y maneja la lógica de plantillas de Excel, reemplazando algunas partes de `src/main.py`.

---

## 6. Archivos del Proyecto

```
_6Proyecto_PrismaHR_Refactor/
├── motor_prisma.py           # Motor principal (V6 Template System)
├── run_batch.py              # Punto de entrada (opcional)
├── servidor_webhook.py       # Servidor para integraciones por Webhook
├── generar_plantilla.py      # Generador de plantillas base de Excel
├── .env                      # Variables de entorno
├── plantilla_radar.html      # Plantilla HTML para PDF
├── plantilla_excel.xlsx      # Plantilla base para Excel corporativo
├── README_SISTEMA.md         # Documentación del sistema general
├── src/                      # Módulos legados / utilidades
│   ├── __init__.py
│   ├── main.py               # PrismaEngine
│   ├── config.py             # Settings (Pydantic)
│   ├── models.py             # Modelos de datos (Pydantic v2)
│   ├── processor.py          # Lógica de negocio
│   ├── ai_client.py          # Cliente Groq con retry
│   ├── content_generator.py  # Generación IA en paralelo
│   ├── pdf_generator.py      # PDF con Jinja2+Playwright
│   ├── charts.py             # Gráficos Matplotlib
│   └── excel/
│       ├── __init__.py
│       ├── individual.py     # Excel programático (V5 Legacy)
│       └── consolidado.py    # Excel maestro de equipo
└── Salida_PDF/               # PDFs generados
└── Salida_Excel/             # Excels generados
```

---

## 7. Formato de Datos de Entrada (JSON)

```json
{
  "empresas": {
    "EMP001": {
      "info": {
        "nombre": "TechCorp",
        "sector": "Tecnología",
        "plantilla": {
          "color_primario": "#1e40af",
          "color_acento": "#f59e0b",
          "logo_url": "https://url-del-logo.com/logo.png"
        },
        "pesos_perfil_objetivo": {
          "adaptabilidad": 8,
          "comunicación": 7,
          "creatividad": 6,
          "disciplina": 9,
          "empatía": 7,
          "iniciativa": 8,
          "resiliencia": 7
        }
      },
      "clientes": [
        {
          "id": "C001",
          "nombre": "Juan Pérez",
          "dimensiones": {
            "adaptabilidad": 85,
            "comunicacion": 78,
            "creatividad": 65,
            "disciplina": 90,
            "empatia": 72,
            "iniciativa": 80,
            "resiliencia": 75
          },
          "frases_predeterminadas": ["Lideró proyecto X"]
        }
      ]
    }
  }
}
```

---

## 8. Optimizaciones Implementadas

| Aspecto | Mejora |
|---------|--------|
| **Velocidad IA** | Generación asíncrona para múltiples prompts de Groq |
| **Robustez** | Captura inteligente de errores HTTP para URLs de logos |
| **Plantillas Flexibles** | Uso de marcadores (e.g., `[CHART_RADAR]`) para insertar gráficos en Excel |
| **Memoria** | Liberación de gráficos en memoria (`plt.close()`) y context managers |
| **Modularidad** | Separación del generador de plantillas (`generar_plantilla.py`) |

---

## 9. Uso

```bash
# 1. Configurar .env
echo "GROQ_API_KEY=tu_clave_aqui" > .env

# 2. Instalar dependencias
pip install -r requirements.txt
playwright install chromium

# 3. Ejecutar
python motor_prisma.py

# 4. Verificar salidas
ls Salida_PDF/   # PDFs individuales
ls Salida_Excel/ # Excels individuales + consolidado
```
