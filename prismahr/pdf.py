"""
PDF individual: plantilla HTML (Jinja2) → PDF con Chromium (Playwright).

La plantilla no carga nada de internet: CSS propio y fuentes del sistema.
El autoescape está activado, así que el texto de la IA no puede inyectar HTML.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import Browser

from prismahr.charts import imagen_a_data_uri, png_a_data_uri, radar_bytes
from prismahr.config import Settings, fecha_es
from prismahr.models import DIMENSIONES, DIMENSIONES_LABELS, Informe


def nombre_archivo_seguro(texto: str) -> str:
    """'José Pérez / Ventas' → 'Jose_Perez_Ventas'."""
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9]+", "_", t).strip("_")
    return t or "sin_nombre"


class GeneradorPDF:
    def __init__(self, cfg: Settings, base_datos: Path):
        self.cfg = cfg
        self.base_datos = base_datos  # para resolver rutas de logo relativas al JSON
        self.env = Environment(
            loader=FileSystemLoader(str(cfg.TEMPLATES_DIR)),
            autoescape=select_autoescape(["html"]),
        )

    def render_html(self, inf: Informe) -> str:
        p = inf.empresa.plantilla
        objetivo = inf.empresa.perfil_objetivo_100()
        dims = inf.persona.dimensiones

        radar = radar_bytes(
            {DIMENSIONES_LABELS[k]: dims[k] for k in DIMENSIONES},
            {DIMENSIONES_LABELS[k]: objetivo[k] for k in DIMENSIONES},
            color_usuario=p.color_primario,
            color_objetivo=p.color_acento,
        )
        logo = imagen_a_data_uri(self.base_datos / p.logo_path) if p.logo_path else ""

        return self.env.get_template("informe.html").render(
            inf=inf,
            n=inf.narrativa,
            ev=inf.evaluacion,
            empresa=inf.empresa,
            persona=inf.persona,
            colores=p,
            radar_uri=png_a_data_uri(radar),
            logo_uri=logo,
            logo_height=self.cfg.LOGO_HEIGHT_PDF,
            firma_uri=imagen_a_data_uri(self.cfg.FIRMA_IMAGE),
            items=[
                {
                    "nombre": DIMENSIONES_LABELS[k],
                    "valor": round(dims[k]),
                    "objetivo": round(objetivo[k]),
                    "gap": inf.evaluacion.gaps[k],
                }
                for k in DIMENSIONES
            ],
            fortalezas=[DIMENSIONES_LABELS[k] for k in inf.evaluacion.fortalezas],
            fecha=fecha_es(),
            id_evaluacion=f"{inf.empresa_id.upper()}-{inf.persona.usuario_id}",
        )

    async def generar(self, browser: Browser, inf: Informe) -> Path:
        html = self.render_html(inf)
        self.cfg.pdf_dir.mkdir(parents=True, exist_ok=True)
        destino = self.cfg.pdf_dir / (
            f"Informe_{nombre_archivo_seguro(inf.empresa_id)}_"
            f"{nombre_archivo_seguro(inf.persona.usuario_id)}_"
            f"{nombre_archivo_seguro(inf.persona.nombre)}.pdf"
        )
        page = await browser.new_page()
        try:
            await page.set_content(html, wait_until="load")
            await page.pdf(path=str(destino), format="A4", print_background=True)
        finally:
            await page.close()
        return destino
