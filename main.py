import os
import shutil
import json
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import openpyxl
from typing import List

# CAMBIO: Importar las nuevas listas de columnas oficiales del RCV
from ocr_services import (
    extract_data_with_template, 
    extract_data_without_template,
    BOLIVIAN_COMPRAS_FIELDS,
    BOLIVIAN_VENTAS_FIELDS
)

app = FastAPI(title="Factura OCR API (RCV Bolivia)", description="API para procesar facturas y generar un borrador del Registro de Compras y Ventas.")

# --- Configuración de CORS (sin cambios) ---
origins = [
    "http://localhost:5173", "http://localhost:5174", "http://localhost:5175",
    "https://bill-ai-frontend.vercel.app",
]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# --- Configuración de directorios (sin cambios) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

active_template = {"path": None, "fields": []}

# --- Endpoints /upload-template/ y /clear-template/ (sin cambios) ---
@app.post("/upload-template/")
async def upload_template(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx')):
        raise HTTPException(status_code=400, detail="El archivo debe ser un .xlsx")
    template_path = os.path.join(TEMPLATES_DIR, "template.xlsx")
    with open(template_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    try:
        workbook = openpyxl.load_workbook(template_path)
        sheet = workbook.active
        headers = [cell.value for cell in sheet[1] if cell.value]
        if not headers: raise HTTPException(status_code=400, detail="La plantilla no tiene encabezados en la primera fila.")
        active_template["path"] = template_path
        active_template["fields"] = headers
        return {"message": "Plantilla cargada exitosamente", "campos_detectados": headers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo procesar la plantilla: {e}")

@app.post("/clear-template/")
async def clear_template():
    active_template["path"] = None
    active_template["fields"] = []
    template_file = os.path.join(TEMPLATES_DIR, "template.xlsx")
    if os.path.exists(template_file): os.remove(template_file)
    return {"message": "Plantilla limpiada."}

@app.post("/process-invoice/")
async def process_invoice(
    files: List[UploadFile] = File(...),
    nombre: str = Form(None),
    nit: str = Form(None)
):
    workbook = openpyxl.Workbook()
    # CAMBIO: Crear dos hojas, una para Compras y otra para Ventas
    sheet_compras = workbook.active
    sheet_compras.title = "Registro de Compras"
    sheet_ventas = workbook.create_sheet("Registro de Ventas")
    
    # Escribir los encabezados oficiales en cada hoja
    sheet_compras.append(BOLIVIAN_COMPRAS_FIELDS)
    sheet_ventas.append(BOLIVIAN_VENTAS_FIELDS)
    
    # CAMBIO: Lógica de Flujo Dual adaptada al RCV
    if active_template["path"]:
        # --- Flujo 1: CON PLANTILLA PERSONALIZADA ---
        # (Este flujo ahora usa una tercera hoja para no interferir con el RCV)
        sheet_custom = workbook.create_sheet("Resultado Plantilla Custom")
        sheet_custom.append(active_template["fields"])
        
        for file in files:
            file_path = os.path.join(UPLOADS_DIR, file.filename)
            with open(file_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
            json_string = extract_data_with_template(file_path, active_template["fields"])
            try:
                data = json.loads(json_string)
                new_row = [data.get(field) for field in active_template["fields"]]
            except (json.JSONDecodeError, AttributeError):
                new_row = [f"ERROR: {file.filename}"] + ["Respuesta no válida"] * (len(active_template["fields"]) - 1)
            sheet_custom.append(new_row)
            os.remove(file_path)
    else:
        # --- Flujo 2: SIN PLANTILLA (Generación de RCV) ---
        if not nombre or not nit:
            raise HTTPException(status_code=400, detail="Se requiere 'nombre' y 'nit' cuando no hay plantilla.")
        
        for file in files:
            file_path = os.path.join(UPLOADS_DIR, file.filename)
            with open(file_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
            json_string = extract_data_without_template(file_path, nombre, nit)
            try:
                response = json.loads(json_string)
                invoice_type = response.get("tipo_factura")
                data = response.get("datos", {})

                if invoice_type == "Compra":
                    new_row = [data.get(field) for field in BOLIVIAN_COMPRAS_FIELDS]
                    sheet_compras.append(new_row)
                elif invoice_type == "Venta":
                    new_row = [data.get(field) for field in BOLIVIAN_VENTAS_FIELDS]
                    sheet_ventas.append(new_row)
                else:
                    # Si no se pudo clasificar, lo añadimos a la primera hoja como error
                    error_row = [f"ERROR: {file.filename}"] + ["No se pudo clasificar"] * (len(BOLIVIAN_COMPRAS_FIELDS) - 1)
                    sheet_compras.append(error_row)

            except (json.JSONDecodeError, AttributeError):
                 error_row = [f"ERROR: {file.filename}"] + ["Respuesta no válida de la IA"] * (len(BOLIVIAN_COMPRAS_FIELDS) - 1)
                 sheet_compras.append(error_row)
            os.remove(file_path)

    # --- Guardado y respuesta (sin cambios) ---
    output_filename = "RCV_Procesado.xlsx"
    output_path = os.path.join(UPLOADS_DIR, output_filename)
    workbook.save(output_path)
    return FileResponse(path=output_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=output_filename)

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de OCR para RCV Bolivia."}