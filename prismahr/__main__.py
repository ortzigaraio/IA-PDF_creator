"""
Uso:
    python -m prismahr                       # usa la configuración del .env
    python -m prismahr --datos mis_datos.json --proveedor anthropic
    python -m prismahr --proveedor plantillas   # sin IA, sin coste
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from prismahr.config import MODELOS_POR_DEFECTO, settings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="prismahr", description="Genera informes PDF y Excel de evaluación de competencias.")
    ap.add_argument("--datos", type=Path, help="JSON de entrada (por defecto: DATOS_JSON del .env)")
    ap.add_argument("--salida", type=Path, help="Carpeta de salida (por defecto: OUTPUT_DIR)")
    ap.add_argument("--proveedor", choices=list(MODELOS_POR_DEFECTO), help="Proveedor de IA")
    ap.add_argument("--modelo", help="Modelo concreto del proveedor")
    ap.add_argument("-v", "--verbose", action="store_true", help="Más detalle en el log")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )
    for ruidoso in ("httpx", "httpx2", "matplotlib", "PIL"):
        logging.getLogger(ruidoso).setLevel(logging.WARNING)

    cambios = {}
    if args.salida:
        cambios["OUTPUT_DIR"] = args.salida.resolve()
    if args.proveedor:
        cambios["LLM_PROVIDER"] = args.proveedor
        if not args.modelo:
            cambios["LLM_MODEL"] = None
    if args.modelo:
        cambios["LLM_MODEL"] = args.modelo
    cfg = settings.model_copy(update=cambios)

    from prismahr.pipeline import ejecutar  # import tardío: --help no carga Playwright

    print(f"Proveedor: {cfg.LLM_PROVIDER} · modelo: {cfg.modelo}")
    resumen = ejecutar(cfg, args.datos)

    print(f"\nPDF generados:   {len(resumen.pdfs)}  → {cfg.pdf_dir}")
    print(f"Excel generados: {len(resumen.excels)}  → {cfg.excel_dir}")
    print(f"Auditoría:       {cfg.auditoria_dir}")
    if resumen.respaldos:
        print(f"⚠ {resumen.respaldos} persona(s) con textos de respaldo porque la IA falló (ver log).")
    if resumen.errores:
        print(f"✘ {len(resumen.errores)} error(es):")
        for e in resumen.errores:
            print("   -", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
