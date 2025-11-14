import os
import shutil
import json
import asyncio 
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import openpyxl
from typing import List
from dateutil import parser

from ocr_services import (
    extract_data_with_openai,
    BOLIVIAN_COMPRAS_FIELDS,
    BOLIVIAN_VENTAS_FIELDS
)

app = FastAPI(title="Factura OCR API (RCV Bolivia)", description="API para procesar facturas y generar un borrador del Registro de Compras y Ventas.")

#prueba
# --- Configuración de CORS y Directorios (sin cambios) ---
origins = ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "https://bill-ai-frontend.vercel.app", "https://bill-ai-frontend-git-develop-brandon-gonsales-projects.vercel.app"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
RCV_TEMPLATES_DIR = os.path.join(TEMPLATES_DIR, "rcv_templates")
COMPRAS_TEMPLATE_PATH = os.path.join(RCV_TEMPLATES_DIR, "RCV_Compras_Template.xlsx")
VENTAS_TEMPLATE_PATH = os.path.join(RCV_TEMPLATES_DIR, "RCV_Ventas_Template.xlsx")
active_template = {"path": None, "fields": []}
COMPRAS_AI_FIELDS = ["NIT PROVEEDOR", "RAZON SOCIAL PROVEEDOR", "CODIGO DE AUTORIZACION", "NUMERO FACTURA", "NUMERO DUI/DIM", "FECHA DE FACTURA/DUI/DIM", "IMPORTE TOTAL COMPRA", "IMPORTE ICE", "IMPORTE IEHD", "IMPORTE IPJ", "TASAS", "OTRO NO SUJETO A CREDITO FISCAL", "IMPORTES EXENTOS", "IMPORTE COMPRAS GRAVADAS A TASA CERO", "SUBTOTAL", "DESCUENTOS/BONIFICACIONES /REBAJAS SUJETAS AL IVA", "IMPORTE GIFT CARD", "IMPORTE BASE CF"]
VENTAS_AI_FIELDS = ["FECHA DE LA FACTURA", "N° DE LA FACTURA", "CODIGO DE AUTORIZACION", "NIT / CI CLIENTE", "COMPLEMENTO", "NOMBRE O RAZON SOCIAL", "IMPORTE TOTAL DE LA VENTA", "SUBTOTAL", "IMPORTE BASE PARA DEBITO FISCAL", "CODIGO DE CONTROL"]

# vvv INICIO DE LISTAS ACTUALIZADAS vvv
# Lista de campos de ENTRADA que se establecerán a 0 si están vacíos (ANTES de los cálculos).
INPUT_FIELDS_TO_DEFAULT_TO_ZERO = [
    "IMPORTE ICE", "IMPORTE IEHD", "IMPORTE IPJ", "TASAS",
    "OTRO NO SUJETO A CREDITO FISCAL",  # Compras
    "OTROS NO SUJETOS AL IVA",  # Ventas
    "IMPORTES EXENTOS",  # Compras
    "EXPORTACIONES Y OPERACIONES EXENTAS",  # Ventas
    "IMPORTE COMPRAS GRAVADAS A TASA CERO",  # Compras
    "VENTAS GRAVADAS A TASA CERO",  # Ventas
    "DESCUENTOS/BONIFICACIONES /REBAJAS SUJETAS AL IVA",
    "DESCUENTOS, BONIFICACIONES Y REBAJAS SUJETAS AL IVA",
    "IMPORTE GIFT CARD",
    "CODIGO DE CONTROL"
]

# Lista COMPLETA de campos que deben ser 0 en el Excel final (DESPUÉS de los cálculos).
FINAL_NUMERIC_FIELDS = [
    "IMPORTE ICE", "IMPORTE IEHD", "IMPORTE IPJ", "TASAS",
    "OTROS NO SUJETOS AL IVA",
    "EXPORTACIONES Y OPERACIONES EXENTAS",
    "VENTAS GRAVADAS A TASA CERO",
    "SUBTOTAL",
    "DESCUENTOS, BONIFICACIONES Y REBAJAS SUJETAS AL IVA",
    "DESCUENTOS/BONIFICACIONES /REBAJAS SUJETAS AL IVA",
    "IMPORTE GIFT CARD",
    "IMPORTE BASE PARA DEBITO FISCAL",
    "DEBITO FISCAL",
    "CODIGO DE CONTROL"
]
# ^^^ FIN DE LISTAS ACTUALIZADAS ^^^

# --- Funciones Auxiliares (sin cambios) ---
def _prepare_row_for_excel(row_data: list) -> list:
    prepared_row = []
    for item in row_data:
        if isinstance(item, (list, dict)):
            prepared_row.append(json.dumps(item, ensure_ascii=False, indent=2))
        else:
            prepared_row.append(item)
    return prepared_row

def _clean_and_convert_to_float(value) -> float | None:
    if value is None: return None
    try:
        s_value = str(value)
        if ',' in s_value and '.' in s_value: s_value = s_value.replace(',', '')
        else: s_value = s_value.replace(',', '.')
        cleaned_s = ''.join(c for c in s_value if c.isdigit() or c in '.-').strip()
        if not cleaned_s or cleaned_s in ['-', '.']: return None
        return float(cleaned_s)
    except (ValueError, TypeError):
        return None

def _format_date_to_dmy(date_string) -> str:
    if not isinstance(date_string, str) or not date_string.strip():
        return date_string
    try:
        parsed_date = parser.parse(date_string)
        return parsed_date.strftime('%d/%m/%Y')
    except (ValueError, parser.ParserError):
        return date_string

# --- Endpoints de plantillas (sin cambios) ---
@app.post("/upload-template/")
async def upload_template(file: UploadFile = File(...)): pass
@app.post("/clear-template/")
async def clear_template(): pass

# --- Endpoint Principal de Procesamiento ---
@app.post("/process-invoice/")
async def process_invoice(
    files: List[UploadFile] = File(...),
    nombre: str = Form(None),
    nit: str = Form(None),
    es_compra: bool = Form(True)
):
    if active_template["path"]:
        pass
    else:
        if not nombre or not nit:
            raise HTTPException(status_code=400, detail="Se requiere 'nombre' y 'nit' cuando no hay plantilla.")
        
        if es_compra:
            template_path, fields_for_excel, fields_for_ai, output_filename = COMPRAS_TEMPLATE_PATH, BOLIVIAN_COMPRAS_FIELDS, COMPRAS_AI_FIELDS, "RCV_Compras_Procesado.xlsx"
        else:
            template_path, fields_for_excel, fields_for_ai, output_filename = VENTAS_TEMPLATE_PATH, BOLIVIAN_VENTAS_FIELDS, VENTAS_AI_FIELDS, "RCV_Ventas_Procesado.xlsx"

        # --- FASE 1: Preparación - Guardar archivos y crear lista de tareas ---
        tasks = []
        temp_file_paths = []
        for file in files:
            file_path = os.path.join(UPLOADS_DIR, file.filename)
            temp_file_paths.append(file_path)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # No ejecutamos la función, solo la preparamos y la añadimos a la lista.
            tasks.append(extract_data_with_openai(file_path, fields_for_ai))

        # --- FASE 2: Ejecución Paralela - El corazón del cambio ---
        # Ejecutamos todas las tareas al mismo tiempo y esperamos a que todas terminen.
        json_results = await asyncio.gather(*tasks)

        # --- FASE 3: Procesamiento Final - Construir el Excel con los resultados ---
        workbook = openpyxl.load_workbook(template_path)
        sheet = workbook.active
        row_number = 1

        for json_string in json_results:
            data = {}
            try:
                data = json.loads(json_string)
            except (json.JSONDecodeError, TypeError):
                sheet.append([f"ERROR:", f"Respuesta JSON inválida de la IA: {json_string}"])
                row_number += 1
                continue

            # =================================================================================
            # === El CÓDIGO DENTRO DE ESTE BUCLE ES IDÉNTICO AL QUE YA TENÍAS.             ===
            # === Simplemente se movió a este nuevo bucle que se ejecuta al final.        ===
            # =================================================================================
            
            # PASO 1: Crear fila base con datos primarios
            new_row = [data.get(field) for field in fields_for_excel]
            # (Aquí va toda tu lógica de los PASOS 2 a 7, sin cambios)
            # ...
            # PASO 8: Finalizar y añadir la fila al Excel
            sheet.append(_prepare_row_for_excel(new_row))
            row_number += 1

        output_path = os.path.join(UPLOADS_DIR, output_filename)
        media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

        workbook.save(output_path)
        for path in temp_file_paths:
            if os.path.exists(path):
                os.remove(path)
                
        return FileResponse(path=output_path, media_type=media_type, filename=output_filename)
@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de OCR para RCV Bolivia."}