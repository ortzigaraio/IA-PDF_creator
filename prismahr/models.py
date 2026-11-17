"""
Modelos de datos (Pydantic v2).

- Entrada: Empresa, Persona, DatosEntrada  → validan el JSON.
- Cálculo:  Evaluacion                       → lo que deciden las reglas.
- IA:       Narrativa                        → lo único que redacta la IA.
- Salida:   Informe                          → todo junto, listo para PDF/Excel.
"""
from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

# Claves internas (sin tildes) y etiquetas para mostrar (con tildes)
DIMENSIONES: List[str] = [
    "adaptabilidad", "comunicacion", "creatividad",
    "disciplina", "empatia", "iniciativa", "resiliencia",
]
DIMENSIONES_LABELS: Dict[str, str] = {
    "adaptabilidad": "Adaptabilidad",
    "comunicacion": "Comunicación",
    "creatividad": "Creatividad",
    "disciplina": "Disciplina",
    "empatia": "Empatía",
    "iniciativa": "Iniciativa",
    "resiliencia": "Resiliencia",
}

_SIN_TILDES = str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU")


def normalizar_clave(clave: str) -> str:
    """'Comunicación' → 'comunicacion'."""
    return clave.strip().lower().translate(_SIN_TILDES)


def _normalizar_dimensiones(valor: Dict[str, float], nombre_campo: str) -> Dict[str, float]:
    limpio = {normalizar_clave(k): float(v) for k, v in valor.items()}
    desconocidas = set(limpio) - set(DIMENSIONES)
    if desconocidas:
        raise ValueError(f"{nombre_campo}: dimensiones desconocidas {sorted(desconocidas)}")
    faltan = set(DIMENSIONES) - set(limpio)
    if faltan:
        raise ValueError(f"{nombre_campo}: faltan dimensiones {sorted(faltan)}")
    return {k: limpio[k] for k in DIMENSIONES}


# ----------------------------------------------------------------------
# Entrada
# ----------------------------------------------------------------------
class Plantilla(BaseModel):
    color_primario: str = "#1e40af"
    color_secundario: str = "#3b82f6"
    color_acento: str = "#f59e0b"
    logo_path: str = ""          # ruta local (relativa al JSON) a PNG/JPG/SVG

    @field_validator("color_primario", "color_secundario", "color_acento")
    @classmethod
    def _hex(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith("#"):
            v = "#" + v
        if len(v) != 7 or any(c not in "0123456789abcdefABCDEF" for c in v[1:]):
            raise ValueError(f"color no válido: {v!r} (usa formato #RRGGBB)")
        return v.lower()


class Persona(BaseModel):
    """Persona evaluada. Puntuaciones de 0 a 100 en las 7 dimensiones."""
    model_config = ConfigDict(populate_by_name=True)

    usuario_id: str = Field(validation_alias=AliasChoices("usuario_id", "id"))
    nombre: str
    dimensiones: Dict[str, float]
    frases_predeterminadas: List[str] = []

    @field_validator("dimensiones")
    @classmethod
    def _dims(cls, v: Dict[str, float]) -> Dict[str, float]:
        v = _normalizar_dimensiones(v, "dimensiones")
        for k, val in v.items():
            if not 0 <= val <= 100:
                raise ValueError(f"dimensiones.{k}={val} fuera de rango 0-100")
        return v


class Empresa(BaseModel):
    nombre: str
    sector: str = ""
    plantilla: Plantilla = Plantilla()
    pesos_perfil_objetivo: Dict[str, float]   # escala 0-10
    clientes: List[Persona] = []

    @field_validator("pesos_perfil_objetivo")
    @classmethod
    def _pesos(cls, v: Dict[str, float]) -> Dict[str, float]:
        v = _normalizar_dimensiones(v, "pesos_perfil_objetivo")
        for k, val in v.items():
            if not 0 <= val <= 10:
                raise ValueError(f"pesos_perfil_objetivo.{k}={val} fuera de rango 0-10")
        return v

    @model_validator(mode="after")
    def _ids_unicos(self) -> "Empresa":
        ids = [p.usuario_id for p in self.clientes]
        repetidos = {i for i in ids if ids.count(i) > 1}
        if repetidos:
            raise ValueError(f"usuario_id repetidos: {sorted(repetidos)}")
        return self

    def perfil_objetivo_100(self) -> Dict[str, float]:
        """Perfil objetivo en escala 0-100 (para comparar con las personas)."""
        return {k: v * 10 for k, v in self.pesos_perfil_objetivo.items()}


class DatosEntrada(BaseModel):
    empresas: Dict[str, Empresa]


# ----------------------------------------------------------------------
# Resultado de las reglas (sin IA)
# ----------------------------------------------------------------------
NivelRiesgo = Literal["BAJO", "MEDIO", "ALTO"]


class Evaluacion(BaseModel):
    compatibilidad: float                 # 0-100
    promedio: float                       # media de las 7 dimensiones
    veredicto: str
    nivel_riesgo: NivelRiesgo
    motivos_riesgo: List[str]
    gaps: Dict[str, float]                # persona - objetivo (0-100)
    percentiles: Dict[str, float]         # posición dentro del equipo
    fortalezas: List[str]                 # claves de dimensión (las 3 mejores)
    areas_mejora: List[str]               # claves (las 2 más por debajo del objetivo)


# ----------------------------------------------------------------------
# Lo que redacta la IA
# ----------------------------------------------------------------------
class Narrativa(BaseModel):
    """Textos del informe. La IA solo explica; no decide nada."""
    resumen_dictamen: str = Field(description="2-3 frases que justifican el veredicto ya decidido.")
    analisis_fortalezas: str = Field(description="2-3 frases sobre las fortalezas indicadas.")
    analisis_liderazgo: str = Field(description="2-3 frases sobre su potencial de liderazgo.")
    recomendacion_final: str = Field(description="2-3 frases con la recomendación de desarrollo.")
    puntos_criticos: List[str] = Field(description="Exactamente 2 frases, una por cada área de mejora indicada.")
    catalizadores: List[str] = Field(description="Exactamente 2 frases sobre cómo aprovechar las fortalezas.")
    justificacion_riesgo: str = Field(description="1-2 frases que explican el nivel de riesgo ya decidido.")


class Informe(BaseModel):
    empresa_id: str
    empresa: Empresa
    persona: Persona
    evaluacion: Evaluacion
    narrativa: Narrativa
    fuente_narrativa: str                 # "groq:llama-3.3-70b-versatile", "plantillas", ...
