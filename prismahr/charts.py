"""
Gráficos con matplotlib. Todas las funciones devuelven bytes PNG.
"""
from __future__ import annotations

import base64
import io
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib

matplotlib.use("Agg")  # sin pantalla: necesario en servidores y contenedores

import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def _fig_to_bytes(fig: plt.Figure, dpi: int = 100) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ------------------------------------------------------------------
# Radar (PDF)
# ------------------------------------------------------------------
def radar_bytes(
    dimensiones: Dict[str, float],
    dimensiones_objetivo: Optional[Dict[str, float]] = None,
    color_usuario: str = "#1e40af",
    color_objetivo: str = "#f59e0b",
) -> bytes:
    etiquetas = list(dimensiones.keys())
    valores = [dimensiones[k] for k in etiquetas]
    angulos = np.linspace(0, 2 * np.pi, len(etiquetas), endpoint=False).tolist()
    
    valores_c = valores + valores[:1]
    angulos_c = angulos + angulos[:1]

    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # Escala 0-100 visible
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=7, color="gray")

    # Perfil Candidato
    ax.fill(angulos_c, valores_c, color=color_usuario, alpha=0.3)
    ax.plot(angulos_c, valores_c, color=color_usuario, linewidth=3, label="Candidato")

    # Perfil Objetivo (Amarillo/Acento)
    if dimensiones_objetivo:
        # Asegurar mismo orden que etiquetas
        vals_o = [dimensiones_objetivo.get(k, 0.0) for k in etiquetas]
        vals_o_c = vals_o + vals_o[:1]
        ax.plot(angulos_c, vals_o_c, color=color_objetivo, linewidth=3, linestyle="-", label="Objetivo", alpha=0.8)
        ax.fill(angulos_c, vals_o_c, color=color_objetivo, alpha=0.1)

    ax.set_xticks(angulos)
    ax.set_xticklabels(etiquetas, fontsize=11, color="#374151", fontweight="bold")
    ax.grid(True, color="#d1d5db", linewidth=0.5, linestyle="--")
    
    if dimensiones_objetivo:
        ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=9, frameon=True)

    return _fig_to_bytes(fig, dpi=120)


# ------------------------------------------------------------------
# Utilidades Base64 (para incrustar en el HTML del PDF)
# ------------------------------------------------------------------
def png_a_data_uri(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def imagen_a_data_uri(path: Optional[Path]) -> str:
    """Imagen local → data URI con su tipo real (png, jpg, svg). '' si no existe."""
    if not path or not Path(path).is_file():
        return ""
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(Path(path).read_bytes()).decode("ascii")


# ------------------------------------------------------------------
# Ranking de equipo (barras horizontales comparativas)
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
# Mapa de calor del equipo
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
