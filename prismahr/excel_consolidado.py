"""
Excel consolidado por empresa: ranking, mapa de calor y detalle de textos.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import List

import openpyxl
from openpyxl.drawing.image import Image as OxlImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from prismahr.charts import heatmap_equipo_bytes, ranking_equipo_bytes
from prismahr.models import DIMENSIONES, DIMENSIONES_LABELS, Informe
from prismahr.pdf import nombre_archivo_seguro

_FINO = Side(style="thin", color="D1D5DB")
BORDE = Border(left=_FINO, right=_FINO, top=_FINO, bottom=_FINO)
CLARO = PatternFill("solid", fgColor="F8FAFC")
RIESGO_ESTILO = {
    "ALTO": (PatternFill("solid", fgColor="FEE2E2"), Font(bold=True, color="DC2626")),
    "MEDIO": (PatternFill("solid", fgColor="FEF3C7"), Font(bold=True, color="B45309")),
    "BAJO": (PatternFill("solid", fgColor="DCFCE7"), Font(bold=True, color="16A34A")),
}
MEDALLAS = ["FFD700", "C0C0C0", "CD7F32"]


def _titulo(ws: Worksheet, rango: str, texto: str, color: str) -> None:
    ws.merge_cells(rango)
    c = ws[rango.split(":")[0]]
    c.value = texto
    c.font = Font(bold=True, size=14, color="FFFFFF")
    c.fill = PatternFill("solid", fgColor=color)
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 34


def _cabeceras(ws: Worksheet, fila: int, textos: List[str], color: str) -> None:
    for col, t in enumerate(textos, 1):
        c = ws.cell(row=fila, column=col, value=t)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=color)
        c.border = BORDE
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _anchos(ws: Worksheet, anchos: List[float]) -> None:
    for i, w in enumerate(anchos, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def _imagen(ws: Worksheet, png: bytes, celda: str) -> None:
    ws.add_image(OxlImage(io.BytesIO(png)), celda)


def generar_excel_consolidado(informes: List[Informe], destino_dir: Path) -> Path:
    if not informes:
        raise ValueError("No hay informes para consolidar")

    empresa = informes[0].empresa
    empresa_id = informes[0].empresa_id
    cp = empresa.plantilla.color_primario.lstrip("#").upper()
    ordenados = sorted(informes, key=lambda i: i.evaluacion.compatibilidad, reverse=True)
    wb = openpyxl.Workbook()

    # ---------------- Hoja 1: ranking ----------------
    ws = wb.active
    ws.title = "Ranking"
    _titulo(ws, "A1:J1", f"RANKING DE COMPATIBILIDAD — {empresa.nombre.upper()}", cp)
    _cabeceras(ws, 3, [
        "Posición", "ID", "Persona", "Compatibilidad (%)", "Media",
        "Veredicto", "Riesgo", "Fortalezas", "Áreas de mejora", "Textos redactados por",
    ], cp)
    for pos, inf in enumerate(ordenados, 1):
        ev = inf.evaluacion
        fila = [
            pos, inf.persona.usuario_id, inf.persona.nombre, ev.compatibilidad, ev.promedio,
            ev.veredicto, ev.nivel_riesgo,
            ", ".join(DIMENSIONES_LABELS[k] for k in ev.fortalezas),
            ", ".join(DIMENSIONES_LABELS[k] for k in ev.areas_mejora),
            inf.fuente_narrativa,
        ]
        r = 3 + pos
        for col, val in enumerate(fila, 1):
            c = ws.cell(row=r, column=col, value=val)
            c.border = BORDE
            c.alignment = Alignment(horizontal="center" if col in (1, 2, 4, 5, 7) else "left", vertical="center")
            if pos % 2 == 0:
                c.fill = CLARO
        if pos <= 3:
            ws.cell(row=r, column=1).fill = PatternFill("solid", fgColor=MEDALLAS[pos - 1])
        relleno, fuente = RIESGO_ESTILO[ev.nivel_riesgo]
        ws.cell(row=r, column=7).fill = relleno
        ws.cell(row=r, column=7).font = fuente
    _anchos(ws, [10, 12, 24, 16, 10, 32, 10, 40, 32, 34])
    ws.freeze_panes = "A4"
    _imagen(ws, ranking_equipo_bytes(
        [i.persona.nombre for i in ordenados],
        [i.evaluacion.compatibilidad for i in ordenados],
        empresa.plantilla.color_primario, empresa.plantilla.color_acento, "#dc2626", empresa.nombre,
    ), f"A{len(ordenados) + 6}")

    # ---------------- Hoja 2: mapa de calor ----------------
    wh = wb.create_sheet("Mapa de calor")
    _titulo(wh, "A1:I1", "MAPA DE CALOR — COMPETENCIAS DEL EQUIPO", cp)
    _cabeceras(wh, 3, ["Persona"] + [DIMENSIONES_LABELS[k] for k in DIMENSIONES] + ["Objetivo"], cp)
    objetivo = empresa.perfil_objetivo_100()
    filas = [(i.persona.nombre, [i.persona.dimensiones[k] for k in DIMENSIONES]) for i in ordenados]
    filas.append(("PERFIL OBJETIVO", [objetivo[k] for k in DIMENSIONES]))
    for r, (nombre, vals) in enumerate(filas, 4):
        wh.cell(row=r, column=1, value=nombre).font = Font(bold=True)
        for c_i, v in enumerate(vals, 2):
            c = wh.cell(row=r, column=c_i, value=v)
            c.border = BORDE
            c.alignment = Alignment(horizontal="center")
            ratio = v / 100.0
            rgb = (int(220 * (1 - ratio) + 22 * ratio), int(38 * (1 - ratio) + 163 * ratio), int(38 * (1 - ratio) + 74 * ratio))
            c.fill = PatternFill("solid", fgColor="%02X%02X%02X" % rgb)
            luminancia = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
            c.font = Font(bold=True, color="FFFFFF" if luminancia < 140 else "000000")
    _anchos(wh, [24] + [15] * 8)
    _imagen(wh, heatmap_equipo_bytes(
        [n for n, _ in filas[:-1]], [DIMENSIONES_LABELS[k] for k in DIMENSIONES], [v for _, v in filas[:-1]],
    ), f"A{len(filas) + 6}")

    # ---------------- Hoja 3: detalle de textos ----------------
    wd = wb.create_sheet("Detalle")
    _titulo(wd, "A1:F1", "DETALLE DE DICTÁMENES (revisar antes de decidir)", cp)
    _cabeceras(wd, 3, ["Persona", "Veredicto", "Dictamen", "Riesgo", "Puntos de atención", "Catalizadores"], cp)
    for r, inf in enumerate(ordenados, 4):
        n = inf.narrativa
        valores = [
            inf.persona.nombre, inf.evaluacion.veredicto, n.resumen_dictamen,
            f"{inf.evaluacion.nivel_riesgo}: {n.justificacion_riesgo}",
            "\n".join(n.puntos_criticos), "\n".join(n.catalizadores),
        ]
        for col, val in enumerate(valores, 1):
            c = wd.cell(row=r, column=col, value=val)
            c.border = BORDE
            c.alignment = Alignment(wrap_text=True, vertical="top")
    _anchos(wd, [22, 26, 60, 45, 50, 50])
    wd.freeze_panes = "A4"

    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / f"Consolidado_{nombre_archivo_seguro(empresa_id)}.xlsx"
    wb.save(destino)
    return destino
