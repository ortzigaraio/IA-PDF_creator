"""
Interfaz común de los proveedores de IA.

Cada proveedor recibe instrucciones (system), datos (user) y un modelo
Pydantic, y devuelve una instancia de ese modelo ya validada. Si la IA
devuelve algo que no encaja, se lanza RespuestaInvalida.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class RespuestaInvalida(Exception):
    """La IA respondió, pero no con el formato pedido (o se negó a responder)."""


class ProveedorLLM(ABC):
    nombre: str = "base"

    def __init__(self, modelo: str, max_tokens: int, timeout: float):
        self.modelo = modelo
        self.max_tokens = max_tokens
        self.timeout = timeout

    @property
    def etiqueta(self) -> str:
        return f"{self.nombre}:{self.modelo}"

    @abstractmethod
    async def generar(self, system: str, user: str, esquema: Type[T]) -> T:
        ...


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parsear_json(texto: str | None, esquema: Type[T]) -> T:
    """Valida texto JSON contra el esquema (tolera bloques ```json ... ```)."""
    if not texto:
        raise RespuestaInvalida("respuesta vacía")
    limpio = _FENCE.sub("", texto.strip())
    try:
        return esquema.model_validate(json.loads(limpio))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise RespuestaInvalida(f"JSON no válido: {exc}") from exc
