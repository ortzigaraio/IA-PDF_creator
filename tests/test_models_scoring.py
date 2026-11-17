from __future__ import annotations

import pytest
from pydantic import ValidationError

from prismahr import scoring
from prismahr.models import DatosEntrada, Empresa, Persona
from tests.conftest import RAIZ

DIMS_OK = {k: 50 for k in ["adaptabilidad", "comunicación", "creatividad", "disciplina", "empatía", "iniciativa", "resiliencia"]}


def test_acepta_claves_con_y_sin_tilde_e_id_alternativo(empresa):
    p2 = empresa.clientes[1]
    assert p2.usuario_id == "P2"                       # leído desde "id"
    assert p2.dimensiones["comunicacion"] == 40        # leído desde "comunicación"
    assert empresa.pesos_perfil_objetivo["empatia"] == 7


def test_rechaza_dimension_fuera_de_rango():
    with pytest.raises(ValidationError):
        Persona(usuario_id="X", nombre="X", dimensiones={**DIMS_OK, "iniciativa": 120})


def test_rechaza_dimension_que_falta_o_sobra():
    faltan = dict(DIMS_OK)
    faltan.pop("resiliencia")
    with pytest.raises(ValidationError):
        Persona(usuario_id="X", nombre="X", dimensiones=faltan)
    with pytest.raises(ValidationError):
        Persona(usuario_id="X", nombre="X", dimensiones={**DIMS_OK, "carisma": 50})


def test_rechaza_ids_repetidos_y_colores_invalidos():
    p = Persona(usuario_id="A", nombre="A", dimensiones=DIMS_OK)
    with pytest.raises(ValidationError):
        Empresa(nombre="E", pesos_perfil_objetivo={k: 5 for k in DIMS_OK}, clientes=[p, p])
    with pytest.raises(ValidationError):
        Empresa(nombre="E", pesos_perfil_objetivo={k: 5 for k in DIMS_OK}, plantilla={"color_primario": "azul"})


def test_datos_de_ejemplo_validan():
    datos = DatosEntrada.model_validate_json((RAIZ / "datos" / "ejemplo.json").read_text(encoding="utf-8"))
    assert len(datos.empresas) >= 1
    for e in datos.empresas.values():
        assert e.clientes


def test_compatibilidad_identica_es_100_y_conserva_formula_original():
    obj = {k: 80.0 for k in scoring.DIMENSIONES}
    assert scoring.calcular_compatibilidad(obj, obj) == 100.0
    # fórmula original: 100 - media(|u/10 - peso|) * 10
    dims = {k: v for k, v in zip(scoring.DIMENSIONES, [90, 70, 60, 100, 80, 50, 75])}
    original = 100 - sum(abs(dims[k] / 10 - 8) for k in scoring.DIMENSIONES) / 7 * 10
    assert scoring.calcular_compatibilidad(dims, obj) == round(original, 1)


@pytest.mark.parametrize("compat,esperado", [
    (85, "PROMOCIÓN DIRECTA"), (84.9, "FORMACIÓN TÉCNICA RECOMENDADA"),
    (72, "FORMACIÓN TÉCNICA RECOMENDADA"), (71.9, "CONSOLIDACIÓN"),
    (55, "CONSOLIDACIÓN"), (54.9, "PLAN DE MEJORA INMEDIATO"),
])
def test_umbrales_veredicto(compat, esperado):
    assert scoring.decidir_veredicto(compat) == esperado


@pytest.mark.parametrize("res,emp,nivel", [(60, 90, "ALTO"), (70, 90, "MEDIO"), (85, 60, "MEDIO"), (85, 80, "BAJO")])
def test_riesgo_lo_deciden_las_reglas(res, emp, nivel):
    dims = {k: 70.0 for k in scoring.DIMENSIONES} | {"resiliencia": res, "empatia": emp}
    assert scoring.evaluar_riesgo(dims)[0] == nivel


def test_evaluar_completo(empresa):
    ev_buena = scoring.evaluar(empresa.clientes[0], empresa)
    ev_mala = scoring.evaluar(empresa.clientes[1], empresa)
    assert ev_buena.compatibilidad == 100.0
    assert ev_buena.veredicto == "PROMOCIÓN DIRECTA"
    # Con la fórmula heredada, ~26 puntos de desviación media siguen dando 74,3 %
    assert ev_mala.compatibilidad == 74.3
    assert ev_mala.veredicto == "FORMACIÓN TÉCNICA RECOMENDADA"
    assert ev_mala.nivel_riesgo == "ALTO"
    assert len(ev_buena.fortalezas) == 3 and len(ev_mala.areas_mejora) == 2
    assert ev_buena.fortalezas[0] == "disciplina"
    assert ev_mala.areas_mejora[0] == "comunicacion"    # gap -40, el mayor
    assert ev_buena.percentiles["disciplina"] == 100.0
    assert ev_mala.percentiles["disciplina"] == 50.0
