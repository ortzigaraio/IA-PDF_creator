import json
import jinja2
from playwright.sync_api import sync_playwright
import openpyxl
import os
import matplotlib.pyplot as plt
import numpy as np
import base64
from datetime import datetime

# --- CONFIGURACIÓN DE CARPETAS ---
for carpeta in ["Salida_HTML", "Salida_PDF", "Salida_Excel", "Salida_Imagenes"]:
    os.makedirs(carpeta, exist_ok=True)

# --- CARGA DE DICCIONARIO ---
with open('diccionario_perfiles.json', 'r', encoding='utf-8') as f:
    dict_full = json.load(f)
    PERFILES_DICT = dict_full.get("perfiles", {})
    RECOM_DICT = dict_full.get("recomendaciones", {})

# --- LÓGICA DE INTELIGENCIA Y AUTO-CLASIFICACIÓN ---
def auto_clasificar_candidato(dims):
    """ Heurística para decidir perfil y recomendación según puntuaciones. """
    avg = sum(dims.values()) / len(dims)
    
    # 1. Decidir Perfil (Cluster) - Sistema de Puntuación de Ajuste
    puntos = {
        "CLUSTER_PERFIL_ANALITICO": dims.get("At. Detalle", 0) * 0.7 + dims.get("Tol. Estrés", 0) * 0.3,
        "CLUSTER_LID_ESTRATEGICO": dims.get("Lid. Operativo", 0) * 0.7 + dims.get("Adaptabilidad", 0) * 0.3,
        "CLUSTER_LID_EQUIPOS": dims.get("Eq. Trabajo", 0) * 0.6 + dims.get("Lid. Operativo", 0) * 0.4,
        "CLUSTER_PERFIL_CREATIVO": dims.get("Adaptabilidad", 0) * 0.8 + (100 - dims.get("At. Detalle", 0)) * 0.2,
        "CLUSTER_PERFIL_COMERCIAL": dims.get("Eq. Trabajo", 0) * 0.5 + dims.get("Adaptabilidad", 0) * 0.5,
        "CLUSTER_PERFIL_OPERATIVO": dims.get("At. Detalle", 0) * 0.5 + dims.get("Eq. Trabajo", 0) * 0.5
    }
    
    # El cluster con mayor puntuación de ajuste es el ganador
    cluster_id = max(puntos, key=puntos.get)

    # 2. Decidir Recomendación
    if avg >= 85:
        recom_id = "RECOM_PROMO_DIRECTA"
    elif avg < 55 or any(v < 35 for v in dims.values()):
        recom_id = "RECOM_PIP_BASICO"
    elif avg >= 72:
        recom_id = "RECOM_FORMACION_TECNICA"
    else:
        recom_id = "RECOM_CONSOLIDACION"
        
    return cluster_id, recom_id

def generar_contenido_ia(dimensiones, titulo_perfil):
    fortalezas = [k for k, v in dimensiones.items() if v >= 80]
    debilidades = [k for k, v in dimensiones.items() if v <= 50]
    
    analisis = f"Basado en el perfil de {titulo_perfil}, se observa un despliegue de competencias "
    analisis += f"sobresaliente en {', '.join(fortalezas)}. " if fortalezas else "equilibrado en las dimensiones evaluadas. "
    if debilidades:
        analisis += f"No obstante, existe un margen de optimización en {', '.join(debilidades)}, donde la respuesta ante la presión o demanda técnica puede ser inconsistente. "
    
    analisis += "En términos de proyección, el colaborador demuestra una afinidad natural con la cultura organizacional de PrismaHR, aportando un enfoque metódico que favorece la estabilidad operativa."

    plan = ""
    if dimensiones.get("Liderazgo Operativo", 0) < 50:
        plan += "<li>Fortalecer toma de decisiones bajo presión y delegación efectiva.</li>"
    if dimensiones.get("Atención al Detalle", 0) < 50:
        plan += "<li>Implementar sistemas de doble verificación y checklists dinámicos.</li>"
    if dimensiones.get("Trabajo en Equipo", 0) > 80:
        plan += "<li>Explorar roles de mentoría para facilitar la transferencia de conocimiento.</li>"
    
    if not plan:
        plan = "<li>Mantener los estándares actuales de rendimiento.</li><li>Explorar nuevas áreas de especialización técnica.</li>"
    plan += "<li>Fomentar la participación en comités transversales para ampliar la visión de negocio.</li>"
        
    return analisis, plan

# --- GENERACIÓN DE GRÁFICOS ---
def generar_radar_base64(dimensiones):
    etiquetas = list(dimensiones.keys())
    valores = list(dimensiones.values())
    angulos = np.linspace(0, 2 * np.pi, len(etiquetas), endpoint=False).tolist()
    valores += valores[:1]
    angulos += angulos[:1]
    
    fig, ax = plt.subplots(figsize=(5.5, 5.5), subplot_kw=dict(polar=True))
    ax.fill(angulos, valores, color='#002147', alpha=0.4) 
    ax.plot(angulos, valores, color='#002147', linewidth=2)
    ax.set_yticklabels([]) 
    ax.set_xticks(angulos[:-1])
    ax.set_xticklabels(etiquetas, fontsize=9, color='#4a5568')
    ax.set_ylim(0, 100)
    
    from io import BytesIO
    buf = BytesIO()
    plt.savefig(buf, format='png', transparent=True, bbox_inches='tight')
    plt.close()
    return base64.b64encode(buf.getvalue()).decode('utf-8')

# --- PROCESAMIENTO PRINCIPAL ---
def procesar_candidato(nombre, dimensiones, template):
    print(f"\n>>> Procesando: {nombre}...")
    
    # IA: Auto-clasificación basada en puntuaciones
    cluster_id, recom_id = auto_clasificar_candidato(dimensiones)
    
    # Obtener textos del diccionario
    perfil = PERFILES_DICT.get(cluster_id, {"titulo": "Perfil General", "descripcion": "Sin descripción."})
    recom = RECOM_DICT.get(recom_id, {"titulo": "Seguimiento", "descripcion": "Continuar plan estándar."})
    
    # Generar contenido dinámico
    analisis, plan = generar_contenido_ia(dimensiones, perfil['titulo'])
    radar_img = generar_radar_base64(dimensiones)
    
    # Datos de control
    fecha_hoy = datetime.now().strftime("%d de %B, %Y").lower()
    id_eval = f"PRISM-{datetime.now().year}-{nombre[:2].upper()}{np.random.randint(100, 999)}"
    
    html_final = template.render(
        nombre_candidato=nombre,
        titulo_perfil=perfil['titulo'],
        desc_perfil=perfil['descripcion'],
        titulo_recom=recom['titulo'],
        desc_recom=recom['descripcion'],
        analisis_detallado=analisis,
        plan_accion=plan,
        imagen_radar_base64=radar_img,
        fecha_actual=fecha_hoy,
        id_evaluacion=id_eval
    )
    
    nombre_seguro = nombre.replace(' ', '_')
    nombre_pdf = os.path.abspath(os.path.join("Salida_PDF", f"Informe_{nombre_seguro}.pdf"))
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html_final)
            page.wait_for_load_state("networkidle")
            page.pdf(path=nombre_pdf, format="A4", print_background=True, margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"})
            browser.close()
        print(f"✅ PDF Creado: {nombre_pdf}")
    except Exception as e:
        print(f"❌ Error PDF: {e}")

def ejecutar_lote(archivo_input):
    if not os.path.exists(archivo_input):
        print(f"❌ Error: {archivo_input} no encontrado.")
        return

    # Cargar plantilla una sola vez
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("."))
    template = env.get_template("plantilla_radar.html")
    
    wb = openpyxl.load_workbook(archivo_input)
    hoja = wb.active
    
    for fila in hoja.iter_rows(min_row=2, values_only=True):
        if not fila[0]: continue
        
        nombre = fila[0]
        dimensiones = {
            "Lid. Operativo": fila[1],
            "Eq. Trabajo": fila[2],
            "Adaptabilidad": fila[3],
            "At. Detalle": fila[4],
            "Tol. Estrés": fila[5]
        }
        
        procesar_candidato(nombre, dimensiones, template)

if __name__ == "__main__":
    ejecutar_lote("Datos_Entrada_Prisma.xlsx")
    print("\n✨ Procesamiento por lotes finalizado.")
