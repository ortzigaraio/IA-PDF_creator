# PrismaHR Pro — Documentación Técnica del Proyecto 05

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
│                      run_batch.py                               │
│                  (Punto de entrada)                              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PrismaEngine (main.py)                       │
│            Motor central que orquesta el flujo                  │
└──────────┬──────────────┬──────────────┬──────────────────────┘
           │              │              │
           ▼              ▼              ▼
┌─────────────────┐ ┌───────────┐ ┌──────────────────────────┐
│  AI Client      │ │ Processor │ │ Content Generator        │
│  (Groq API)     │ │ (Lógica)  │ │ (6 prompts paralelos)    │
└────────┬────────┘ └─────┬─────┘ └──────────┬───────────────┘
         │                 │                   │
         ▼                 ▼                   ▼
┌─────────────────┐ ┌───────────┐ ┌──────────────────────────┐
│ PDF Generator   │ │ Excel     │ │ Charts                    │
│ (Jinja2+Play)   │ │ Individual│ │ (Matplotlib PNG bytes)   │
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
- **ThreadPoolExecutor compartido**: max_workers=12 para eficiencia

### 3.5 Generador de Contenido (`content_generator.py`)
Lanza **6 prompts en paralelo** con `asyncio.gather()`:

1. `_bloques()`: 3 bloques de análisis (Fortalezas, Liderazgo, Veredicto)
2. `_descripcion()`: Justificación breve del dictamen
3. `_fortalezas()`: 3 fortalezas clave
4. `_puntos_criticos()`: 2 puntos de atención
5. `_catalizadores()`: 2 catalizadores de crecimiento
6. `_alerta_riesgo()`: Evaluación de burnout/fuga de talento

**Optimización**: Secuencial ~8-12s → Paralelo ~2s (6x más rápido)

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

### 3.8 Excel Individual (`excel/individual.py`)
Genera libro con **5 hojas**:

1. **Dashboard**: KPIs + 4 gráficos embebidos
2. **Radar Comparativo**: Tabla + gráfico radar nativo (interactivo)
3. **Análisis de Gaps**: Tabla + gráfico de barras de gaps
4. **Algoritmo de Cálculo**: Explicación paso a paso de la fórmula
5. **Fortalezas y Debilidades**: Contenido cualitativo

### 3.9 Excel Consolidado (`excel/consolidado.py`)
Genera reporte maestro del equipo con:
- **Ranking del Equipo**: Ordenado por compatibilidad
- **Heatmap del Equipo**: Mapa de calor de competencias

---

## 4. Pipeline del Proyecto — Flujo de Trabajo

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          INICIO: run_batch.py                              │
│                    python run_batch.py datos_empresa.json                  │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PASO 1: CARGA DE DATOS                                                   │
│  ├─ Leer JSON con empresas y clientes                                     │
│  ├─ Validar estructura con Pydantic                                      │
│  └─ Crear directorio de salida                                            │
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
│     ├── Bloques de análisis                                              │
│     ├── Descripción del veredicto                                        │
│     ├── Fortalezas                                                        │
│     ├── Puntos críticos                                                   │
│     ├── Catalizadores                                                     │
│     └── Alerta de riesgo                                                  │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PASO 5: DECIDIR VEREDITO                                                │
│  ├─ Compatibilidad ≥ 85% → PROMOCIÓN DIRECTA                            │
│  ├─ Compatibilidad 72-84% → FORMACIÓN TÉCNICA                           │
│  ├─ Compatibilidad 55-71% → CONSOLIDACIÓN                               │
│  └─ Compatibilidad < 55% → PLAN DE MEJORA                              │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────────┐  ┌────────────────────┐  ┌──────────────────────────┐
│  GENERAR PDF      │  │  GENERAR EXCEL     │  │  ACUMULAR EN LISTA       │
│  - Render HTML    │  │  INDIVIDUAL        │  │  (para consolidado)      │
│  - Gráfico radar  │  │  - 5 hojas         │  │                          │
│  - Convertir PDF  │  │  - Múltiples       │  │  ItemEquipo:             │
│  (Playwright)     │  │    gráficos        │  │  - Usuario               │
│                   │  │                    │  │  - Resultado             │
│                   │  │                    │  │  - EmpresaInfo           │
└───────────────────┘  └────────────────────┘  └──────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │  FIN DE CLIENTES        │
                    └────────────┬────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PASO 6: GENERAR EXCEL CONSOLIDADO                                       │
│  - Ranking del equipo                                                    │
│  - Heatmap colectivo                                                    │
│  - Guardar archivo maestro                                              │
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

## 5. Diagrama de Flujo Detallado

```
                    ┌─────────────────┐
                    │  JSON de Entrada │
                    │ datos_empresa   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ PrismaEngine    │
                    │ .run_batch_json │
                    └────────┬────────┘
                             │
                             ▼
                 ┌────────────────────────┐
                 │ for empresa in empresas│◄────────┐
                 └───────────┬────────────┘         │
                             │                      │
                             ▼                      │
              ┌─────────────────────────────┐       │
              │ 1. Parse EmpresaInfo        │       │
              │ 2. Collect scores equipo   │       │
              └───────────┬─────────────────┘       │
                           │                       │
                           ▼                       │
              ┌─────────────────────────────┐       │
              │ for cliente in clientes     │◄──────┘
              └───────────┬─────────────────┘   (loop)
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
   ┌───────────┐    ┌───────────┐    ┌───────────────┐
   │ Processor │    │ Processor │    │ ContentGen    │
   │ .percentil│    │ .compatib │    │ .generar_todo │
   └─────┬─────┘    └─────┬─────┘    └───────┬───────┘
         │                 │                  │
         └────────┬────────┘                  │
                  │                           │
                  │         ┌─────────────────┘
                  │         │
                  ▼         ▼
         ┌────────────────────────┐
         │ ResultadoModel completo│
         │ - compatibilidad       │
         │ - veredicto            │
         │ - contenido IA          │
         └───────────┬────────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
    ▼                ▼                ▼
┌────────┐     ┌──────────┐    ┌──────────────┐
│  PDF   │     │  Excel   │    │ ItemEquipo[]│
│ Gen    │     │ Individual│    │ (acumulador)│
└────────┘     └──────────┘    └──────┬───────┘
                                     │
                    ┌────────────────┘
                    │ (post-loop)
                    ▼
           ┌──────────────────┐
           │ Excel Consolidado│
           │ - Ranking        │
           │ - Heatmap        │
           └──────────────────┘
```

---

## 6. Archivos del Proyecto

```
_5Proyecto_PrismaHR_Pro/
├── run_batch.py              # Punto de entrada
├── .env                      # Variables de entorno
├── plantilla_radar.html      # Plantilla HTML para PDF
├── src/
│   ├── __init__.py
│   ├── main.py               # PrismaEngine (orquestador)
│   ├── config.py             # Settings (Pydantic)
│   ├── models.py             # Modelos de datos (Pydantic v2)
│   ├── processor.py          # Lógica de negocio
│   ├── ai_client.py          # Cliente Groq con retry
│   ├── content_generator.py  # Generación IA en paralelo
│   ├── pdf_generator.py      # PDF con Jinja2+Playwright
│   ├── charts.py             # Gráficos Matplotlib
│   └── excel/
│       ├── __init__.py
│       ├── individual.py     # Excel por candidato
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
          "color_acento": "#f59e0b"
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
| **Velocidad IA** | 6x más rápido con `asyncio.gather()` |
| **Robustez** | Retry con backoff exponencial (tenacity) |
| **Memoria** | ThreadPoolExecutor compartido (no crear uno por llamada) |
| **Limpieza** | Context manager `temp_png()` para archivos temporales |
| **Tipado** | Pydantic v2 para validación automática |
| **Concurrencia** | Browser Playwright compartido para todos los PDFs |

---

## 9. Uso

```bash
# 1. Configurar .env
echo "GROQ_API_KEY=tu_clave_aqui" > .env

# 2. Ejecutar
python run_batch.py datos_empresa.json

# 3. Verificar salidas
ls Salida_PDF/   # PDFs individuales
ls Salida_Excel/ # Excels individuales + consolidado
```
