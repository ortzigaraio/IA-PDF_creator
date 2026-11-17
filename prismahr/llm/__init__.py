"""Capa de IA multiproveedor. Se elige con LLM_PROVIDER en el .env."""
from __future__ import annotations

from typing import Optional

from prismahr.config import Settings
from prismahr.llm.base import ProveedorLLM, RespuestaInvalida

__all__ = ["ProveedorLLM", "RespuestaInvalida", "crear_proveedor"]


def crear_proveedor(cfg: Settings) -> Optional[ProveedorLLM]:
    """Devuelve el proveedor configurado, o None si se usan solo plantillas."""
    if cfg.LLM_PROVIDER == "plantillas":
        return None

    from prismahr.llm import proveedores as p

    clases = {
        "groq": p.GroqProveedor,
        "anthropic": p.AnthropicProveedor,
        "openai": p.OpenAIProveedor,
        "gemini": p.GeminiProveedor,
    }
    try:
        return clases[cfg.LLM_PROVIDER](cfg.modelo, cfg.LLM_MAX_TOKENS, cfg.LLM_TIMEOUT)
    except ImportError as exc:
        raise SystemExit(
            f"Falta el SDK de '{cfg.LLM_PROVIDER}'. Instálalo con: "
            f"pip install -e '.[{cfg.LLM_PROVIDER}]'"
        ) from exc
    except Exception as exc:  # p. ej. falta la clave en el entorno
        raise SystemExit(
            f"No se pudo iniciar el proveedor '{cfg.LLM_PROVIDER}': {exc}\n"
            "Revisa que la clave correspondiente esté en tu fichero .env."
        ) from exc
