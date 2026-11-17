from __future__ import annotations

import asyncio
import json

import openpyxl

from prismahr import scoring
from prismahr.config import Settings
from prismahr.excel_consolidado import generar_excel_consolidado
from prismahr.llm.base import RespuestaInvalida, parsear_json
from prismahr.models import Informe, Narrativa
from prismahr.narrativa import MARCADOR, construir_entrada, generar_narrativa, seudonimizar
from prismahr.pdf import GeneradorPDF, nombre_archivo_seguro
from tests.conftest import RAIZ, ProveedorFalso, narrativa_ia


def _gen(persona, empresa, proveedor, reintentos=2):
    ev = scoring.evaluar(persona, empresa)
    return asyncio.run(generar_narrativa(persona, empresa, ev, proveedor, reintentos))


def test_seudonimizar_quita_nombre_completo_y_de_pila():
    assert seudonimizar("Ana López lidera; Ana escucha.", "Ana López") == f"{MARCADOR} lidera; {MARCADOR} escucha."


def test_la_ia_no_recibe_el_nombre_real(empresa):
    p = empresa.clientes[0]
    entrada = construir_entrada(p, empresa, scoring.evaluar(p, empresa))
    assert "Ana" not in entrada and "López" not in entrada
    datos = json.loads(entrada)
    assert datos["veredicto"] == "PROMOCIÓN DIRECTA"
    assert datos["observaciones_evaluador"] == [f"{MARCADOR} coordina muy bien al equipo."]


def test_una_sola_llamada_y_limpieza(empresa):
    prov = ProveedorFalso([narrativa_ia(puntos_criticos=["Solo uno."])])
    n, fuente = _gen(empresa.clientes[0], empresa, prov)
    assert len(prov.llamadas) == 1
    assert fuente == "falso:test"
    assert n.resumen_dictamen == "Ana López encaja muy bien."     # marcador sustituido
    assert n.analisis_fortalezas == "Gran disciplina."              # sin Markdown
    assert len(n.puntos_criticos) == 2                              # completado con respaldo


def test_reintenta_si_json_invalido_y_luego_acierta(empresa):
    prov = ProveedorFalso([RespuestaInvalida("mal"), narrativa_ia()])
    _, fuente = _gen(empresa.clientes[0], empresa, prov)
    assert len(prov.llamadas) == 2 and fuente == "falso:test"


def test_si_la_ia_falla_usa_plantillas_y_no_para_el_lote(empresa):
    prov = ProveedorFalso([ConnectionError("sin red")])
    n, fuente = _gen(empresa.clientes[1], empresa, prov)
    assert fuente.startswith("plantillas (respaldo")
    assert "Luis Pardo" in n.resumen_dictamen and MARCADOR not in n.resumen_dictamen


def test_sin_proveedor_usa_plantillas(empresa):
    n, fuente = _gen(empresa.clientes[0], empresa, None)
    assert fuente == "plantillas" and len(n.catalizadores) == 2


def test_parsear_json_tolera_bloque_markdown():
    texto = "```json\n" + narrativa_ia().model_dump_json() + "\n```"
    assert isinstance(parsear_json(texto, Narrativa), Narrativa)


def _informe(empresa, persona, narrativa):
    return Informe(
        empresa_id="emp", empresa=empresa, persona=persona,
        evaluacion=scoring.evaluar(persona, empresa), narrativa=narrativa, fuente_narrativa="falso:test",
    )


def test_html_escapa_lo_que_escribe_la_ia(empresa, tmp_path):
    malicioso = narrativa_ia(analisis_liderazgo='<script>alert("x")</script>')
    cfg = Settings(TEMPLATES_DIR=RAIZ / "templates", OUTPUT_DIR=tmp_path)
    html = GeneradorPDF(cfg, tmp_path).render_html(_informe(empresa, empresa.clientes[0], malicioso))
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "http://" not in html and "https://" not in html      # no depende de internet
    assert "PROMOCIÓN DIRECTA" in html


def test_excel_consolidado(empresa, tmp_path):
    informes = [_informe(empresa, p, narrativa_ia()) for p in empresa.clientes]
    ruta = generar_excel_consolidado(informes, tmp_path)
    wb = openpyxl.load_workbook(ruta)
    assert wb.sheetnames == ["Ranking", "Mapa de calor", "Detalle"]
    ws = wb["Ranking"]
    assert ws["C4"].value == "Ana López" and ws["G5"].value == "ALTO"


def test_nombre_archivo_seguro():
    assert nombre_archivo_seguro("José Pérez / Ventas") == "Jose_Perez_Ventas"
