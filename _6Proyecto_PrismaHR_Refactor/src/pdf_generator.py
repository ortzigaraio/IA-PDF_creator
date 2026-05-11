"""
src/pdf_generator.py — Generador de PDF con Chromium+Jinja2
"""
from __future__ import annotations
import os

from jinja2 import Environment, FileSystemLoader
from playwright.async_api import Browser

from src.charts import radar_base64, image_to_base64
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
        template = self.env.get_template("plantilla_pdf.html")

        # Generar radar en base64 map -> objective map
        obj = resultado.perfil_objetivo
        
        # Mapeamos nombres (con tildes vía DIMENSIONES_LABELS si la plantilla lo espera)
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
            nombre_candidato=usuario.nombre,
            nombre_empresa=empresa_info.nombre,
            sector_empresa=empresa_info.sector,
            compatibilidad=resultado.compatibilidad,
            titulo_perfil="Análisis de Compatibilidad",
            desc_perfil=f"Comparación con perfil objetivo de {empresa_info.nombre}",
            titulo_recom=resultado.veredicto,
            desc_recom=resultado.contenido.descripcion_recom,
            imagen_radar_base64=b64_radar,
            radar_items=[{"nombre": k, "valor": v} for k, v in dim_display.items()],
            analisis_bloque_1=resultado.contenido.analisis_bloques[0] if len(resultado.contenido.analisis_bloques) > 0 else "",
            analisis_bloque_2=resultado.contenido.analisis_bloques[1] if len(resultado.contenido.analisis_bloques) > 1 else "",
            analisis_bloque_3=resultado.contenido.analisis_bloques[2] if len(resultado.contenido.analisis_bloques) > 2 else "",
            puntos_criticos=resultado.contenido.puntos_criticos,
            catalizadores_crecimiento=resultado.contenido.catalizadores_crecimiento,
            fecha_actual=settings.FECHA_ACTUAL,
            id_evaluacion=f"PRISM-{settings.YEAR}-CA",
            auth_key="SECURE-PRO",
            color_primario=empresa_info.plantilla.color_primario,
            color_secundario=empresa_info.plantilla.color_secundario,
            color_acento=empresa_info.plantilla.color_acento,
            # Imagen de marca principal (desde settings)
            logo_base64=image_to_base64(settings.BRAND_LOGO),
            logo_height=settings.LOGO_HEIGHT_PDF,
            firma_base64=image_to_base64(settings.FIRMA_IMAGE)
        )

    async def generate_pdf(
        self,
        browser: Browser,
        usuario: UsuarioModel,
        resultado: ResultadoModel,
        empresa_info: EmpresaInfo,
    ) -> str:
        """Renderiza HTML y lo convierte a PDF usando Playwright asíncrono."""
        html = self.render_html(usuario, resultado, empresa_info)

        os.makedirs(settings.OUTPUT_PDF_DIR, exist_ok=True)
        filename = f"Reporte_{usuario.nombre.replace(' ', '_')}.pdf"
        output_path = os.path.join(settings.OUTPUT_PDF_DIR, filename)

        page = await browser.new_page()
        await page.set_content(html)
        await page.pdf(path=output_path, format="A4", print_background=True)
        await page.close()

        return output_path
