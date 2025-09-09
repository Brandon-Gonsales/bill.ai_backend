import os
import shutil
import json
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse
import openpyxl
from typing import Literal

from ocr_services import file_to_text

# --- Inicialización de la App y directorios ---
app = FastAPI(title="Factura OCR API", description="API para extraer datos de facturas a Excel.")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Guardamos la plantilla activa en memoria (en una app real se usaría una DB o un sistema de caché)
active_template = {"path": None, "fields": []}

@app.post("/upload-template/")
async def upload_template(file: UploadFile = File(...)):
    """
    Endpoint para subir una plantilla de Excel.
    La primera fila de la hoja activa debe contener los nombres de los campos a extraer.
    """
    if not file.filename.endswith(('.xlsx')):
        raise HTTPException(status_code=400, detail="El archivo debe ser un .xlsx")

    template_path = os.path.join(TEMPLATES_DIR, "template.xlsx")
    
    with open(template_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        workbook = openpyxl.load_workbook(template_path)
        sheet = workbook.active
        # Leemos los encabezados de la primera fila
        headers = [cell.value for cell in sheet[1] if cell.value]
        
        if not headers:
            raise HTTPException(status_code=400, detail="La plantilla no tiene encabezados en la primera fila.")
            
        active_template["path"] = template_path
        active_template["fields"] = headers
        
        return {"message": "Plantilla cargada exitosamente", "campos_detectados": headers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo procesar la plantilla: {e}")

@app.post("/process-invoice/")
async def process_invoice(
    # CAMBIO IMPORTANTE: Eliminado 'tesseract' de las opciones válidas
    ocr_engine: Literal['easyocr', 'gemini'] = Form(...),
    file: UploadFile = File(...)
):
    """
    Endpoint para procesar una factura (imagen o PDF) y extraer datos.
    Requiere que una plantilla haya sido subida previamente.
    """
    if not active_template["path"]:
        raise HTTPException(status_code=400, detail="Primero debe subir una plantilla de Excel a través del endpoint /upload-template/")

    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ['.png', '.jpg', '.jpeg', '.pdf']:
        raise HTTPException(status_code=400, detail="Formato de archivo no soportado. Use PNG, JPG o PDF.")

    # Guardar el archivo subido temporalmente
    file_path = os.path.join(UPLOADS_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # --- Extracción de Texto con el motor OCR seleccionado ---
    extracted_text_or_json = file_to_text(file_path, ocr_engine, active_template["fields"])
    
    # --- Procesamiento de resultados y generación de Excel ---
    try:
        workbook = openpyxl.load_workbook(active_template["path"])
        sheet = workbook.active
        
        extracted_data = {}
        
        if ocr_engine == 'gemini':
            # Gemini ya devuelve un JSON (en formato string), lo parseamos
            try:
                extracted_data = json.loads(extracted_text_or_json)
            except json.JSONDecodeError:
                 raise HTTPException(status_code=500, detail=f"Gemini no devolvió un JSON válido. Respuesta: {extracted_text_or_json}")
        else:
            # Para EasyOCR, hacemos una búsqueda simple de palabras clave
            text_lines = extracted_text_or_json.lower().split('\n')
            for field in active_template["fields"]:
                found = False
                for line in text_lines:
                    if field.lower() in line:
                        try:
                            value = line.split(field.lower())[1].strip().replace(':', '').strip()
                            extracted_data[field] = value
                            found = True
                            break
                        except IndexError:
                            continue
                if not found:
                    extracted_data[field] = "N/A" # No encontrado
        
        # Escribir los datos en una nueva fila
        new_row = []
        for field in active_template["fields"]:
            new_row.append(extracted_data.get(field, "N/A"))
            
        sheet.append(new_row)
        
        output_filename = f"processed_{os.path.splitext(os.path.basename(active_template['path']))[0]}.xlsx"
        output_path = os.path.join(UPLOADS_DIR, output_filename)
        workbook.save(output_path)
        
        # Limpiar el archivo subido
        os.remove(file_path)

        return FileResponse(path=output_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=output_filename)

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Error procesando el archivo Excel: {e}")

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de OCR para Facturas. Visita /docs para la documentación interactiva."}

