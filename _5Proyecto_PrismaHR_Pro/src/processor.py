"""
src/processor.py — Lógica de negocio pura (sin IA, sin I/O).

Clases: AnalisadorParametros, ClasificadorHibrido, MotorDecision
Sin dependencias externas salvo los modelos propios.
"""
from __future__ import annotations
from typing import Dict, Tuple

from src.models import (
    DimensionesModel,
    EmpresaInfo,
    UsuarioModel,
    DIMENSIONES,
)


UMBRALES = {
    "promotion":     85.0,
    "training_hi":   85.0,
    "training_lo":   72.0,
    "consolidation": 55.0,
}


class Processor:
    """
    Responsabilidad única: convertir datos del candidato + empresa
    en una puntuación de compatibilidad y un veredicto ejecutivo.
    """

    # ------------------------------------------------------------------
    # Features
    # ------------------------------------------------------------------
    @staticmethod
    def extraer_features(usuario: UsuarioModel) -> Dict[str, float]:
        """Normaliza scores 0-100 → 0-1 y calcula promedio."""
        raw = usuario.dimensiones.model_dump()
        normalizado = {k: raw[k] / 100.0 for k in DIMENSIONES}
        avg = sum(normalizado.values()) / len(DIMENSIONES) * 100
        return {
            "vector": list(normalizado.values()),
            "avg_score": round(avg, 1),
            "features_dict": normalizado,
        }

    # ------------------------------------------------------------------
    # Compatibilidad
    # ------------------------------------------------------------------
    @staticmethod
    def calcular_compatibilidad(
        features: Dict,
        empresa_info: EmpresaInfo,
    ) -> float:
        """
        Compatibilidad = 100 - (promedio_diferencias × 10).
        Perfil objetivo en escala 0-10, usuario en 0-1 (×10 para equiparar).
        """
        objetivo = empresa_info.pesos_perfil_objetivo
        if not objetivo:
            return 0.0

        mapping = {"comunicación": "comunicacion", "empatía": "empatia"}
        feat = features["features_dict"]
        diffs = []
        for dim_json, peso in objetivo.items():
            dim_key = mapping.get(dim_json, dim_json)
            val_u = feat.get(dim_key, 0) * 10
            diffs.append(abs(val_u - peso))

        promedio = sum(diffs) / len(diffs) if diffs else 10
        return round(max(0.0, 100 - promedio * 10), 1)

    @staticmethod
    def obtener_perfil_escalado(empresa_info: EmpresaInfo) -> Dict[str, float]:
        """Devuelve perfil objetivo con claves sin tilde y escala 0-100."""
        return empresa_info.perfil_objetivo_escalado()

    # ------------------------------------------------------------------
    # Decisión
    # ------------------------------------------------------------------
    @staticmethod
    def decidir_veredicto(compatibilidad: float) -> Tuple[str, list]:
        if compatibilidad >= UMBRALES["promotion"]:
            veredicto = "PROMOCIÓN DIRECTA"
            enfasis = ["Considera rol de mentor"]
        elif compatibilidad < UMBRALES["consolidation"]:
            veredicto = "PLAN DE MEJORA INMEDIATO"
            enfasis = ["Requiere seguimiento"]
        elif UMBRALES["training_lo"] <= compatibilidad < UMBRALES["training_hi"]:
            veredicto = "FORMACIÓN TÉCNICA RECOMENDADA"
            enfasis = []
        else:
            veredicto = "CONSOLIDACIÓN"
            enfasis = []
        return veredicto, enfasis

    # ------------------------------------------------------------------
    # Percentiles contextuales (vs. equipo)
    # ------------------------------------------------------------------
    @staticmethod
    def calcular_percentiles(
        usuario: UsuarioModel,
        scores_equipo: Dict[str, list],
    ) -> Dict[str, float]:
        percentiles = {}
        raw = usuario.dimensiones.model_dump()
        for dim in DIMENSIONES:
            valor = raw.get(dim, 50)
            scores = scores_equipo.get(dim, [valor])
            count = sum(1 for s in scores if s <= valor)
            percentiles[dim] = round((count / len(scores)) * 100, 1)
        return percentiles
