"""
src/config.py — Gestión centralizada de configuración con pydantic-settings.
Lee variables desde .env con validación automática de tipos.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    GROQ_MAX_TOKENS_BLOQUES: int = 600
    GROQ_MAX_TOKENS_CORTO: int = 200
    GROQ_MAX_TOKENS_MEDIO: int = 300
    GROQ_MAX_TOKENS_LARGO: int = 800
    API_MAX_RETRIES: int = 3
    API_WAIT_MIN: float = 1.0
    API_WAIT_MAX: float = 10.0

    OUTPUT_EXCEL_DIR: str = "Salida_Excel"
    OUTPUT_PDF_DIR: str = "Salida_PDF"
    JSON_PERFILES: str = "datos_empresa.json"

    # Rutas de imágenes (fácil de cambiar)
    BRAND_LOGO: str = "logo.jpg"
    FIRMA_IMAGE: str = "firma blanco.png"
    
    # Ajustes de tamaño (opcional)
    LOGO_HEIGHT_PDF: int = 40   # Pixeles para el PDF
    LOGO_HEIGHT_EXCEL: int = 35 # Pixeles para el Excel

    @property
    def FECHA_ACTUAL(self) -> str:
        from datetime import datetime
        import locale
        try:
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        except:
            pass
        return datetime.now().strftime("%d de %B, %Y").lower()

    @property
    def YEAR(self) -> str:
        from datetime import datetime
        return str(datetime.now().year)


# Singleton accesible en todo el proyecto
settings = Settings()
