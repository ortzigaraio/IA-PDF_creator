"""
Configuración centralizada. Se lee de variables de entorno o del fichero .env.

Ninguna clave se escribe en el código: cada proveedor de IA lee la suya
(GROQ_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent

Proveedor = Literal["groq", "anthropic", "openai", "gemini", "plantillas"]

# Modelo por defecto de cada proveedor. Se puede cambiar con LLM_MODEL.
MODELOS_POR_DEFECTO: dict[str, str] = {
    "groq": "llama-3.3-70b-versatile",
    "anthropic": "claude-opus-5-5",
    "openai": "gpt-5-mini",
    "gemini": "gemini-2.5-flash",
    "plantillas": "plantillas-deterministas",
}

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- IA -------------------------------------------------------------
    LLM_PROVIDER: Proveedor = "groq"
    LLM_MODEL: Optional[str] = None          # None → MODELOS_POR_DEFECTO
    LLM_MAX_TOKENS: int = 4000
    LLM_TIMEOUT: float = 60.0                # segundos por petición
    LLM_MAX_RETRIES: int = 2                 # reintentos ante JSON inválido
    LLM_CONCURRENCY: int = 4                 # personas procesadas a la vez

    # --- Rutas ----------------------------------------------------------
    DATOS_JSON: Path = RAIZ_PROYECTO / "datos" / "ejemplo.json"
    TEMPLATES_DIR: Path = RAIZ_PROYECTO / "templates"
    OUTPUT_DIR: Path = RAIZ_PROYECTO / "salida"
    FIRMA_IMAGE: Optional[Path] = None       # PNG opcional con la firma

    # Ruta a un Chromium ya instalado. Vacío = el que instala Playwright.
    CHROMIUM_PATH: Optional[str] = None

    LOGO_HEIGHT_PDF: int = 40

    @property
    def modelo(self) -> str:
        return self.LLM_MODEL or MODELOS_POR_DEFECTO[self.LLM_PROVIDER]

    @property
    def pdf_dir(self) -> Path:
        return self.OUTPUT_DIR / "pdf"

    @property
    def excel_dir(self) -> Path:
        return self.OUTPUT_DIR / "excel"

    @property
    def auditoria_dir(self) -> Path:
        return self.OUTPUT_DIR / "auditoria"


def fecha_es(d: Optional[date] = None) -> str:
    """Fecha en castellano sin depender del 'locale' del sistema."""
    d = d or date.today()
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


settings = Settings()
