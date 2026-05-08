"""
src/content_generator.py — Generación de contenido IA en paralelo.

MEJORA CLAVE: en el motor original las 6 llamadas a Groq son secuenciales
(~8-12 segundos por usuario). Aquí se lanzan todas con asyncio.gather()
y se resuelven en paralelo (~2 segundos por usuario → ~6x más rápido).
"""
from __future__ import annotations
import asyncio
import logging
from typing import List

from src.ai_client import AIClient
from src.config import settings
from src.models import ContenidoModel, UsuarioModel

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Orquesta la generación de contenido lanzando todas las llamadas en paralelo."""

    def __init__(self, ai_client: AIClient):
        self.ai = ai_client

    # ------------------------------------------------------------------
    # Método principal: asyncio.gather — todas las llamadas a la vez
    # ------------------------------------------------------------------
    async def generar_todo(
        self,
        usuario: UsuarioModel,
        empresa_id: str,
        compatibilidad: float,
    ) -> ContenidoModel:
        """
        Lanza las 6 co-rutinas de generación concurrentemente y espera
        a que todas terminen. El tiempo total ≈ la llamada más lenta,
        no la suma de todas.
        """
        d = usuario.dimensiones
        frases = " ".join(usuario.frases_predeterminadas)

        (
            raw_bloques,
            raw_desc,
            raw_fortalezas,
            raw_puntos,
            raw_catalizadores,
            raw_alerta,
        ) = await asyncio.gather(
            self._bloques(usuario.nombre, empresa_id, compatibilidad, frases),
            self._descripcion(usuario.nombre, empresa_id, compatibilidad),
            self._fortalezas(empresa_id),
            self._puntos_criticos(usuario, empresa_id, compatibilidad),
            self._catalizadores(usuario, empresa_id, compatibilidad),
            self._alerta_riesgo(usuario, empresa_id, frases),
        )

        return ContenidoModel(
            analisis_bloques=raw_bloques,
            descripcion_recom=raw_desc,
            fortalezas=raw_fortalezas,
            puntos_criticos=raw_puntos,
            catalizadores_crecimiento=raw_catalizadores,
            alerta_riesgo=raw_alerta,
        )

    # ------------------------------------------------------------------
    # Generadores individuales (privados)
    # ------------------------------------------------------------------
    async def _bloques(
        self,
        nombre: str,
        empresa_id: str,
        score: float,
        frases: str,
    ) -> List[str]:
        prompt = (
            f"Genera 3 bloques de análisis para {nombre} ({empresa_id}) con rating {score}/100. "
            "Bloque 1: Fortalezas. Bloque 2: Liderazgo. Bloque 3: Veredicto Final. "
            "Cada bloque debe tener exactamente 2 oraciones potentes. Separa los bloques con '###'."
        )
        if frases:
            prompt += (
                f" REQUISITO OBLIGATORIO: Toma como base central argumentativa las siguientes "
                f"observaciones y desarróllalas: '{frases}'."
            )
        try:
            raw = await self.ai.call_async(prompt, settings.GROQ_MAX_TOKENS_BLOQUES)
            bloques = [b.strip() for b in raw.split("###")]
            return bloques[:3] if len(bloques) >= 3 else bloques + ["Análisis en proceso."] * (3 - len(bloques))
        except Exception:
            logger.warning("Fallback bloques para %s", nombre)
            return ["Análisis de fortalezas.", "Potencial de liderazgo en desarrollo.", "Recomendación operativa estable."]

    async def _descripcion(self, nombre: str, empresa_id: str, score: float) -> str:
        prompt = (
            f"Genera una 'Justificación de Dictamen' muy breve (máx 2-3 frases) "
            f"para {nombre} ({empresa_id}) con score {score}."
        )
        try:
            return await self.ai.call_async(prompt, settings.GROQ_MAX_TOKENS_CORTO)
        except Exception:
            return "Consolidar rol actual mediante planes de formación continua."

    async def _fortalezas(self, empresa_id: str) -> List[str]:
        prompt = f"Lista 3 fortalezas clave para un perfil {empresa_id}. Solo nombres, una por línea."
        try:
            raw = await self.ai.call_async(prompt, settings.GROQ_MAX_TOKENS_CORTO)
            return [l.strip().lstrip("-•*").strip() for l in raw.split("\n") if l.strip()]
        except Exception:
            return ["Capacidad adaptativa", "Enfoque en procesos", "Orientación a resultados"]

    async def _puntos_criticos(
        self,
        usuario: UsuarioModel,
        empresa_id: str,
        score: float,
    ) -> List[str]:
        d = usuario.dimensiones
        prompt = (
            f"Analiza al candidato {usuario.nombre} de {empresa_id} con score {score}/100. "
            f"Dimensiones — Adaptabilidad:{d.adaptabilidad}%, Comunicación:{d.comunicacion}%, "
            f"Creatividad:{d.creatividad}%, Disciplina:{d.disciplina}%, Empatía:{d.empatia}%, "
            f"Iniciativa:{d.iniciativa}%, Resiliencia:{d.resiliencia}%. "
            "Genera exactamente 2 puntos de atención crítica. "
            "Una frase corta por línea, sin numeración ni guiones."
        )
        try:
            raw = await self.ai.call_async(prompt, settings.GROQ_MAX_TOKENS_MEDIO)
            lineas = [
                l.strip() for l in raw.split("\n")
                if l.strip() and not l.strip()[0] in "0123456789-*•"
            ]
            resultado = lineas[:2]
            if len(resultado) < 2:
                resultado += ["Desarrollar estrategias de mejora continua."]
            return resultado
        except Exception:
            return self._fallback_puntos(usuario)

    async def _catalizadores(
        self,
        usuario: UsuarioModel,
        empresa_id: str,
        score: float,
    ) -> List[str]:
        d = usuario.dimensiones
        prompt = (
            f"Identifica 2 catalizadores de crecimiento para {usuario.nombre} ({empresa_id}) "
            f"con score {score}/100. "
            f"Dimensiones — Adaptabilidad:{d.adaptabilidad}%, Comunicación:{d.comunicacion}%, "
            f"Creatividad:{d.creatividad}%, Disciplina:{d.disciplina}%, Empatía:{d.empatia}%, "
            f"Iniciativa:{d.iniciativa}%, Resiliencia:{d.resiliencia}%. "
            "Orientados a resultado de negocio. Una frase impactante por línea, sin numeración."
        )
        try:
            raw = await self.ai.call_async(prompt, settings.GROQ_MAX_TOKENS_MEDIO)
            lineas = [
                l.strip() for l in raw.split("\n")
                if l.strip() and not l.strip()[0] in "0123456789-*•"
            ]
            resultado = lineas[:2]
            if len(resultado) < 2:
                resultado += ["Alto potencial de desarrollo en roles de mayor responsabilidad."]
            return resultado
        except Exception:
            return ["Alto compromiso con la excelencia operativa.", "Orientación proactiva hacia la mejora continua."]

    async def _alerta_riesgo(
        self,
        usuario: UsuarioModel,
        empresa_id: str,
        frases: str,
    ) -> str:
        d = usuario.dimensiones
        prompt = (
            f"Analiza si {usuario.nombre} ({empresa_id}) tiene riesgo de burnout o fuga de talento. "
            f"Resiliencia: {d.resiliencia}%, Empatía: {d.empatia}%, exigencia: alta."
        )
        if frases:
            prompt += f" Contexto: '{frases}'."
        prompt += " Responde SOLO con: 'RIESGO BAJO:', 'RIESGO MEDIO:' o 'RIESGO ALTO:' + justificación breve."
        try:
            return await self.ai.call_async(prompt, settings.GROQ_MAX_TOKENS_CORTO)
        except Exception:
            return self._fallback_alerta(usuario)

    # ------------------------------------------------------------------
    # Fallbacks inteligentes
    # ------------------------------------------------------------------
    @staticmethod
    def _fallback_puntos(usuario: UsuarioModel) -> List[str]:
        d = usuario.dimensiones
        pts = []
        if d.resiliencia < 70:
            pts.append("Optimizar gestión de presión y recuperación ante adversidad.")
        elif d.comunicacion < 70:
            pts.append("Fortalecer comunicación efectiva y escucha activa.")
        else:
            pts.append("Implementar acciones de desarrollo en competencias transversales.")
        pts.append(
            "Desarrollar proactividad en toma de decisiones."
            if d.iniciativa < 70 else
            "Mantener y potenciar la iniciativa demostrada."
        )
        return pts

    @staticmethod
    def _fallback_alerta(usuario: UsuarioModel) -> str:
        r = usuario.dimensiones.resiliencia
        if r < 65:
            return "RIESGO ALTO: Resiliencia muy baja frente a alta presión, propenso a burnout."
        if r < 80:
            return "RIESGO MEDIO: Monitorear nivel de carga de trabajo."
        return "RIESGO BAJO: Niveles estables de manejo del estrés."
