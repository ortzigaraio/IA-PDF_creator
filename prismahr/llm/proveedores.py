"""
Implementación de cada proveedor con su SDK oficial.

Los SDK se importan dentro de cada clase: solo hace falta instalar el
del proveedor que uses. Cada SDK lee su clave de su variable de entorno
(GROQ_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY).
"""
from __future__ import annotations

import json
from typing import Type

from prismahr.llm.base import ProveedorLLM, RespuestaInvalida, T, parsear_json


def _esquema_en_texto(esquema: Type[T]) -> str:
    return (
        "\n\nResponde ÚNICAMENTE con un objeto JSON válido que cumpla este esquema:\n"
        + json.dumps(esquema.model_json_schema(), ensure_ascii=False)
    )


class GroqProveedor(ProveedorLLM):
    """Groq: modo JSON + validación con Pydantic."""
    nombre = "groq"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from groq import AsyncGroq
        self._client = AsyncGroq(timeout=self.timeout)

    async def generar(self, system: str, user: str, esquema: Type[T]) -> T:
        res = await self._client.chat.completions.create(
            model=self.modelo,
            messages=[
                {"role": "system", "content": system + _esquema_en_texto(esquema)},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            max_tokens=self.max_tokens,
            temperature=0.4,
        )
        return parsear_json(res.choices[0].message.content, esquema)


class AnthropicProveedor(ProveedorLLM):
    """Claude: salida estructurada nativa (messages.parse)."""
    nombre = "anthropic"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from anthropic import AsyncAnthropic
        self._client = AsyncAnthropic(timeout=self.timeout)

    async def generar(self, system: str, user: str, esquema: Type[T]) -> T:
        res = await self._client.messages.parse(
            model=self.modelo,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=esquema,
        )
        if res.stop_reason == "refusal":
            raise RespuestaInvalida("el modelo rechazó la petición")
        if res.stop_reason == "max_tokens":
            raise RespuestaInvalida("respuesta cortada por max_tokens")
        if res.parsed_output is None:
            raise RespuestaInvalida("sin salida estructurada")
        return res.parsed_output


class OpenAIProveedor(ProveedorLLM):
    """OpenAI: salida estructurada nativa (chat.completions.parse)."""
    nombre = "openai"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(timeout=self.timeout)

    async def generar(self, system: str, user: str, esquema: Type[T]) -> T:
        res = await self._client.chat.completions.parse(
            model=self.modelo,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format=esquema,
            max_completion_tokens=self.max_tokens,
        )
        msg = res.choices[0].message
        if msg.refusal:
            raise RespuestaInvalida(f"el modelo rechazó la petición: {msg.refusal}")
        if msg.parsed is None:
            raise RespuestaInvalida("sin salida estructurada")
        return msg.parsed


class GeminiProveedor(ProveedorLLM):
    """Gemini: salida JSON con esquema (google-genai)."""
    nombre = "gemini"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from google import genai
        self._client = genai.Client()

    async def generar(self, system: str, user: str, esquema: Type[T]) -> T:
        from google.genai import types
        res = await self._client.aio.models.generate_content(
            model=self.modelo,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=esquema,
                max_output_tokens=self.max_tokens,
                temperature=0.4,
            ),
        )
        if isinstance(res.parsed, esquema):
            return res.parsed
        return parsear_json(res.text, esquema)
