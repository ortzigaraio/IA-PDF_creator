"""
src/ai_client.py — Cliente Groq con retry automático y ejecución asíncrona.

Mejoras vs original:
- tenacity: reintenta hasta 3x con backoff exponencial ante errores de red/API
- run_in_executor: llama al SDK síncrono desde un thread pool sin bloquear el event loop
- Un único ThreadPoolExecutor compartido (no se crea uno por llamada)
"""
from __future__ import annotations
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from groq import Groq
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from src.config import settings

logger = logging.getLogger(__name__)

# Pool compartido — reutilizado en toda la vida del proceso
_executor = ThreadPoolExecutor(max_workers=12, thread_name_prefix="groq-worker")


class AIClient:
    """
    Wrapper sobre el SDK de Groq que expone tanto una API síncrona
    (con retry) como una API asíncrona (ejecutando en thread pool).
    """

    def __init__(self, api_key: str):
        self._groq = Groq(api_key=api_key)
        self.model = settings.GROQ_MODEL

    # ------------------------------------------------------------------
    # API síncrona con retry (usada internamente y por el servidor webhook)
    # ------------------------------------------------------------------
    @retry(
        stop=stop_after_attempt(settings.API_MAX_RETRIES),
        wait=wait_exponential(
            multiplier=1,
            min=settings.API_WAIT_MIN,
            max=settings.API_WAIT_MAX,
        ),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def call(self, prompt: str, max_tokens: int = 500) -> str:
        """Llamada síncrona con retry automático."""
        res = self._groq.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return res.choices[0].message.content.strip()

    # ------------------------------------------------------------------
    # API asíncrona — no bloquea el event loop
    # ------------------------------------------------------------------
    async def call_async(self, prompt: str, max_tokens: int = 500) -> str:
        """
        Ejecuta self.call() en el thread pool compartido,
        liberando el event loop para otras co-rutinas concurrentes.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            lambda: self.call(prompt, max_tokens),
        )

    # Fallback seguro para catch-all
    @staticmethod
    def fallback(text: str) -> str:
        return text
