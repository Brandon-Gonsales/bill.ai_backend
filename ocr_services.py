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

def extract_data_without_template(file_path: str, user_name: str, user_nit: str) -> str:
    """
    Procesa una factura para rellenar el RCV de Bolivia, determinando si es Compra o Venta.
    """
    try:
        media_part = _get_media_part(file_path)
        if media_part is None: return f'{{"error": "Formato de archivo no soportado."}}'

        model = genai.GenerativeModel('gemini-2.5-pro')
        
        # --- CAMBIO: Prompt altamente especializado para el RCV de Bolivia ---
        prompt = f"""
Actúa como un contador experto llenando el Registro de Compras y Ventas (RCV) de Bolivia. Te daré una factura y los datos de la empresa que registra. Tu tarea es clasificar la factura y extraer los datos para llenar la plantilla correspondiente.

**Datos de la Empresa Registrando:**
- Nombre/Razón Social: "{user_name}"
- NIT: "{user_nit}"

**Paso 1: Clasificación de la Factura**
- Es una **COMPRA** si el NIT de la empresa ({user_nit}) aparece como el **receptor** (en el campo "NIT/CI/CEX").
- Es una **VENTA** si el NIT de la empresa ({user_nit}) aparece como el **emisor** (en el campo "NIT" de la cabecera).

**Paso 2: Extracción de Datos según la Plantilla RCV**
- Si es una **COMPRA**, extrae los datos para estos campos: {json.dumps(BOLIVIAN_COMPRAS_FIELDS)}
- Si es una **VENTA**, extrae los datos para estos campos: {json.dumps(BOLIVIAN_VENTAS_FIELDS)}

**Reglas de Mapeo y Llenado:**
- **"NIT PROVEEDOR"**: Es el NIT del emisor de la factura.
- **"RAZON SOCIAL PROVEEDOR"**: Es el nombre del emisor de la factura.
- **"NIT / CI CLIENTE"**: Es el NIT del receptor de la factura.
- **"NOMBRE O RAZON SOCIAL"**: Es el nombre del receptor de la factura.
- **"CODIGO DE AUTORIZACION"**: Extrae el código de autorización.
- **"NUMERO FACTURA"** o **"N° DE LA FACTURA"**: Extrae el número de la factura.
- **"FECHA DE FACTURA/DUI/DIM"** o **"FECHA DE LA FACTURA"**: Extrae la fecha en formato AAAA-MM-DD.
- **"IMPORTE TOTAL COMPRA"** o **"IMPORTE TOTAL DE LA VENTA"**: Usa el "MONTO A PAGAR" o total final.
- **"IMPORTE BASE CF"** o **"IMPORTE BASE PARA DEBITO FISCAL"**: Usa el "IMPORTE BASE CRÉDITO FISCAL".
- **"CREDITO FISCAL"** o **"DEBITO FISCAL"**: Calcula el 13% del importe base. Sé preciso.
- **Valores por defecto (si no están en la factura)**: Para campos como "IMPORTE ICE", "IMPORTE IEHD", "TASAS", "DESCUENTOS...", si no los encuentras, usa `0.00`.
- **"ESPECIFICACION"**: Usa `1` para Compras y `2` para Ventas.
- **"ESTADO"**: Para Ventas, asume siempre "V" (Válida).
- **"Nº"**: Deja este campo como `null`, se llenará después.
- **Campos no presentes en la factura** (ej: "NUMERO DUI/DIM", "TIPO COMPRA"): Déjalos como `null`.

**Formato de Salida Obligatorio:**
Devuelve un único objeto JSON con dos claves: "tipo_factura" (con el valor "Compra" o "Venta") y "datos" (un objeto con los campos de la plantilla RCV correspondiente llenados).

Analiza el documento y proporciona la respuesta.
"""
        content = [prompt, media_part]
        response = model.generate_content(content)
        return response.text.strip().replace('```json', '').replace('```', '')
    except Exception as e:
        return f'{{"error": "Ocurrió un error en el flujo sin plantilla.", "details": "{str(e)}"}}'