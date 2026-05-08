from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn
import os
import traceback
from dotenv import load_dotenv

load_dotenv()

# Importamos la lógica central
from motor_prisma import MotorPDFv2, UsuarioData, generar_radar_base64
import jinja2
from playwright.async_api import async_playwright
import matplotlib.pyplot as plt
import numpy as np
import base64
from datetime import datetime
import asyncio

app = FastAPI(title="Perfil_Psic_PDF_maker Webhook IA v2.0")

# API KEY cargada correctamente desde entorno
API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise ValueError("Falta GROQ_API_KEY en las variables de entorno.")

motor = MotorPDFv2(API_KEY, "datos_empresa.json")

class UsuarioRequest(BaseModel):
    id: str
    nombre: str
    atencion_detalle: float
    adaptabilidad: float
    trabajo_equipo: float
    tolerancia_estres: float
    liderazgo: float

async def generar_pdf_async(usuario_req: UsuarioRequest, result: dict):
    """ Tarea en segundo plano para renderizar el PDF sin bloquear la respuesta web """
    try:
        env = jinja2.Environment(loader=jinja2.FileSystemLoader("."))
        template = env.get_template("plantilla_radar.html")
        
        # Generar gráfico radar
        dimensiones = {
            "Lid. Operativo": usuario_req.liderazgo * 10,
            "Eq. Trabajo": usuario_req.trabajo_equipo * 10,
            "Adaptabilidad": usuario_req.adaptabilidad * 10,
            "At. Detalle": usuario_req.atencion_detalle * 10,
            "Tol. Estrés": usuario_req.tolerancia_estres * 10
        }
        
        # Render radar sync -> no blocking the event loop ideally, but fast enough
        radar_img = generar_radar_base64(dimensiones)
        fecha_hoy = datetime.now().strftime("%d de %B, %Y").lower()
        id_eval = f"PRISM-{datetime.now().year}-{usuario_req.nombre[:2].upper()}-{usuario_req.id}"
        
        # Mapear a diseño previo
        perfil_titulo = motor.perfiles_data["perfiles"].get(result["cluster"], {}).get("nombre", "Perfil")
        perfil_desc = motor.perfiles_data["perfiles"].get(result["cluster"], {}).get("descripcion", "")
        
        # Join strengths & steps into lists for jinja
        plan_html = "".join([f"<li>{paso}</li>" for paso in result["contenido"]["plan_accion"].split('\n') if paso.strip() and not paso.startswith('Genera')])
        
        if not plan_html:
             plan_html = f"<li>{result['contenido']['plan_accion']}</li>"
        
        html_final = template.render(
            nombre_candidato=usuario_req.nombre,
            titulo_perfil=perfil_titulo,
            desc_perfil=perfil_desc,
            titulo_recom=result['veredicto'],
            desc_recom="Generado por IA Claude",
            analisis_detallado=result['contenido']['analisis_ejecutivo'],
            plan_accion=plan_html,
            imagen_radar_base64=radar_img,
            fecha_actual=fecha_hoy,
            id_evaluacion=id_eval
        )
        
        nombre_seguro = usuario_req.nombre.replace(' ', '_')
        os.makedirs("Salida_PDF", exist_ok=True)
        nombre_pdf = os.path.abspath(os.path.join("Salida_PDF", f"Informe_{nombre_seguro}_Webhook.pdf"))
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(html_final)
            await page.wait_for_load_state("networkidle")
            await page.pdf(path=nombre_pdf, format="A4", print_background=True, margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"})
            await browser.close()
            
        print(f"Webhook -> PDF Creado: {nombre_pdf}")

    except Exception as e:
        print(f"Error en generación asíncrona: {e}")
        traceback.print_exc()

@app.post("/api/v1/webhook/nuevo_candidato")
async def webhook_nuevo_candidato(req: UsuarioRequest, background_tasks: BackgroundTasks):
    try:
        # 1. Empaquetar a estructura base
        usuario = UsuarioData(
            usuario_id=req.id,
            nombre=req.nombre,
            atención_detalle=req.atencion_detalle,
            adaptabilidad=req.adaptabilidad,
            trabajo_equipo=req.trabajo_equipo,
            tolerancia_estrés=req.tolerancia_estres,
            liderazgo=req.liderazgo
        )
        
        # 2. IA Processing
        # (Nota: El API real bloqueará si es síncrono. Idealmente sería asíncrono o mockeado para tests)
        resultado = motor.procesar_usuario(usuario)
        
        # 3. Lanzar PDF generation background job
        background_tasks.add_task(generar_pdf_async, req, resultado)
        
        return {
            "status": "success",
            "message": "Candidato procesado. PDF en cola de generación.",
            "ia_analysis": resultado
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("Iniciando Servidor Webhook Perfil_Psic_PDF_maker v2.0...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
