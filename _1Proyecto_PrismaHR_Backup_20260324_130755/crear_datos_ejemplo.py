import openpyxl
import os

def crear_excel_ejemplo():
    # Ruta del archivo
    nombre_archivo = "Datos_Entrada_Prisma.xlsx"
    
    # Crear un nuevo libro de trabajo
    wb = openpyxl.Workbook()
    hoja = wb.active
    hoja.title = "Candidatos"
    
    # Encabezados
    columnas = [
        "Nombre", "Liderazgo", "Trabajo en Equipo", "Adaptabilidad", 
        "Atención al Detalle", "Tolerancia Estrés", "Codigo_Cluster", "Codigo_Recomendacion"
    ]
    hoja.append(columnas)
    
    # Datos de ejemplo (5 candidatos)
    datos = [
        ["Elena García", 45, 85, 90, 95, 60, "CLUSTER_ANALISTA_DETALLE", "RECOM_VIGILANCIA_DESEMPENO"],
        ["Juan Pérez", 70, 60, 50, 40, 80, "CLUSTER_PERFIL_OPERATIVO", "RECOM_VIGILANCIA_DESEMPENO"], # Asumiendo estos códigos existen o se adaptan
        ["Marta Ruiz", 90, 95, 85, 70, 75, "CLUSTER_LID_ESTRATEGICO", "RECOM_VIGILANCIA_DESEMPENO"],
        ["Carlos Lyon", 30, 40, 60, 85, 90, "CLUSTER_ANALISTA_DETALLE", "RECOM_VIGILANCIA_DESEMPENO"],
        ["Sofía Marín", 60, 80, 75, 65, 55, "CLUSTER_PERFIL_OPERATIVO", "RECOM_VIGILANCIA_DESEMPENO"]
    ]
    
    for fila in datos:
        hoja.append(fila)
    
    # Guardar el archivo
    wb.save(nombre_archivo)
    print(f"✅ Archivo '{nombre_archivo}' creado con {len(datos)} candidatos de ejemplo.")

if __name__ == "__main__":
    crear_excel_ejemplo()
