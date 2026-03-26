# Documentación Técnica del Sistema PrismaHR v2.0

## 1. Resumen de la Estructura General

El sistema **PrismaHR** es un motor de IA decisional que genera informes PDF personalizados para la evaluación de candidatos/colaboradores en Recursos Humanos. El flujo de trabajo es el siguiente:

```
Excel Entrada → motor_prisma.py → IA (Groq) → plantilla_radar.html → PDF Final
                    ↓
              diccionario_perfiles.json (Base de Conocimiento)
```

**Flujo de ejecución:**
1. El script lee los datos de candidatos desde `Datos_Entrada_Prisma.xlsx`
2. Para cada candidato, el motor de IA analiza sus dimensiones (liderazgo, trabajo en equipo, adaptabilidad, etc.)
3. Se consulta a Groq (IA) para generar contenido personalizado basado en el perfil
4. Los datos se renderizan en la plantilla HTML `plantilla_radar.html`
5. Se genera un PDF profesional de 2 páginas usando Playwright

---

## 2. Descripción de Cada Archivo

### 2.1 motor_prisma.py (Motor de Procesamiento Principal)

**Propósito:** Orquestar todo el proceso de generación de informes.

**Clases principales:**

| Clase | Función |
|-------|---------|
| [`UsuarioData`](_3Proyecto_PrismaHR/motor_prisma.py:20) | Estructura de datos del candidato (nombre, scores de 5 dimensiones) |
| [`AnalisadorParametros`](_3Proyecto_PrismaHR/motor_prisma.py:40) | Normaliza los scores (0-100) y calcula promedio |
| [`ClasificadorHibrido`](_3Proyecto_PrismaHR/motor_prisma.py:63) | Clasifica al candidato en un perfil usando Best Fit clásico + IA para zonas grises |
| [`MotorDecision`](_3Proyecto_PrismaHR/motor_prisma.py:101) | Decide qué veredicto dar (Promoción, Formación, Consolidación, Mejora) |
| [`GeneradorContenidoDinamico`](_3Proyecto_PrismaHR/motor_prisma.py:126) | Genera texto personalizado usando IA Groq |
| [`MotorPrismaHRv2`](_3Proyecto_PrismaHR/motor_prisma.py:214) | Orquestador principal que une todo |
| [`ejecutar_batch_excel()`](_3Proyecto_PrismaHR/motor_prisma.py:245) | Lee Excel, procesa cada fila, genera PDFs |

**Métodos de generación de contenido IA:**
- `generar_analisis_bloques()` → Genera 3 bloques de análisis (Fortalezas, Liderazgo, Veredicto)
- `generar_descripcion_recom()` → Genera la justificación del dictamen
- `generar_fortalezas()` → Lista fortalezas del perfil
- `generar_plan_accion()` → Genera un PDI de 12 meses
- `generar_puntos_criticos()` → **NUEVO:** Genera 2 puntos de atención dinámica basados en debilidades
- `generar_catalizadores_crecimiento()` → **NUEVO:** Genera 2 catalizadores de crecimiento basados en fortalezas

---

### 2.2 plantilla_radar.html (Plantilla de Presentación)

**Propósito:** Define el diseño visual del PDF con formato profesional de 2 páginas.

**Estructura HTML con Jinja2:**

| Sección | Descripción |
|---------|-------------|
| **Página 1** | Encabezado corporativo, datos del candidato, perfil determinado, mapa de competencias (gráfico radar) |
| **Página 2** | Análisis dinámico con bloques generados por IA, matriz de riesgos (Puntos Críticos y Catalizadores dinámicos) |

**Variables de Jinja2 usadas:**
```html
{{ nombre_candidato }}        <!-- Nombre del candidato -->
{{ titulo_perfil }}            <!-- Clasificación (ej: Perfil Analítico) -->
{{ desc_perfil }}              <!-- Descripción del perfil -->
{{ titulo_recom }}             <!-- Veredicto (ej: PROMOCIÓN DIRECTA) -->
{{ analisis_bloque_1 }}        <!-- Fortalezas (IA) -->
{{ analisis_bloque_2 }}        <!-- Liderazgo (IA) -->
{{ analisis_bloque_3 }}        <!-- Veredicto Final (IA) -->
{{ imagen_radar_base64 }}      <!-- Gráfico radar codificado -->
{{ puntos_criticos }}          <!-- Lista dinámica de puntos de atención -->
{{ catalizadores_crecimiento }} <!-- Lista dinámica de catalizadores -->
```

**Tecnologías usadas:**
- Tailwind CSS (CDN) para estilos
- Google Fonts (Roboto)
- Playwright para renderizado PDF

---

### 2.3 diccionario_perfiles.json (Base de Conocimiento)

**Propósito:** Define los perfiles de clasificación y sus pesos para la decisión automática.

**Estructura del JSON:**

```json
{
  "metadata": { ... },           // Info de versión
  "perfiles": {
    "analítico": {
      "id": "analítico",
      "nombre": "Perfil Analítico",
      "descripcion": "Usuario que sobresale en análisis...",
      "pesos_clasificacion": {
        "atención_detalle": 0.70,   // Peso mayor para este perfil
        "adaptabilidad": 0.10,
        "trabajo_equipo": 0.10,
        "tolerancia_estrés": 0.05,
        "liderazgo": 0.05
      },
      "frases_contextuales": { ... },  // Textos predefinidos
      "planes_accion": { ... }         // Planes según veredicto
    },
    "dinámico": { ... },
    "equilibrio": { ... },
    "lider": { ... }
  }
}
```

**Perfiles definidos:**
1. **analítico** - Alta atención al detalle, prefieres datos sobre intuición
2. **dinámico** - Versátil, adaptable, orientado a resultados rápidos
3. **equilibrio** - Buen balance entre todas las dimensiones
4. **lider** - Alta capacidad de liderazgo y trabajo en equipo

---

### 2.4 Datos_Entrada_Prisma.xlsx (Archivo de Entrada)

**Propósito:** Hoja de cálculo con los candidatos a evaluar.

**Columnas:**
| Columna | Descripción |
|---------|-------------|
| Nombre | Nombre completo del candidato |
| Liderazgo | Score 0-100 |
| Trabajo en Equipo | Score 0-100 |
| Adaptabilidad | Score 0-100 |
| Atención al Detalle | Score 0-100 |
| Tolerancia Estrés | Score 0-100 |
| Codigo_Cluster | (No usado activamente, el motor lo calcula) |
| Codigo_Recomendacion | (No usado activamente) |

**Ejemplo de datos:**
```
Elena García    → L:45  Eq:85  Adp:90  Det:95  Est:60
Juan Pérez      → L:70  Eq:60  Adp:50  Det:40  Est:80
Marta Ruiz      → L:90  Eq:95  Adp:85  Det:70  Est:75
Carlos Lyon     → L:30  Eq:40  Adp:60  Det:85  Est:90
Sofía Marín     → L:60  Eq:80  Adp:75  Det:65  Est:55
```

---

## 3. Flujo de Ejecución Completo

### Paso 1: Lectura de Excel
```python
# En ejecutar_batch_excel()
wb = openpyxl.load_workbook("Datos_Entrada_Prisma.xlsx")
hoja = wb.active
for fila in hoja.iter_rows(min_row=2, values_only=True):
    # fila = (Nombre, Liderazgo, TrabajoEquipo, Adaptabilidad, AtencionDetalle, ToleranciaEstres)
```

### Paso 2: Clasificación del Perfil
```python
# Best Fit clásico: multiplicar scores por pesos del perfil
# Si avg_score está entre 50-75, consultar IA para confirmar/cambiar perfil
cluster = clasificador.consultar_ia_zona_gris(features, mejor_perfil)
```

### Paso 3: Generación de Contenido IA
```python
# Groq genera texto personalizado para cada candidato
bloques = generador.generar_analisis_bloques(usuario, perfil, score)
puntos_criticos = generador.generar_puntos_criticos(usuario, features, perfil, score)
catalizadores = generador.generar_catalizadores_crecimiento(usuario, features, perfil, score)
```

### Paso 4: Renderizado HTML
```python
html = template.render(
    nombre_candidato=usuario.nombre,
    puntos_criticos=puntos_criticos,           # ← Ahora dinámico
    catalizadores_crecimiento=catalizadores    # ← Ahora dinámico
)
```

### Paso 5: Generación PDF
```python
page = browser.new_page()
page.set_content(html_final)
page.pdf(path="Informe_Nombre.pdf", format="A4")
```

---

## 4. Mejoras Recientes (v4.2 PRO)

Se han añadido dos nuevos métodos de generación dinámica en [`motor_prisma.py`](_3Proyecto_PrismaHR/motor_prisma.py:175):

1. **Puntos de Atención Crítica** → Analiza las dimensiones más bajas del candidato y genera recomendaciones específicas de mejora
2. **Catalizadores de Crecimiento** → Identifica las dimensiones más altas y genera oportunidades de desarrollo

Ambos contenidos ahora se renderizan dinámicamente en la **segunda página** del PDF en lugar de tener texto estático.

---

## 5. Cómo Ejecutar el Sistema

```bash
cd _3Proyecto_PrismaHR
python motor_prisma.py
```

El sistema procesará todos los candidatos del Excel y generará los PDFs en la carpeta `Salida_PDF/`.
