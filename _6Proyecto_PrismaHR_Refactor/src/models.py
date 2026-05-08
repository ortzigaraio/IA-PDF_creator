"""
src/models.py — Modelos de datos con Pydantic v2.

Mejoras vs dataclass original:
- Validación automática de rangos (0-100)
- Nombres de campo sin tildes (bug-prone en Python)
- Aliases para leer JSON con tildes (comunicación, empatía)
- Serialización/deserialización gratuita
"""
from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, AliasChoices, ConfigDict

# Claves internas (sin tildes) ↔ labels para display (con tildes)
DIMENSIONES: List[str] = [
    "adaptabilidad", "comunicacion", "creatividad",
    "disciplina", "empatia", "iniciativa", "resiliencia",
]
DIMENSIONES_LABELS: Dict[str, str] = {
    "adaptabilidad": "Adaptabilidad",
    "comunicacion":  "Comunicación",
    "creatividad":   "Creatividad",
    "disciplina":    "Disciplina",
    "empatia":       "Empatía",
    "iniciativa":    "Iniciativa",
    "resiliencia":   "Resiliencia",
}


class DimensionesModel(BaseModel):
    """Scores 0-100 por dimensión. Acepta claves con o sin tilde vía aliases."""
    model_config = ConfigDict(populate_by_name=True)

    adaptabilidad: float = Field(50.0, ge=0, le=100)
    comunicacion:  float = Field(
        50.0, ge=0, le=100,
        validation_alias=AliasChoices("comunicacion", "comunicación"),
    )
    creatividad:   float = Field(50.0, ge=0, le=100)
    disciplina:    float = Field(50.0, ge=0, le=100)
    empatia:       float = Field(
        50.0, ge=0, le=100,
        validation_alias=AliasChoices("empatia", "empatía"),
    )
    iniciativa:    float = Field(50.0, ge=0, le=100)
    resiliencia:   float = Field(50.0, ge=0, le=100)

    def score_promedio(self) -> float:
        return sum(self.model_dump().values()) / len(DIMENSIONES)

    def as_display_dict(self) -> Dict[str, float]:
        """Devuelve {label_con_tilde: valor} para gráficos."""
        raw = self.model_dump()
        return {DIMENSIONES_LABELS[k]: raw[k] for k in DIMENSIONES}

    def get(self, key: str, default: float = 0.0) -> float:
        """Acceso seguro por clave interna (sin tilde)."""
        return getattr(self, key, default)


class UsuarioModel(BaseModel):
    """Perfil completo de un candidato."""
    usuario_id: str
    nombre: str
    empresa_id: str
    dimensiones: DimensionesModel
    frases_predeterminadas: List[str] = []
    percentiles: Dict[str, float] = {}


class PlantillaEmpresa(BaseModel):
    color_primario:   str = "#1e40af"
    color_secundario: str = "#3b82f6"
    color_acento:     str = "#f59e0b"
    logo_url:         str = ""
    fuente_principal: str = "Inter"


class EmpresaInfo(BaseModel):
    nombre: str = "Empresa"
    sector: str = ""
    plantilla: PlantillaEmpresa = PlantillaEmpresa()
    pesos_perfil_objetivo: Dict[str, float] = {}

    def perfil_objetivo_escalado(self) -> Dict[str, float]:
        """Convierte pesos 0-10 → scores 0-100, normalizando claves a sin tilde."""
        result = {}
        mapping = {"comunicación": "comunicacion", "empatía": "empatia"}
        for k, v in self.pesos_perfil_objetivo.items():
            clean_k = mapping.get(k, k)
            result[clean_k] = v * 10
        return result


class ContenidoModel(BaseModel):
    """Contenido generado por IA para un usuario."""
    analisis_bloques:       List[str]
    descripcion_recom:      str
    fortalezas:             List[str]
    puntos_criticos:        List[str]
    catalizadores_crecimiento: List[str]
    alerta_riesgo:          str


class ResultadoModel(BaseModel):
    """Resultado completo del procesamiento de un usuario."""
    usuario_id:      str
    empresa_id:      str
    compatibilidad:  float
    veredicto:       str
    perfil_objetivo: Dict[str, float]   # claves sin tilde, escala 0-100
    features_usuario: Dict[str, float]
    contenido:       ContenidoModel
    puntos_enfasis:  List[str]


class ItemEquipo(BaseModel):
    """Unidad atómica del acumulador de equipo."""
    usuario:       UsuarioModel
    resultado:     ResultadoModel
    empresa_info:  EmpresaInfo
