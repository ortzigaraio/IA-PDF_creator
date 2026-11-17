"""
Reglas de negocio puras: sin IA, sin ficheros, sin red.

Todo lo que se DECIDE sobre una persona sale de aquí, con reglas fijas
y explicables. La IA solo redacta después (ver narrativa.py).
"""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from prismahr.models import DIMENSIONES, Empresa, Evaluacion, NivelRiesgo, Persona

# Umbrales del veredicto (compatibilidad 0-100)
UMBRAL_PROMOCION = 85.0
UMBRAL_FORMACION = 72.0
UMBRAL_CONSOLIDACION = 55.0

VEREDICTOS = {
    "promocion": "PROMOCIÓN DIRECTA",
    "formacion": "FORMACIÓN TÉCNICA RECOMENDADA",
    "consolidacion": "CONSOLIDACIÓN",
    "mejora": "PLAN DE MEJORA INMEDIATO",
}

# Umbrales del riesgo de desgaste (burnout) o salida
RIESGO_RESILIENCIA_ALTO = 65.0
RIESGO_RESILIENCIA_MEDIO = 80.0
RIESGO_EMPATIA_MEDIO = 65.0


def calcular_compatibilidad(dimensiones: Dict[str, float], objetivo_100: Dict[str, float]) -> float:
    """
    Compatibilidad = 100 − media de |persona − objetivo|, todo en escala 0-100.
    (Es la misma fórmula del proyecto original, expresada sin cambios de escala.)
    """
    diffs = [abs(dimensiones[k] - objetivo_100[k]) for k in DIMENSIONES]
    return round(max(0.0, 100.0 - sum(diffs) / len(diffs)), 1)


def decidir_veredicto(compatibilidad: float) -> str:
    if compatibilidad >= UMBRAL_PROMOCION:
        return VEREDICTOS["promocion"]
    if compatibilidad >= UMBRAL_FORMACION:
        return VEREDICTOS["formacion"]
    if compatibilidad >= UMBRAL_CONSOLIDACION:
        return VEREDICTOS["consolidacion"]
    return VEREDICTOS["mejora"]


def evaluar_riesgo(dimensiones: Dict[str, float]) -> Tuple[NivelRiesgo, List[str]]:
    """Riesgo de desgaste o salida a partir de resiliencia y empatía."""
    res, emp = dimensiones["resiliencia"], dimensiones["empatia"]
    motivos: List[str] = []
    if res < RIESGO_RESILIENCIA_ALTO:
        motivos.append(f"resiliencia {res:.0f} < {RIESGO_RESILIENCIA_ALTO:.0f}")
        return "ALTO", motivos
    if res < RIESGO_RESILIENCIA_MEDIO:
        motivos.append(f"resiliencia {res:.0f} < {RIESGO_RESILIENCIA_MEDIO:.0f}")
    if emp < RIESGO_EMPATIA_MEDIO:
        motivos.append(f"empatía {emp:.0f} < {RIESGO_EMPATIA_MEDIO:.0f}")
    if motivos:
        return "MEDIO", motivos
    return "BAJO", [f"resiliencia {res:.0f} y empatía {emp:.0f} en niveles estables"]


def calcular_gaps(dimensiones: Dict[str, float], objetivo_100: Dict[str, float]) -> Dict[str, float]:
    return {k: round(dimensiones[k] - objetivo_100[k], 1) for k in DIMENSIONES}


def elegir_fortalezas(dimensiones: Dict[str, float], objetivo_100: Dict[str, float], n: int = 3) -> List[str]:
    """Las n dimensiones con mayor puntuación (empate: la que más pesa en el perfil)."""
    return sorted(DIMENSIONES, key=lambda k: (-dimensiones[k], -objetivo_100[k], k))[:n]


def elegir_areas_mejora(gaps: Dict[str, float], objetivo_100: Dict[str, float], n: int = 2) -> List[str]:
    """Las n dimensiones más por debajo del objetivo (empate: la que más pesa)."""
    return sorted(DIMENSIONES, key=lambda k: (gaps[k], -objetivo_100[k], k))[:n]


def calcular_percentiles(dimensiones: Dict[str, float], equipo: Sequence[Dict[str, float]]) -> Dict[str, float]:
    """% de personas del equipo con puntuación menor o igual en cada dimensión."""
    if not equipo:
        return {k: 100.0 for k in DIMENSIONES}
    return {
        k: round(sum(1 for d in equipo if d[k] <= dimensiones[k]) / len(equipo) * 100, 1)
        for k in DIMENSIONES
    }


def evaluar(persona: Persona, empresa: Empresa) -> Evaluacion:
    dims = persona.dimensiones
    objetivo = empresa.perfil_objetivo_100()
    compat = calcular_compatibilidad(dims, objetivo)
    gaps = calcular_gaps(dims, objetivo)
    nivel, motivos = evaluar_riesgo(dims)
    return Evaluacion(
        compatibilidad=compat,
        promedio=round(sum(dims.values()) / len(dims), 1),
        veredicto=decidir_veredicto(compat),
        nivel_riesgo=nivel,
        motivos_riesgo=motivos,
        gaps=gaps,
        percentiles=calcular_percentiles(dims, [p.dimensiones for p in empresa.clientes]),
        fortalezas=elegir_fortalezas(dims, objetivo),
        areas_mejora=elegir_areas_mejora(gaps, objetivo),
    )
