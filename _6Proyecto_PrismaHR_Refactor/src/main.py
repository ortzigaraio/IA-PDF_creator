"""
src/main.py — Controlador principal. Coordina la lectura, el procesamiento, 
la IA generativa y la exportación de manera eficiente.
"""
from __future__ import annotations
import asyncio
import json
import logging
import os
from typing import Dict, List

from playwright.sync_api import sync_playwright
from tqdm import tqdm

from src.ai_client import AIClient
from src.config import settings
from src.content_generator import ContentGenerator
from src.excel.consolidado import generar_excel_consolidado_equipo
from src.excel.individual import generar_excel_individual
from src.models import (
    DIMENSIONES,
    EmpresaInfo,
    ItemEquipo,
    ResultadoModel,
    UsuarioModel,
)
from src.pdf_generator import PDFGenerator
from src.processor import Processor

logger = logging.getLogger(__name__)


class PrismaEngine:
    """Motor central PrismaHR."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        if not self.api_key:
            raise ValueError("API KEY no proporcionada ni encontrada en entorno.")
            
        self.ai = AIClient(self.api_key)
        self.generator = ContentGenerator(self.ai)
        self.pdf_gen = PDFGenerator(template_dir=".")

    def run_batch_json(self, json_path: str):
        """Prepara el entorno y ejecuta el flujo asíncrono."""
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"No se encontró el archivo base: {json_path}")
            
        with open(json_path, "r", encoding="utf-8") as f:
            datos_completos = json.load(f)

        logger.info("Iniciando procesamiento BATCH...")
        asyncio.run(self._process_all(datos_completos))

    async def _process_all(self, datos_completos: Dict):
        """Itera empresas/clientes usando Playwright y asyncio."""
        os.makedirs(settings.OUTPUT_PDF_DIR, exist_ok=True)
        os.makedirs(settings.OUTPUT_EXCEL_DIR, exist_ok=True)

        with sync_playwright() as p:
            browser = p.chromium.launch()

            for api_empresa_id, data_empresa in datos_completos.get("empresas", {}).items():
                print(f"\\n[{api_empresa_id}] Analizando clientes...")
                # 1. Parse EmpresaInfo
                empresa_info = EmpresaInfo(**data_empresa.get("info", {}))
                
                clientes_raw = data_empresa.get("clientes", [])
                if not clientes_raw:
                    continue

                # 2. Recolectar scores globales para percentiles contextuales
                scores_equipo = {dim: [] for dim in DIMENSIONES}
                for c in clientes_raw:
                    for d in DIMENSIONES:
                        # Buscamos con/sin tilde
                        dim_dict = c.get("dimensiones", {})
                        val = dim_dict.get(d, dim_dict.get(
                            "comunicación" if d == "comunicacion" else "empatía" if d == "empatia" else d, 50.0
                        ))
                        scores_equipo[d].append(val)

                equipo_items: List[ItemEquipo] = []
                
                # Barra de progreso para visualización elegante
                for cliente_raw in tqdm(clientes_raw, desc="Generando reportes", unit="usr"):
                    # 3. Parse Usuario
                    dim_data = cliente_raw.get("dimensiones", {})
                    # Forzar compatibilidad con tildes desde JSON via dict update si es estrictamente necesario,
                    # Pydantic v2 aliases se encargará
                    usuario = UsuarioModel(
                        usuario_id=cliente_raw.get("id", "U00"),
                        nombre=cliente_raw.get("nombre", "Sin Nombre"),
                        empresa_id=api_empresa_id,
                        dimensiones=dim_data,
                        frases_predeterminadas=cliente_raw.get("frases_predeterminadas", [])
                    )

                    # 4. Asignar percentiles locales
                    usuario.percentiles = Processor.calcular_percentiles(usuario, scores_equipo)

                    # 5. Core Processor
                    features = Processor.extraer_features(usuario)
                    compatibilidad = Processor.calcular_compatibilidad(features, empresa_info)
                    veredicto, enfasis = Processor.decidir_veredicto(compatibilidad)

                    # 6. Generación de Contenido Asíncrono en Paralelo (Groq x6)
                    contenido = await self.generator.generar_todo(usuario, api_empresa_id, compatibilidad)

                    resultado = ResultadoModel(
                        usuario_id=usuario.usuario_id,
                        empresa_id=api_empresa_id,
                        compatibilidad=compatibilidad,
                        veredicto=veredicto,
                        perfil_objetivo=Processor.obtener_perfil_escalado(empresa_info),
                        features_usuario=features["features_dict"],
                        contenido=contenido,
                        puntos_enfasis=enfasis
                    )

                    # 7. Exports
                    self.pdf_gen.generate_pdf(browser, usuario, resultado, empresa_info)
                    generar_excel_individual(usuario, resultado, empresa_info)

                    # 8. Acumulador para consolidado
                    equipo_items.append(ItemEquipo(
                        usuario=usuario,
                        resultado=resultado,
                        empresa_info=empresa_info
                    ))

                # Generar consolidado al terminar la empresa
                if equipo_items:
                    print("Generando Excel consolidado maestro...")
                    path = generar_excel_consolidado_equipo(equipo_items, api_empresa_id)
                    print(f"MAESTRO GENERADO: {path}")

            browser.close()
