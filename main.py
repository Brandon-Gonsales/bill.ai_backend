import os
import shutil
import json
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import openpyxl
from typing import List # CAMBIO: Importar List para manejar múltiples archivos

from ocr_services import file_to_text

# --- Inicialización de la App y directorios ---
app = FastAPI(title="Factura OCR API (Procesamiento por Lotes)", description="API para extraer datos de múltiples facturas a Excel usando Gemini.")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

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
        headers = [cell.value for cell in sheet[1] if cell.value]
        
        if not headers:
            raise HTTPException(status_code=400, detail="La plantilla no tiene encabezados en la primera fila.")
            
        active_template["path"] = template_path
        active_template["fields"] = headers
        
        return {"message": "Plantilla cargada exitosamente", "campos_detectados": headers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo procesar la plantilla: {e}")

@app.post("/process-invoice/")
# CAMBIO: La firma ahora acepta una LISTA de UploadFile
async def process_invoice(files: List[UploadFile] = File(...)):
    """
    Endpoint para procesar una o más facturas (imágenes o PDFs) y extraer los datos.
    """
    if not active_template["path"]:
        raise HTTPException(status_code=400, detail="Primero debe subir una plantilla de Excel a través del endpoint /upload-template/")

    # CAMBIO: Cargar el libro de trabajo UNA SOLA VEZ, antes de empezar a procesar los archivos.
    try:
        workbook = openpyxl.load_workbook(active_template["path"])
        sheet = workbook.active
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo cargar la plantilla de Excel: {e}")

    temp_file_paths = [] # Lista para guardar las rutas de los archivos temporales y borrarlos al final

    # CAMBIO: Bucle para procesar cada archivo subido
    for file in files:
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in ['.png', '.jpg', '.jpeg', '.pdf', '.webp']:
            # Si un archivo no es válido, podemos saltarlo y continuar con los demás
            print(f"Archivo omitido por formato no válido: {file.filename}")
            continue

        file_path = os.path.join(UPLOADS_DIR, file.filename)
        temp_file_paths.append(file_path) # Añadir a la lista para borrarlo después
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        extracted_json_string = file_to_text(file_path, active_template["fields"])
        
        try:
            extracted_data = json.loads(extracted_json_string)
            if 'error' in extracted_data:
                print(f"Error procesando {file.filename}: {extracted_data.get('details', 'Error desconocido')}")
                # Creamos una fila de error para saber qué archivo falló
                new_row = [f"ERROR: {file.filename}"] + ["Error al procesar"] * (len(active_template["fields"]) - 1)
            else:
                # Construir la fila con los datos extraídos
                new_row = [extracted_data.get(field) for field in active_template["fields"]]
            
            sheet.append(new_row)

        except json.JSONDecodeError:
            print(f"Error: Gemini no devolvió un JSON válido para el archivo {file.filename}. Respuesta: {extracted_json_string}")
            new_row = [f"ERROR: {file.filename}"] + ["Respuesta no válida"] * (len(active_template["fields"]) - 1)
            sheet.append(new_row)
        except Exception as e:
            print(f"Error inesperado procesando {file.filename}: {e}")
            new_row = [f"ERROR: {file.filename}"] + [f"Error: {e}"] * (len(active_template["fields"]) - 1)
            sheet.append(new_row)

    # CAMBIO: Guardar el archivo Excel UNA SOLA VEZ, después de procesar todos los archivos.
    output_filename = f"processed_batch_{active_template['path'].split('/')[-1]}.xlsx"
    output_path = os.path.join(UPLOADS_DIR, output_filename)
    workbook.save(output_path)
    
    # CAMBIO: Limpiar todos los archivos temporales que se subieron
    for path in temp_file_paths:
        if os.path.exists(path):
            os.remove(path)

    return FileResponse(path=output_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=output_filename)

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de OCR para Facturas (v4 - Lotes). Visita /docs para la documentación."}