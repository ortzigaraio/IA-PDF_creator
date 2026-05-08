"""
src/charts.py — Generación centralizada de gráficos matplotlib.

Todas las funciones devuelven bytes PNG puros.
El caller los convierte a archivo temporal sólo cuando lo necesita
(Excel) usando el context manager temp_png().

Mejoras vs original:
- Sin side-effects de I/O — funciones puras que retornan bytes
- Context manager temp_png() garantiza limpieza aunque haya excepciones
- Funciones independientes y testeables
"""
from __future__ import annotations
import io
import os
import tempfile
from contextlib import contextmanager
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


# ------------------------------------------------------------------
# Context manager para archivos temporales garantizados
# ------------------------------------------------------------------
@contextmanager
def temp_png(png_bytes: bytes, prefix: str = "prisma_"):
    """
    Escribe bytes en un archivo .png temporal y cede su ruta.
    Garantiza la eliminación del archivo aunque ocurra una excepción.

    Uso:
        with temp_png(chart_bytes) as path:
            img = OpenpyxlImage(path)
    """
    tmp = tempfile.NamedTemporaryFile(
        suffix=".png", prefix=prefix, delete=False
    )
    try:
        tmp.write(png_bytes)
        tmp.flush()
        tmp.close()
        yield tmp.name
    finally:
        if os.path.exists(tmp.name):
            os.remove(tmp.name)


# ------------------------------------------------------------------
# Utilidad interna para guardar figura a bytes
# ------------------------------------------------------------------
def _fig_to_bytes(fig: plt.Figure, dpi: int = 100) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ------------------------------------------------------------------
# 1. Radar (PDF + Excel individual)
# ------------------------------------------------------------------
def radar_bytes(
    dimensiones: Dict[str, float],
    dimensiones_objetivo: Optional[Dict[str, float]] = None,
    color_usuario: str = "#1e40af",
    color_objetivo: str = "#f59e0b",
) -> bytes:
    etiquetas = list(dimensiones.keys())
    valores = list(dimensiones.values())
    angulos = np.linspace(0, 2 * np.pi, len(etiquetas), endpoint=False).tolist()
    valores_c = valores + valores[:1]
    angulos_c = angulos + angulos[:1]

    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.fill(angulos_c, valores_c, color=color_usuario, alpha=0.35)
    ax.plot(angulos_c, valores_c, color=color_usuario, linewidth=2, label="Usuario")

    if dimensiones_objetivo:
        vals_o = list(dimensiones_objetivo.values()) + [list(dimensiones_objetivo.values())[0]]
        ax.plot(angulos_c, vals_o, color=color_objetivo, linewidth=2, linestyle="--", label="Objetivo")
        ax.fill(angulos_c, vals_o, color=color_objetivo, alpha=0.15)

    ax.set_yticklabels([])
    ax.set_xticks(angulos)
    ax.set_xticklabels(etiquetas, fontsize=8, color="#4b5563")
    ax.grid(True, color="#d1d5db", linewidth=0.5)
    ax.set_ylim(0, 100)
    if dimensiones_objetivo:
        ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=8)

    return _fig_to_bytes(fig, dpi=100)


# ------------------------------------------------------------------
# 2. Radar en Base64 (para HTML/PDF via Jinja2)
# ------------------------------------------------------------------
def radar_base64(
    dimensiones: Dict[str, float],
    dimensiones_objetivo: Optional[Dict[str, float]] = None,
) -> str:
    import base64
    return base64.b64encode(radar_bytes(dimensiones, dimensiones_objetivo)).decode("utf-8")


# ------------------------------------------------------------------
# 3. Barras comparativas usuario vs objetivo
# ------------------------------------------------------------------
def barras_comparativas_bytes(
    dim_labels: List[str],
    valores_usuario: List[float],
    valores_objetivo: List[float],
    color_usuario: str = "#1e40af",
    color_objetivo: str = "#f59e0b",
) -> bytes:
    x = np.arange(len(dim_labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(x - width / 2, valores_usuario, width, label="Usuario", color=color_usuario)
    ax.bar(x + width / 2, valores_objetivo, width, label="Objetivo", color=color_objetivo)
    ax.set_ylabel("Puntuación (0-100)")
    ax.set_title("Perfil Usuario vs Perfil Objetivo")
    ax.set_xticks(x)
    ax.set_xticklabels(dim_labels, rotation=45, ha="right", fontsize=9)
    ax.legend()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_to_bytes(fig, dpi=90)


# ------------------------------------------------------------------
# 4. Scatter / Matriz de prioridades
# ------------------------------------------------------------------
def scatter_prioridades_bytes(
    dim_labels: List[str],
    valores_usuario: List[float],
    valores_objetivo: List[float],
    color: str = "#f59e0b",
) -> bytes:
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(valores_usuario, valores_objetivo, color=color, s=110, zorder=3)
    ax.axhline(y=70, color="gray", linestyle="--", alpha=0.5)
    ax.axvline(x=70, color="gray", linestyle="--", alpha=0.5)
    for i, lbl in enumerate(dim_labels):
        ax.annotate(lbl, (valores_usuario[i], valores_objetivo[i]),
                    xytext=(5, 5), textcoords="offset points", fontsize=8)
    ax.set_title("Matriz de Prioridades Estratégicas")
    ax.set_xlabel("Desempeño del Candidato")
    ax.set_ylabel("Exigencia del Rol (Objetivo)")
    ax.set_xlim(0, 110)
    ax.set_ylim(0, 110)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_to_bytes(fig, dpi=90)


# ------------------------------------------------------------------
# 5. Coxcomb (polar de áreas)
# ------------------------------------------------------------------
def coxcomb_bytes(
    dim_labels: List[str],
    valores: List[float],
    cmap: str = "Blues",
) -> bytes:
    n = len(dim_labels)
    ancho = (2 * np.pi) / n
    angulos = np.linspace(0, 2 * np.pi, n, endpoint=False)
    colores = plt.get_cmap(cmap)(np.linspace(0.4, 0.9, n))

    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.bar(angulos, valores, width=ancho, bottom=0.0, color=colores, alpha=0.85, edgecolor="white")
    ax.set_xticks(angulos)
    ax.set_xticklabels(dim_labels, fontsize=8)
    ax.set_yticklabels([])
    ax.set_title("Volumen de Competencias Consolidadas", va="bottom", fontsize=10)
    return _fig_to_bytes(fig, dpi=90)


# ------------------------------------------------------------------
# 6. Mapa de Gaps (barras horizontales con colores semánticos)
# ------------------------------------------------------------------
def gaps_bytes(
    dim_labels: List[str],
    gaps: List[float],
) -> bytes:
    colores = ["#16a34a" if g >= 0 else "#dc2626" for g in gaps]

    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f8fafc")

    bars = ax.barh(dim_labels, gaps, color=colores, edgecolor="white", linewidth=1.5, height=0.6)
    ax.axvline(x=0, color="#374151", linewidth=1.5)

    for bar, val in zip(bars, gaps):
        xpos = bar.get_width()
        offset = 1.5 if xpos >= 0 else -1.5
        ha = "left" if xpos >= 0 else "right"
        ax.text(xpos + offset, bar.get_y() + bar.get_height() / 2,
                f"{val:+.1f}", va="center", ha=ha, fontsize=9,
                color="#111827", fontweight="bold")

    x_pad = 15
    ax.set_xlim(min(gaps) - x_pad, max(gaps) + x_pad)
    ax.set_xlabel("Gap (+ superior al objetivo  /  − inferior al objetivo)", fontsize=9, color="#6b7280")
    ax.set_title("Mapa de Gaps — Desviación del Perfil Objetivo",
                 fontsize=12, fontweight="bold", color="#1e3a5f", pad=12)
    ax.grid(axis="x", linestyle="--", alpha=0.4, color="#d1d5db")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    legend = [
        mpatches.Patch(facecolor="#16a34a", label="Superior al objetivo"),
        mpatches.Patch(facecolor="#dc2626", label="Inferior al objetivo"),
    ]
    ax.legend(handles=legend, loc="lower right", fontsize=8)
    fig.tight_layout()
    return _fig_to_bytes(fig, dpi=100)


# ------------------------------------------------------------------
# 7. Ranking de equipo (barras horizontales comparativas)
# ------------------------------------------------------------------
def ranking_equipo_bytes(
    nombres: List[str],
    compatibilidades: List[float],
    color_alta: str = "#1e40af",
    color_media: str = "#f59e0b",
    color_baja: str = "#dc2626",
    empresa_nombre: str = "",
) -> bytes:
    colores = [
        color_alta if c >= 75 else color_media if c >= 55 else color_baja
        for c in compatibilidades
    ]
    nombres_inv = nombres[::-1]
    vals_inv = compatibilidades[::-1]
    colores_inv = colores[::-1]

    fig, ax = plt.subplots(figsize=(10, max(4, len(nombres) * 0.7)))
    bars = ax.barh(nombres_inv, vals_inv, color=colores_inv, height=0.55, edgecolor="white")
    for bar, val in zip(bars, vals_inv):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val}%", va="center", ha="left", fontsize=9, fontweight="bold")
    ax.set_xlim(0, 115)
    ax.axvline(x=75, color="gray", linestyle="--", alpha=0.4, linewidth=1)
    ax.set_title(f"Ranking de Compatibilidad — {empresa_nombre}",
                 fontsize=13, fontweight="bold", color="#1e3a5f", pad=10)
    ax.set_xlabel("Compatibilidad con el Perfil Objetivo (%)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    legend = [
        mpatches.Patch(facecolor=color_alta,  label="Alta (≥75%)"),
        mpatches.Patch(facecolor=color_media, label="Media (55-74%)"),
        mpatches.Patch(facecolor=color_baja,  label="Baja (<55%)"),
    ]
    ax.legend(handles=legend, loc="lower right", fontsize=8)
    fig.tight_layout()
    return _fig_to_bytes(fig, dpi=100)


# ------------------------------------------------------------------
# 8. Heatmap del equipo
# ------------------------------------------------------------------
def heatmap_equipo_bytes(
    nombres: List[str],
    dim_labels: List[str],
    matrix: List[List[float]],
) -> bytes:
    arr = np.array(matrix)
    fig, ax = plt.subplots(
        figsize=(max(8, len(dim_labels) * 1.2), max(4, len(nombres) * 0.8))
    )
    im = ax.imshow(arr, cmap="RdYlGn", aspect="auto", vmin=0, vmax=100)
    plt.colorbar(im, ax=ax, shrink=0.8, label="Puntuación (0-100)")
    ax.set_xticks(range(len(dim_labels)))
    ax.set_xticklabels(dim_labels, rotation=35, ha="right", fontsize=9)
    ax.set_yticks(range(len(nombres)))
    ax.set_yticklabels(nombres, fontsize=9)
    ax.set_title("Heatmap de Competencias del Equipo",
                 fontsize=13, fontweight="bold", color="#1e3a5f", pad=12)
    for i in range(len(nombres)):
        for j in range(len(dim_labels)):
            val = arr[i, j]
            ax.text(j, i, f"{val:.0f}", ha="center", va="center",
                    fontsize=9, fontweight="bold",
                    color="white" if val < 50 else "black")
    fig.tight_layout()
    return _fig_to_bytes(fig, dpi=110)
