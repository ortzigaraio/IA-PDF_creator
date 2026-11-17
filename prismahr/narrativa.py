"""
Redacción de los textos del informe.

- Las reglas (scoring.py) ya han decidido veredicto, riesgo, fortalezas y
  áreas de mejora. Aquí solo se REDACTA.
- Una única petición a la IA por persona, con salida estructurada.
- La IA nunca recibe el nombre real: se usa el marcador [NOMBRE] y se
  sustituye al final (minimización de datos personales, RGPD).
- Si la IA falla o devuelve algo inválido, se usan textos deterministas
  (proveedor "plantillas"), de modo que el lote nunca se detiene.
"""
from __future__ import annotations

import json
import logging
import re
from typing import List, Optional, Tuple

from prismahr.llm import ProveedorLLM, RespuestaInvalida
from prismahr.models import DIMENSIONES, DIMENSIONES_LABELS, Empresa, Evaluacion, Narrativa, Persona

logger = logging.getLogger(__name__)

MARCADOR = "[NOMBRE]"

SYSTEM_PROMPT = f"""Eres un consultor senior de Recursos Humanos que redacta informes de evaluación de competencias en castellano de España.

Recibirás en JSON los datos de una persona evaluada y las conclusiones YA DECIDIDAS por un sistema de reglas (veredicto, nivel de riesgo, fortalezas y áreas de mejora). Tu único trabajo es redactarlas con un tono profesional, claro y respetuoso.

Reglas obligatorias:
1. No cambies ni contradigas el veredicto, el nivel de riesgo, las fortalezas ni las áreas de mejora recibidas.
2. No inventes datos, cifras, cargos, logros ni hechos que no estén en la entrada.
3. Si hay "observaciones_evaluador", úsalas como base principal de los textos.
4. Refiérete a la persona solo como {MARCADOR}. No uses ningún otro nombre propio para ella.
5. No hagas diagnósticos médicos ni psicológicos; habla de comportamientos y competencias observables.
6. Texto plano: sin Markdown, sin HTML, sin viñetas ni numeración dentro de los textos.
7. "puntos_criticos": exactamente 2 frases, una por cada área de mejora y en el mismo orden.
8. "catalizadores": exactamente 2 frases sobre cómo aprovechar las fortalezas para el negocio.
9. Cada texto largo tiene 2-3 frases; "justificacion_riesgo" tiene 1-2 frases."""


# ----------------------------------------------------------------------
# Seudonimización
# ----------------------------------------------------------------------
def seudonimizar(texto: str, nombre: str) -> str:
    """Sustituye el nombre completo y el nombre de pila por [NOMBRE]."""
    partes = [nombre.strip()]
    pila = nombre.strip().split()[0] if nombre.strip() else ""
    if len(pila) > 2:
        partes.append(pila)
    for p in partes:
        texto = re.sub(rf"\b{re.escape(p)}\b", MARCADOR, texto, flags=re.IGNORECASE)
    return texto


def construir_entrada(persona: Persona, empresa: Empresa, ev: Evaluacion) -> str:
    objetivo = empresa.perfil_objetivo_100()
    datos = {
        "empresa": {"nombre": empresa.nombre, "sector": empresa.sector},
        "persona": MARCADOR,
        "compatibilidad_con_perfil": ev.compatibilidad,
        "veredicto": ev.veredicto,
        "nivel_riesgo": ev.nivel_riesgo,
        "motivos_riesgo": ev.motivos_riesgo,
        "fortalezas": [DIMENSIONES_LABELS[k] for k in ev.fortalezas],
        "areas_mejora": [DIMENSIONES_LABELS[k] for k in ev.areas_mejora],
        "dimensiones": {
            DIMENSIONES_LABELS[k]: {
                "persona": persona.dimensiones[k],
                "objetivo": objetivo[k],
                "diferencia": ev.gaps[k],
            }
            for k in DIMENSIONES
        },
        "observaciones_evaluador": [
            seudonimizar(f, persona.nombre) for f in persona.frases_predeterminadas
        ],
    }
    return json.dumps(datos, ensure_ascii=False, indent=2)


# ----------------------------------------------------------------------
# Textos deterministas (sin IA)
# ----------------------------------------------------------------------
_FORTALEZA = {
    "adaptabilidad": "se ajusta con rapidez a cambios de prioridades y contextos",
    "comunicacion": "transmite ideas con claridad y facilita el entendimiento en el equipo",
    "creatividad": "aporta enfoques originales y soluciones nuevas a los problemas",
    "disciplina": "mantiene un alto nivel de rigor, orden y cumplimiento de compromisos",
    "empatia": "comprende las necesidades de los demás y genera relaciones de confianza",
    "iniciativa": "se anticipa a los problemas y actúa sin necesidad de supervisión",
    "resiliencia": "mantiene el rendimiento bajo presión y se recupera bien de la adversidad",
}
_MEJORA = {
    "adaptabilidad": "Reforzar la flexibilidad ante cambios mediante proyectos con prioridades variables.",
    "comunicacion": "Trabajar la comunicación y la escucha activa con práctica guiada y feedback frecuente.",
    "creatividad": "Estimular la generación de ideas con espacios de innovación y retos abiertos.",
    "disciplina": "Consolidar hábitos de planificación y seguimiento de compromisos.",
    "empatia": "Desarrollar la sensibilidad hacia las necesidades del equipo con mentoría específica.",
    "iniciativa": "Fomentar la proactividad asignando responsabilidades con autonomía progresiva.",
    "resiliencia": "Mejorar la gestión de la presión con herramientas de organización y apoyo cercano.",
}
_DICTAMEN = {
    "PROMOCIÓN DIRECTA": "El perfil se ajusta de forma muy sólida a lo que busca la organización, lo que respalda asumir mayores responsabilidades.",
    "FORMACIÓN TÉCNICA RECOMENDADA": "El perfil muestra un buen ajuste general; una formación técnica dirigida permitirá cerrar las diferencias restantes.",
    "CONSOLIDACIÓN": "El ajuste es aceptable y conviene consolidar el rol actual antes de plantear nuevos pasos.",
    "PLAN DE MEJORA INMEDIATO": "Existen diferencias relevantes con el perfil objetivo que requieren un plan de mejora con seguimiento cercano.",
}


def narrativa_plantillas(persona: Persona, empresa: Empresa, ev: Evaluacion) -> Narrativa:
    f = ev.fortalezas
    lab = DIMENSIONES_LABELS
    am = ev.areas_mejora
    return Narrativa(
        resumen_dictamen=(
            f"{MARCADOR} obtiene una compatibilidad del {ev.compatibilidad}% con el perfil objetivo "
            f"de {empresa.nombre}. {_DICTAMEN.get(ev.veredicto, '')}"
        ),
        analisis_fortalezas=(
            f"Sus puntos más fuertes son {lab[f[0]]}, {lab[f[1]]} y {lab[f[2]]}. "
            f"En concreto, {_FORTALEZA[f[0]]}, y además {_FORTALEZA[f[1]]}."
        ),
        analisis_liderazgo=(
            f"Su perfil de {lab[f[0]].lower()} y {lab[f[1]].lower()} es una buena base para influir en el equipo. "
            f"Desarrollar {lab[am[0]].lower()} ampliará su capacidad de liderazgo."
        ),
        recomendacion_final=(
            f"Se recomienda priorizar el desarrollo de {lab[am[0]].lower()} y {lab[am[1]].lower()}, "
            f"apoyándose en sus fortalezas actuales. Veredicto: {ev.veredicto.lower()}."
        ),
        puntos_criticos=[_MEJORA[am[0]], _MEJORA[am[1]]],
        catalizadores=[
            f"Aprovechar su {lab[f[0]].lower()} en proyectos de alto impacto para el negocio.",
            f"Utilizar su {lab[f[1]].lower()} como palanca para mentorizar a otras personas del equipo.",
        ],
        justificacion_riesgo=(
            f"Riesgo {ev.nivel_riesgo.lower()} de desgaste o salida: {'; '.join(ev.motivos_riesgo)}."
        ),
    )


# ----------------------------------------------------------------------
# Limpieza y orquestación
# ----------------------------------------------------------------------
def _limpiar(texto: str, nombre: str) -> str:
    texto = re.sub(r"<[^>]*>", "", texto)        # HTML
    texto = re.sub(r"[*_#`~]+", "", texto)        # Markdown
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto.replace(MARCADOR, nombre)


def _ajustar_lista(items: List[str], respaldo: List[str], n: int = 2) -> List[str]:
    items = [i for i in items if i.strip()][:n]
    return items + respaldo[len(items):n]


def finalizar(n: Narrativa, respaldo: Narrativa, nombre: str) -> Narrativa:
    """Garantiza 2 elementos por lista y sustituye el marcador por el nombre."""
    datos = n.model_dump()
    datos["puntos_criticos"] = _ajustar_lista(n.puntos_criticos, respaldo.puntos_criticos)
    datos["catalizadores"] = _ajustar_lista(n.catalizadores, respaldo.catalizadores)
    for k, v in datos.items():
        datos[k] = [_limpiar(x, nombre) for x in v] if isinstance(v, list) else _limpiar(v, nombre)
    return Narrativa(**datos)


async def generar_narrativa(
    persona: Persona,
    empresa: Empresa,
    ev: Evaluacion,
    proveedor: Optional[ProveedorLLM],
    reintentos: int = 2,
) -> Tuple[Narrativa, str]:
    """Devuelve (narrativa, fuente). La fuente queda registrada para auditoría."""
    respaldo = narrativa_plantillas(persona, empresa, ev)
    if proveedor is None:
        return finalizar(respaldo, respaldo, persona.nombre), "plantillas"

    entrada = construir_entrada(persona, empresa, ev)
    ultimo_error: Exception | None = None
    for intento in range(reintentos + 1):
        try:
            n = await proveedor.generar(SYSTEM_PROMPT, entrada, Narrativa)
            return finalizar(n, respaldo, persona.nombre), proveedor.etiqueta
        except RespuestaInvalida as exc:
            ultimo_error = exc
            logger.warning("%s: respuesta inválida (intento %d): %s", persona.usuario_id, intento + 1, exc)
        except Exception as exc:  # red, cuota, clave... el SDK ya ha reintentado
            ultimo_error = exc
            logger.warning("%s: error del proveedor: %s", persona.usuario_id, exc)
            break

    logger.error("%s: se usan textos de respaldo (%s)", persona.usuario_id, ultimo_error)
    return finalizar(respaldo, respaldo, persona.nombre), f"plantillas (respaldo tras error de {proveedor.etiqueta})"
