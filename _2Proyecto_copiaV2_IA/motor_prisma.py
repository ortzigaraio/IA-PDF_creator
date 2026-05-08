"""
PrismaHR v2.0 - Motor de IA Decisional (Versión Restaurada con Groq)
Implementación base con generación dinámica de contenido adaptada a Groq y PDF de Alta Fidelidad.
"""

import json
import asyncio
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from groq import Groq
import logging
import os
from datetime import datetime
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class UsuarioData:
    """Estructura de datos del usuario desde formulario"""
    usuario_id: str
    nombre: str
    atención_detalle: float  # 0-100
    adaptabilidad: float
    trabajo_equipo: float
    tolerancia_estrés: float
    liderazgo: float

@dataclass
class DecisionIA:
    """Resultado de la decisión automática"""
    cluster_id: str
    avg_score: float
    veredicto: str
    secciones_pdf: Dict[str, bool]
    puntos_enfasis: List[str]
    contenido_generado: bool

class AnalisadorParametros:
    """Convierte respuestas del formulario en features normalizados"""
    def __init__(self):
        self.pesos_defaults = {
            "atención_detalle": 1.0, "adaptabilidad": 1.0, 
            "trabajo_equipo": 1.0, "tolerancia_estrés": 1.0, "liderazgo": 1.0
        }
    
    def extraer_features(self, usuario: UsuarioData) -> Dict:
        features = {
            "atención_detalle": usuario.atención_detalle / 100,
            "adaptabilidad": usuario.adaptabilidad / 100,
            "trabajo_equipo": usuario.trabajo_equipo / 100,
            "tolerancia_estrés": usuario.tolerancia_estrés / 100,
            "liderazgo": usuario.liderazgo / 100
        }
        avg_score = sum(features.values()) / len(features) * 100
        return {
            "vector_features": list(features.values()),
            "avg_score": round(avg_score, 1),
            "features_dict": features
        }

class ClasificadorHibrido:
    """Combina Best Fit clásico con IA para zonas grises"""
    def __init__(self, json_perfiles: str, cliente_groq: Groq):
        with open(json_perfiles, 'r', encoding='utf-8') as f:
            self.perfiles_data = json.load(f)
        self.cliente_groq = cliente_groq
        self.perfiles = self.perfiles_data.get("perfiles", {})
    
    def best_fit_clasico(self, features: Dict) -> Tuple[str, float]:
        max_score = -1
        mejor_perfil = None
        for perfil_id, perfil_config in self.perfiles.items():
            pesos = perfil_config.get("pesos_clasificacion", {})
            score = sum(features["features_dict"].get(key, 0) * weight for key, weight in pesos.items())
            if score > max_score:
                max_score = score
                mejor_perfil = perfil_id
        return mejor_perfil, max_score
    
    def consultar_ia_zona_gris(self, features: Dict, perfil_candidato: str) -> Optional[str]:
        avg_score = features["avg_score"]
        if not (50 <= avg_score <= 75):
            return perfil_candidato
        
        prompt = f"El usuario tiene {avg_score}/100 y perfil {perfil_candidato}. Confirma o cambia el perfil entre: {', '.join(self.perfiles.keys())}. Responde solo con una palabra clave."
        try:
            res = self.cliente_groq.chat.completions.create(
                model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], max_tokens=20
            )
            respuesta = res.choices[0].message.content.strip().lower()
            for perfil_id in self.perfiles.keys():
                if perfil_id.lower() in respuesta:
                    return perfil_id
            return perfil_candidato
        except Exception as e:
            logger.error(f"Fallback IA: {e}")
            return perfil_candidato

class MotorDecision:
    """Automatiza decisiones sobre contenido del PDF"""
    UMBRALES = {
        "promotion": 85, "training": (72, 85), "consolidation": (55, 72), "improvement": 55
    }
    
    def decidir_contenido(self, avg_score: float, cluster: str) -> DecisionIA:
        if avg_score >= self.UMBRALES["promotion"]:
            veredicto = "PROMOCIÓN DIRECTA"
        elif avg_score < self.UMBRALES["improvement"]:
            veredicto = "PLAN DE MEJORA INMEDIATO"
        elif self.UMBRALES["training"][0] <= avg_score <= self.UMBRALES["training"][1]:
            veredicto = "FORMACIÓN TÉCNICA RECOMENDADA"
        else:
            veredicto = "CONSOLIDACIÓN"
        
        secciones_pdf = {
            "encabezado_ejecutivo": True, "analisis_fortalezas": True,
            "analisis_debilidades": avg_score < 80, "plan_accion": True,
            "grafico_radar": True, "recomendaciones_rrhh": avg_score >= 75
        }
        
        puntos_enfasis = ["Considera rol de mentor"] if avg_score >= 85 else ["Requiere seguimiento"] if avg_score < 55 else []
        return DecisionIA(cluster_id=cluster, avg_score=avg_score, veredicto=veredicto, secciones_pdf=secciones_pdf, puntos_enfasis=puntos_enfasis, contenido_generado=True)

class GeneradorContenidoDinamico:
    """Genera contenido dinámico usando Groq"""
    def __init__(self, cliente_groq: Groq, json_perfiles: str):
        self.cliente = cliente_groq
        with open(json_perfiles, 'r', encoding='utf-8') as f:
            self.perfiles_data = json.load(f)
    
    def generar_analisis_bloques(self, usuario: UsuarioData, perfil: str, avg_score: float) -> List[str]:
        prompt = f"Genera 3 bloques de análisis para {usuario.nombre} ({perfil}) con rating {avg_score}/100. Bloque 1: Fortalezas. Bloque 2: Liderazgo. Bloque 3: Veredicto Final. Cada bloque debe tener exactamente 2 oraciones potentes. Separa los bloques con '###'."
        try:
            res = self.cliente.chat.completions.create(
                model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], max_tokens=1000
            )
            bloques = res.choices[0].message.content.strip().split('###')
            return [b.strip() for b in bloques][:3]
        except:
            return ["Análisis de fortalezas estándar.", "Potencial de liderazgo en desarrollo.", "Recomendación operativa estable."]

    def generar_descripcion_recom(self, usuario: UsuarioData, perfil: str, avg_score: float) -> str:
        prompt = f"Genera una 'Justificación de Dictamen' muy breve (máx 2-3 frases) para {usuario.nombre} ({perfil}) con score {avg_score}."
        try:
            res = self.cliente.chat.completions.create(
                model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], max_tokens=200
            )
            return res.choices[0].message.content.strip()
        except:
            return "Consolidar rol actual mediante planes de formación continua."

    def generar_fortalezas(self, usuario: UsuarioData, features: Dict, perfil: str) -> List[str]:
        prompt = f"Lista 3 fortalezas clave para un perfil {perfil}. Solo los nombres de las fortalezas, una por línea."
        try:
            res = self.cliente.chat.completions.create(
                model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], max_tokens=150
            )
            return [l.strip().lstrip('-').strip() for l in res.choices[0].message.content.split('\n') if l.strip()]
        except:
            return ["Capacidad adaptativa", "Enfoque en procesos"]

    def generar_plan_accion(self, usuario: UsuarioData, perfil: str, avg_score: float) -> str:
        prompt = f"Genera un 'Plan de Desarrollo Individual (PDI)' de 12 meses para {usuario.nombre} ({perfil}). Incluye 5 hitos clave con metodologías (ej. OKRs, 70-20-10, Mentoring). Sé muy detallado y usa un tono de alta dirección."
        try:
            res = self.cliente.chat.completions.create(
                model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], max_tokens=800
            )
            content = res.choices[0].message.content.strip()
            # Formatear para HTML si es necesario
            return content.replace('\n', '<br>')
        except:
            return "Establecer objetivos SMART inmediatos. Participar en programas de coaching ejecutivo."

def generar_radar_base64(dimensiones):
    import matplotlib.pyplot as plt
    import numpy as np
    import base64
    from io import BytesIO
    
    etiquetas = list(dimensiones.keys())
    valores = [float(v) for v in dimensiones.values()]
    angulos = np.linspace(0, 2 * np.pi, len(etiquetas), endpoint=False).tolist()
    valores += valores[:1]
    angulos += angulos[:1]
    
    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    
    # Polígono gris con borde negro como en la imagen v4.2
    ax.fill(angulos, valores, color='#9ca3af', alpha=0.6)
    ax.plot(angulos, valores, color='#000000', linewidth=1.5)
    
    ax.set_yticklabels([])
    ax.set_xticks(angulos[:-1])
    ax.set_xticklabels(etiquetas, fontsize=8, color='#4b5563')
    
    # Cuadrícula circular clásica
    ax.grid(True, color='#d1d5db', linestyle='-', linewidth=0.5)
    ax.set_ylim(0, 100)
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close()
    return base64.b64encode(buf.getvalue()).decode('utf-8')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', transparent=True, dpi=100, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    return base64.b64encode(buf.getvalue()).decode('utf-8')

class MotorPrismaHRv2:
    """Orquestador principal"""
    def __init__(self, api_key_groq: str, ruta_json_perfiles: str = "diccionario_perfiles.json"):
        self.cliente_groq = Groq(api_key=api_key_groq)
        self.ruta_json = ruta_json_perfiles
        self.perfiles_data = json.load(open(ruta_json_perfiles, 'r', encoding='utf-8'))
        self.analizador = AnalisadorParametros()
        self.clasificador = ClasificadorHibrido(ruta_json_perfiles, self.cliente_groq)
        self.motor_decision = MotorDecision()
        self.generador = GeneradorContenidoDinamico(self.cliente_groq, ruta_json_perfiles)
    
    def procesar_usuario(self, usuario: UsuarioData) -> Dict:
        features = self.analizador.extraer_features(usuario)
        cluster_best_fit, _ = self.clasificador.best_fit_clasico(features)
        cluster_final = self.clasificador.consultar_ia_zona_gris(features, cluster_best_fit)
        decision = self.motor_decision.decidir_contenido(features["avg_score"], cluster_final)
        
        bloques_analisis = self.generador.generar_analisis_bloques(usuario, cluster_final, features["avg_score"])
        contenido = {
            "analisis_bloques": bloques_analisis,
            "descripcion_recom": self.generador.generar_descripcion_recom(usuario, cluster_final, features["avg_score"]),
            "fortalezas": self.generador.generar_fortalezas(usuario, features, cluster_final)
        }
        
        return {
            "usuario_id": usuario.usuario_id, "cluster": cluster_final,
            "avg_score": features["avg_score"], "veredicto": decision.veredicto,
            "secciones_pdf": decision.secciones_pdf, "contenido": contenido,
            "puntos_enfasis": decision.puntos_enfasis
        }

def ejecutar_batch_excel(motor, archivo_input):
    import openpyxl, os, jinja2
    from playwright.sync_api import sync_playwright
    
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("."))
    template = env.get_template("plantilla_radar.html")
    wb = openpyxl.load_workbook(archivo_input)
    hoja = wb.active
    
    os.makedirs("Salida_PDF", exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for index, fila in enumerate(hoja.iter_rows(min_row=2, values_only=True)):
            if not fila[0]: continue
            usuario = UsuarioData(
                usuario_id=f"BCH{index:03d}", nombre=fila[0],
                atención_detalle=fila[4], adaptabilidad=fila[3],
                trabajo_equipo=fila[2], tolerancia_estrés=fila[5], liderazgo=fila[1]
            )
            resultado = motor.procesar_usuario(usuario)
            
            dimensiones = {
                "Eq. Trabajo": int(fila[2]),
                "Lid. Operativo": int(fila[1]),
                "Tol. Estrés": int(fila[5]),
                "At. Detalle": int(fila[4]),
                "Adaptabilidad": int(fila[3])
            }
            radar_img = generar_radar_base64(dimensiones)
            radar_items = [{"nombre": k, "valor": v} for k, v in dimensiones.items()]
            
            auth_hash = hashlib.md5(f"{usuario.nombre}{datetime.now()}".encode()).hexdigest()[:8].upper()
            perfil_info = motor.perfiles_data["perfiles"].get(resultado["cluster"], {})
            
            bloques = resultado["contenido"]["analisis_bloques"]
            html_final = template.render(
                nombre_candidato=usuario.nombre,
                titulo_perfil=perfil_info.get("nombre", "Perfil técnico"),
                desc_perfil=perfil_info.get("descripcion", ""),
                titulo_recom=resultado["veredicto"],
                desc_recom=resultado["contenido"]["descripcion_recom"],
                analisis_bloque_1=bloques[0] if len(bloques) > 0 else "Análisis N/A",
                analisis_bloque_2=bloques[1] if len(bloques) > 1 else "Análisis N/A",
                analisis_bloque_3=bloques[2] if len(bloques) > 2 else "Análisis N/A",
                imagen_radar_base64=radar_img,
                radar_items=radar_items,
                fecha_actual=datetime.now().strftime("%d de %B, %Y").lower(),
                id_evaluacion=f"PRISM-{datetime.now().year}-CA{auth_hash[:3]}",
                auth_key=f"{auth_hash[:4]}-XPL-{datetime.now().year}"
            )
            
            nombre_pdf = os.path.abspath(os.path.join("Salida_PDF", f"Informe_{usuario.nombre.replace(' ', '_')}.pdf"))
            page = browser.new_page()
            page.set_content(html_final)
            page.pdf(path=nombre_pdf, format="A4", print_background=True)
            page.close()
            print(f"✅ PDF GENERADO: {nombre_pdf}")
        browser.close()

if __name__ == "__main__":
    API_KEY = os.environ.get("GROQ_API_KEY")
    if not API_KEY:
        raise ValueError("Falta la variable de entorno GROQ_API_KEY")
    motor = MotorPrismaHRv2(API_KEY)
    ejecutar_batch_excel(motor, "Datos_Entrada_Prisma.xlsx")