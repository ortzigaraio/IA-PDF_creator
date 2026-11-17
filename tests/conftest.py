from __future__ import annotations

from pathlib import Path

import pytest

from prismahr.models import Empresa, Narrativa, Persona

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture
def empresa() -> Empresa:
    return Empresa(
        nombre="Empresa Prueba",
        sector="Pruebas",
        pesos_perfil_objetivo={
            "adaptabilidad": 8, "comunicación": 8, "creatividad": 6, "disciplina": 9,
            "empatía": 7, "iniciativa": 8, "resiliencia": 8,
        },
        clientes=[
            Persona(usuario_id="P1", nombre="Ana López", dimensiones={
                "adaptabilidad": 80, "comunicacion": 80, "creatividad": 60, "disciplina": 90,
                "empatia": 70, "iniciativa": 80, "resiliencia": 80,
            }, frases_predeterminadas=["Ana López coordina muy bien al equipo."]),
            Persona(id="P2", nombre="Luis Pardo", dimensiones={
                "adaptabilidad": 50, "comunicación": 40, "creatividad": 55, "disciplina": 60,
                "empatía": 50, "iniciativa": 45, "resiliencia": 60,
            }),
        ],
    )


class ProveedorFalso:
    """Simula una IA: devuelve lo que se le indique o lanza una excepción."""
    nombre = "falso"
    modelo = "test"
    etiqueta = "falso:test"

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.llamadas: list[tuple[str, str]] = []

    async def generar(self, system, user, esquema):
        self.llamadas.append((system, user))
        r = self.respuestas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def narrativa_ia(**cambios) -> Narrativa:
    base = dict(
        resumen_dictamen="[NOMBRE] encaja muy bien.",
        analisis_fortalezas="**Gran** disciplina.",
        analisis_liderazgo="Lidera con el ejemplo.",
        recomendacion_final="Seguir creciendo.",
        puntos_criticos=["Mejorar A.", "Mejorar B."],
        catalizadores=["Aprovechar C.", "Aprovechar D."],
        justificacion_riesgo="Riesgo bajo.",
    )
    base.update(cambios)
    return Narrativa(**base)
