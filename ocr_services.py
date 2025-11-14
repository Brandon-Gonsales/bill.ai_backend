# ocr_services.py

import os
import json
from typing import List
from PIL import Image
from dotenv import load_dotenv
import base64
from io import BytesIO

# --- CAMBIO: Importar el cliente Asíncrono ---
from openai import AsyncOpenAI
import fitz

load_dotenv()
try:
    # --- CAMBIO: Usar el cliente Asíncrono ---
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not client.api_key:
        raise ValueError("La variable de entorno OPENAI_API_KEY no se encontró.")
except (ValueError, TypeError) as e:
    raise RuntimeError(f"Error en la configuración de la API de OpenAI: {e}")

# (Las listas de campos no cambian)
BOLIVIAN_COMPRAS_FIELDS = ["Nº", "ESPECIFICACION", "NIT PROVEEDOR", "RAZON SOCIAL PROVEEDOR", "CODIGO DE AUTORIZACION", "NUMERO FACTURA", "NUMERO DUI/DIM", "FECHA DE FACTURA/DUI/DIM", "IMPORTE TOTAL COMPRA", "IMPORTE ICE", "IMPORTE IEHD", "IMPORTE IPJ", "TASAS", "OTRO NO SUJETO A CREDITO FISCAL", "IMPORTES EXENTOS", "IMPORTE COMPRAS GRAVADAS A TASA CERO", "SUBTOTAL", "DESCUENTOS/BONIFICACIONES /REBAJAS SUJETAS AL IVA", "IMPORTE GIFT CARD", "IMPORTE BASE CF", "CREDITO FISCAL", "TIPO COMPRA", "CODIGO DE CONTROL"]
BOLIVIAN_VENTAS_FIELDS = ["Nº", "ESPECIFICACION", "FECHA DE LA FACTURA", "N° DE LA FACTURA", "CODIGO DE AUTORIZACION", "NIT / CI CLIENTE", "COMPLEMENTO", "NOMBRE O RAZON SOCIAL", "IMPORTE TOTAL DE LA VENTA", "IMPORTE ICE", "IMPORTE IEHD", "IMPORTE IPJ", "TASAS", "OTROS NO SUJETOS AL IVA", "EXPORTACIONES Y OPERACIONES EXENTAS", "VENTAS GRAVADAS A TASA CERO", "SUBTOTAL", "DESCUENTOS, BONIFICACIONES Y REBAJAS SUJETAS AL IVA", "IMPORTE GIFT CARD", "IMPORTE BASE PARA DEBITO FISCAL", "DEBITO FISCAL", "ESTADO", "CODIGO DE CONTROL", "TIPO DE VENTA"]


def _image_to_base64_url(image: Image.Image, format="jpeg") -> str:
    # (Esta función no cambia)
    buffered = BytesIO()
    if image.mode == 'RGBA':
        image = image.convert('RGB')
    image.save(buffered, format=format)
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return f"data:image/{format};base64,{img_str}"

# --- CAMBIO: Convertir la función a 'async def' ---
async def extract_data_with_openai(file_path: str, prompt_fields: List[str]) -> str:
    """
    Procesa un archivo, lo convierte a imágenes y llama a la API de OpenAI de forma asíncrona.
    """
    try:
        image_urls = []
        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension == '.pdf':
            doc = fitz.open(file_path)
            for page in doc:
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                image_urls.append(_image_to_base64_url(img))
            doc.close()
        elif file_extension in ['.png', '.jpg', '.jpeg', '.webp']:
            with Image.open(file_path) as img:
                image_urls.append(_image_to_base64_url(img))
        
        if not image_urls:
            return f'{{"error": "El archivo está vacío o no es un formato soportado."}}'

        fields_str = '", "'.join(prompt_fields)
        prompt = f"""Actúa como un experto en extracción de datos de facturas de Bolivia. Analiza la(s) imagen(es) de la factura y extrae los siguientes campos en formato JSON: "{fields_str}".
Reglas importantes:
1. El resultado debe ser EXCLUSIVAMENTE el objeto JSON.
2. Si un campo no se encuentra, su valor debe ser `null`."""

        messages = [
            { "role": "user", "content": [{"type": "text", "text": prompt}] + [{"type": "image_url", "image_url": {"url": url}} for url in image_urls] }
        ]
        
        # --- CAMBIO: Usar 'await' para la llamada a la API ---
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=2048,
            response_format={"type": "json_object"}
        )
        
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"ERROR en OpenAI Service: {e}")
        return f'{{"error": "Ocurrió un error al procesar con OpenAI.", "details": "{str(e)}"}}'