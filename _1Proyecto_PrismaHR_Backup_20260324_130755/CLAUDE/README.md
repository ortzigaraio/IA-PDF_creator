# PRISMA HR — Generador de Informes Psicométricos

Sistema de automatización para generar informes PDF individuales y un
Excel maestro a partir de datos de evaluaciones psicométricas.

---

## Estructura del proyecto

```
prisma_hr/
├── perfiles.json          ← Diccionario de perfiles con frases por dimensión
├── datos_test.csv         ← Datos de entrada (personas evaluadas)
├── generar_informes.py    ← Script principal
├── requirements.txt       ← Dependencias Python
├── README.md
└── salida/                ← Se crea automáticamente al ejecutar
    ├── pdf/               ← Un PDF por persona
    │   ├── maria_garcia_lopez_informe.pdf
    │   └── ...
    ├── radar_temp/        ← Imágenes de radar (temporales)
    └── registro_maestro.xlsx
```

---

## Instalación

### 1. Requisitos previos

- Python 3.9 o superior
- pip

### 2. Crear entorno virtual (recomendado)

```bash
# Crear entorno
python -m venv venv

# Activar en macOS/Linux
source venv/bin/activate

# Activar en Windows
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## Uso

### Prueba con los datos de ejemplo

```bash
python generar_informes.py
```

Esto procesará los 10 casos del archivo `datos_test.csv` y generará:
- 10 PDFs individuales en `salida/pdf/`
- 1 Excel maestro en `salida/registro_maestro.xlsx`

---

## Adaptar a tus propios datos

### Formato del CSV de entrada

El CSV debe tener exactamente estas columnas:

| Columna | Descripción | Ejemplo |
|---|---|---|
| nombre | Nombre de pila | María |
| apellidos | Apellidos | García López |
| email | Correo electrónico | maria@empresa.com |
| empresa | Nombre de la empresa | TechCorp S.L. |
| sector | Sector de actividad | Tecnología |
| puesto | Cargo o puesto | Project Manager |
| fecha_evaluacion | Fecha del test (YYYY-MM-DD) | 2024-01-15 |
| perfil_primario | Código del perfil principal | CLUSTER_COLABORADOR_NATO |
| perfil_secundario | Código del perfil secundario (opcional, puede estar vacío) | CLUSTER_PERFECCIONISTA_ANSIOSO |
| liderazgo | Puntuación 0-10 | 7.2 |
| trabajo_en_equipo | Puntuación 0-10 | 9.1 |
| comunicacion | Puntuación 0-10 | 7.8 |
| adaptabilidad | Puntuación 0-10 | 6.5 |
| toma_de_decisiones | Puntuación 0-10 | 5.9 |
| orientacion_resultados | Puntuación 0-10 | 7.0 |

### Códigos de perfil disponibles

```
CLUSTER_COLABORADOR_NATO       → Colaborador Integrador
CLUSTER_EJECUTOR_RUTINARIO     → Ejecutor Constante
CLUSTER_INDIVIDUALISTA_AISLADO → Especialista Solitario
CLUSTER_PERFECCIONISTA_ANSIOSO → Perfeccionista Limitante
CLUSTER_NARCISISTA_COMPETITIVO → Competidor Egocéntrico
CLUSTER_REACTIVO_DEFENSIVO     → Perfil Reactivo / Baja Regulación
CLUSTER_RESISTENTE_CAMBIO      → Conservador Inflexible
CLUSTER_PASIVO_DESMOTIVADO     → Perfil de Mínimo Esfuerzo
RECOM_NO_CONTRATAR_TOXICO      → Descarte por Incompatibilidad Cultural
RECOM_VIGILANCIA_DESEMPENO     → Plan de Mejora de Rendimiento
```

---

## Añadir o modificar perfiles

Edita `perfiles.json`. Cada perfil tiene esta estructura:

```json
{
  "codigo": "CLUSTER_MI_PERFIL",
  "tipo": "Perfil Principal",
  "titulo": "Nombre visible del perfil",
  "descripcion": "Descripción general que aparece en el informe.",
  "dimensiones": {
    "liderazgo":              "Frase para liderazgo...",
    "trabajo_en_equipo":      "Frase para trabajo en equipo...",
    "comunicacion":           "Frase para comunicación...",
    "adaptabilidad":          "Frase para adaptabilidad...",
    "toma_de_decisiones":     "Frase para toma de decisiones...",
    "orientacion_resultados": "Frase para orientación a resultados..."
  },
  "recomendacion": "Texto de recomendación de uso.",
  "alerta": "Texto de alerta o consideración especial.",
  "compatibilidades": {
    "CLUSTER_OTRO_PERFIL": {
      "descripcion_mixta": "Frase cuando aparece combinado con este perfil.",
      "alerta": "Alerta específica para la combinación."
    }
  }
}
```

Los tipos válidos son:
- `"Perfil Principal"` → Azul
- `"Perfil Riesgo"` → Rojo
- `"Accion Recomendada"` → Ámbar

---

## Procesamiento masivo (1000+ formularios)

Para procesar grandes volúmenes, simplemente añade todas las filas al CSV.
El script procesa en secuencia con control de errores. Si una fila falla,
el resto continúa procesándose.

Para paralelizar (reducir tiempo en volúmenes muy altos):
```python
# En generar_informes.py, reemplazar el bucle final por:
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=4) as executor:
    executor.map(lambda p: procesar_persona(p, perfiles), personas)
```

---

## Soporte de problemas comunes

**Error: No module named 'reportlab'**
```bash
pip install -r requirements.txt
```

**El PDF no muestra el radar**
Verifica que la carpeta `salida/radar_temp/` existe y tiene permisos de escritura.

**Perfil no encontrado**
El código en la columna `perfil_primario` del CSV no coincide con ningún
código en `perfiles.json`. Verifica que sea exactamente igual (mayúsculas y guiones bajos).
