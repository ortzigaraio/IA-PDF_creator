"""
src/pdf_generator.py — Generador de PDF con Chromium+Jinja2
"""
from __future__ import annotations
import os

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import Browser

from src.charts import radar_base64
from src.config import settings
from src.models import DIMENSIONES_LABELS, EmpresaInfo, ResultadoModel, UsuarioModel


class PDFGenerator:
    """Orquesta Jinja2 y Playwright para exportar reportes."""

    def __init__(self, template_dir: str = "."):
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def render_html(
        self,
        usuario: UsuarioModel,
        resultado: ResultadoModel,
        empresa_info: EmpresaInfo,
    ) -> str:
        """Renderiza HTML inyectando radar en Base64."""
        template = self.env.get_template("plantilla_radar.html")

        # Generar radar en base64 map -> objective map
        obj = resultado.perfil_objetivo
        
        # Mapeamos nombres (con tildes vía DIMENSIONES_LABELS si la plantilla lo espera)
        # O si la plantilla espera las claves crudas (adaptabilidad, etc), le pasamos el diccionario con las claves normales
        # Revisamos qué espera "plantilla_radar.html". Generalmente espera que el motor le inyecte gráfico de matplotlib (foto).
        
        dim_dict_raw = usuario.dimensiones.model_dump()
        dim_display = {DIMENSIONES_LABELS[k]: dim_dict_raw.get(k, 50) for k in DIMENSIONES_LABELS.keys()}
        obj_display = {DIMENSIONES_LABELS[k]: obj.get(k, 0.0) for k in DIMENSIONES_LABELS.keys()}

        b64_radar = radar_base64(
            dim_display,
            obj_display,
            color_usuario="#" + empresa_info.plantilla.color_primario.replace("#", ""),
            color_objetivo="#" + empresa_info.plantilla.color_acento.replace("#", "")
        )

        return template.render(
            nombre=usuario.nombre,
            empresa=empresa_info.nombre,
            sector=empresa_info.sector,
            compatibilidad=resultado.compatibilidad,
            veredicto=resultado.veredicto,
            radar_image_base64=b64_radar,
            usuario_stats=usuario.dimensiones.as_display_dict(),
            colores=empresa_info.plantilla,
            fortalezas=resultado.contenido.fortalezas,
            puntos_criticos=resultado.contenido.puntos_criticos,
            catalizadores=resultado.contenido.catalizadores_crecimiento,
            bloques_ejecutivo=resultado.contenido.analisis_bloques,
            justificacion=resultado.contenido.descripcion_recom,
            puntos_enfasis=resultado.puntos_enfasis,
            alerta_riesgo=resultado.contenido.alerta_riesgo
        )

    def generate_pdf(
        self,
        browser: Browser,
        usuario: UsuarioModel,
        resultado: ResultadoModel,
        empresa_info: EmpresaInfo,
    ) -> str:
        """Renderiza HTML y lo convierte a PDF usando Playwright."""
        html = self.render_html(usuario, resultado, empresa_info)

        os.makedirs(settings.OUTPUT_PDF_DIR, exist_ok=True)
        filename = f"Reporte_{usuario.nombre.replace(' ', '_')}.pdf"
        output_path = os.path.join(settings.OUTPUT_PDF_DIR, filename)

        page = browser.new_page()
        page.set_content(html)
        page.pdf(path=output_path, format="A4", print_background=True)
        page.close()

        return output_path
