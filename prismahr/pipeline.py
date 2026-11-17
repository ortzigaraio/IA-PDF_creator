"""
Orquestador: JSON → reglas → IA (redacción) → PDF por persona + Excel por empresa.

Varias personas se procesan a la vez (LLM_CONCURRENCY). Si una persona
falla, se registra el error y el lote continúa.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from playwright.async_api import Browser, async_playwright

from prismahr import scoring
from prismahr.config import Settings
from prismahr.excel_consolidado import generar_excel_consolidado
from prismahr.llm import ProveedorLLM, crear_proveedor
from prismahr.models import DatosEntrada, Empresa, Informe, Persona
from prismahr.narrativa import generar_narrativa
from prismahr.pdf import GeneradorPDF, nombre_archivo_seguro

logger = logging.getLogger(__name__)


@dataclass
class ResumenLote:
    pdfs: List[Path] = field(default_factory=list)
    excels: List[Path] = field(default_factory=list)
    errores: List[str] = field(default_factory=list)
    respaldos: int = 0      # personas cuyo texto salió de plantillas por un error de la IA


def cargar_datos(ruta: Path) -> DatosEntrada:
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe el fichero de datos: {ruta}")
    return DatosEntrada.model_validate_json(ruta.read_text(encoding="utf-8"))


def guardar_auditoria(cfg: Settings, inf: Informe) -> None:
    """Deja constancia de qué datos, reglas y fuente produjeron cada informe."""
    cfg.auditoria_dir.mkdir(parents=True, exist_ok=True)
    registro = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "empresa_id": inf.empresa_id,
        "usuario_id": inf.persona.usuario_id,
        "dimensiones": inf.persona.dimensiones,
        "perfil_objetivo": inf.empresa.perfil_objetivo_100(),
        "evaluacion": inf.evaluacion.model_dump(),
        "fuente_narrativa": inf.fuente_narrativa,
        "narrativa": inf.narrativa.model_dump(),
    }
    nombre = f"{nombre_archivo_seguro(inf.empresa_id)}_{nombre_archivo_seguro(inf.persona.usuario_id)}.json"
    (cfg.auditoria_dir / nombre).write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")


_DEL_CONFIG = object()


class Motor:
    def __init__(self, cfg: Settings, proveedor: Optional[ProveedorLLM] | object = _DEL_CONFIG):
        """proveedor: por defecto el del .env; None = solo plantillas; o uno propio (tests)."""
        self.cfg = cfg
        self.proveedor = crear_proveedor(cfg) if proveedor is _DEL_CONFIG else proveedor
        self.pdf: Optional[GeneradorPDF] = None
        self._sem = asyncio.Semaphore(max(1, cfg.LLM_CONCURRENCY))

    async def _procesar_persona(
        self, browser: Browser, empresa_id: str, empresa: Empresa, persona: Persona, resumen: ResumenLote,
    ) -> Optional[Informe]:
        async with self._sem:
            try:
                ev = scoring.evaluar(persona, empresa)
                narrativa, fuente = await generar_narrativa(
                    persona, empresa, ev, self.proveedor, self.cfg.LLM_MAX_RETRIES,
                )
                if fuente.startswith("plantillas (respaldo"):
                    resumen.respaldos += 1
                inf = Informe(
                    empresa_id=empresa_id, empresa=empresa, persona=persona,
                    evaluacion=ev, narrativa=narrativa, fuente_narrativa=fuente,
                )
                resumen.pdfs.append(await self.pdf.generar(browser, inf))
                guardar_auditoria(self.cfg, inf)
                logger.info("✔ %s/%s (%s%%, %s)", empresa_id, persona.usuario_id, ev.compatibilidad, fuente)
                return inf
            except Exception as exc:
                msg = f"{empresa_id}/{persona.usuario_id}: {exc}"
                logger.exception("✘ %s", msg)
                resumen.errores.append(msg)
                return None

    async def procesar(self, datos: DatosEntrada, base_datos: Path) -> ResumenLote:
        self.pdf = GeneradorPDF(self.cfg, base_datos)
        resumen = ResumenLote()
        async with async_playwright() as p:
            browser = await p.chromium.launch(executable_path=self.cfg.CHROMIUM_PATH or None)
            try:
                for empresa_id, empresa in datos.empresas.items():
                    logger.info("[%s] %d personas", empresa_id, len(empresa.clientes))
                    resultados = await asyncio.gather(*(
                        self._procesar_persona(browser, empresa_id, empresa, persona, resumen)
                        for persona in empresa.clientes
                    ))
                    informes = [r for r in resultados if r is not None]
                    if informes:
                        resumen.excels.append(generar_excel_consolidado(informes, self.cfg.excel_dir))
            finally:
                await browser.close()
        return resumen


def ejecutar(cfg: Settings, ruta_datos: Optional[Path] = None) -> ResumenLote:
    ruta = Path(ruta_datos or cfg.DATOS_JSON).resolve()
    datos = cargar_datos(ruta)
    return asyncio.run(Motor(cfg).procesar(datos, ruta.parent))
