import os
import json
from typing import List, Union
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv
from google.generativeai.types import File

# --- Configuración de la API de Gemini ---
load_dotenv()
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("La variable de entorno GOOGLE_API_KEY no se encontró.")
    genai.configure(api_key=api_key)
except (ValueError, TypeError) as e:
    raise RuntimeError(f"Error en la configuración de la API de Gemini: {e}")

# --- CAMBIO: Listas de columnas oficiales para el RCV de Bolivia ---
BOLIVIAN_COMPRAS_FIELDS = [
    "Nº", "ESPECIFICACION", "NIT PROVEEDOR", "RAZON SOCIAL PROVEEDOR", 
    "CODIGO DE AUTORIZACION", "NUMERO FACTURA", "NUMERO DUI/DIM", 
    "FECHA DE FACTURA/DUI/DIM", "IMPORTE TOTAL COMPRA", "IMPORTE ICE", 
    "IMPORTE IEHD", "IMPORTE IPJ", "TASAS", "OTRO NO SUJETO A CREDITO FISCAL", 
    "IMPORTES EXENTOS", "IMPORTE COMPRAS GRAVADAS A TASA CERO", "SUBTOTAL", 
    "DESCUENTOS/BONIFICACIONES /REBAJAS SUJETAS AL IVA", "IMPORTE GIFT CARD", 
    "IMPORTE BASE CF", "CREDITO FISCAL", "TIPO COMPRA", "CODIGO DE CONTROL"
]

BOLIVIAN_VENTAS_FIELDS = [
    "Nº", "ESPECIFICACION", "FECHA DE LA FACTURA", "N° DE LA FACTURA", 
    "CODIGO DE AUTORIZACION", "NIT / CI CLIENTE", "COMPLEMENTO", 
    "NOMBRE O RAZON SOCIAL", "IMPORTE TOTAL DE LA VENTA", "IMPORTE ICE", 
    "IMPORTE IEHD", "IMPORTE IPJ", "TASAS", "OTROS NO SUJETOS AL IVA", 
    "EXPORTACIONES Y OPERACIONES EXENTAS", "VENTAS GRAVADAS A TASA CERO", 
    "SUBTOTAL", "DESCUENTOS, BONIFICACIONES Y REBAJAS SUJETAS AL IVA", 
    "IMPORTE GIFT CARD", "IMPORTE BASE PARA DEBITO FISCAL", "DEBITO FISCAL", 
    "ESTADO", "CODIGO DE CONTROL", "TIPO DE VENTA"
]

def _get_media_part(file_path: str) -> Union[Image.Image, File, None]:
    """Función auxiliar para obtener la parte multimedia (imagen o PDF) del archivo."""
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension == '.pdf':
        return genai.upload_file(path=file_path, display_name=os.path.basename(file_path))
    elif file_extension in ['.png', '.jpg', '.jpeg', '.webp']:
        return Image.open(file_path)
    return None

def extract_data_with_template(file_path: str, prompt_fields: List[str]) -> str:
    """Procesa un archivo usando una plantilla personalizada del usuario."""
    # (Sin cambios en esta función)
    try:
        media_part = _get_media_part(file_path)
        if media_part is None: return f'{{"error": "Formato de archivo no soportado."}}'
        model = genai.GenerativeModel('gemini-2.5-pro')
        fields_str = '", "'.join(prompt_fields)
        prompt = f"""Actúa como un experto en extracción de datos. Analiza el documento y extrae los siguientes campos en formato JSON: "{fields_str}". Reglas: El resultado debe ser solo el objeto JSON. Si un campo no se encuentra, su valor debe ser `null`. Los valores numéricos deben ser números, no strings."""
        content = [prompt, media_part]
        response = model.generate_content(content)
        return response.text.strip().replace('```json', '').replace('```', '')
    except Exception as e:
        return f'{{"error": "Ocurrió un error al procesar con plantilla.", "details": "{str(e)}"}}'

    
def extract_data_without_template(file_path: str, fields_to_extract: List[str]) -> str:
    return extract_data_with_template(file_path, fields_to_extract)