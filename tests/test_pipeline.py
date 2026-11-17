"""Prueba de extremo a extremo: genera PDF y Excel reales (sin IA)."""
from __future__ import annotations

import asyncio
import os

import pytest

from prismahr.config import Settings
from prismahr.pipeline import Motor, cargar_datos
from tests.conftest import RAIZ


def _chromium_disponible() -> bool:
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.mark.skipif(not _chromium_disponible(), reason="Playwright no instalado")
def test_lote_completo_con_plantillas(tmp_path):
    cfg = Settings(
        OUTPUT_DIR=tmp_path,
        TEMPLATES_DIR=RAIZ / "templates",
        CHROMIUM_PATH=os.environ.get("CHROMIUM_PATH"),
        LLM_PROVIDER="plantillas",
    )
    ruta = RAIZ / "datos" / "ejemplo.json"
    datos = cargar_datos(ruta)
    resumen = asyncio.run(Motor(cfg, proveedor=None).procesar(datos, ruta.parent))

    total = sum(len(e.clientes) for e in datos.empresas.values())
    assert not resumen.errores
    assert len(resumen.pdfs) == total
    assert len(resumen.excels) == len(datos.empresas)
    assert all(p.stat().st_size > 10_000 and p.read_bytes()[:4] == b"%PDF" for p in resumen.pdfs)
    assert len(list(cfg.auditoria_dir.glob("*.json"))) == total
