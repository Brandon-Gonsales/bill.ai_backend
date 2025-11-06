# ocr_services.py - Versión para OpenAI con PyMuPDF

import os
import json
from typing import List
from PIL import Image
from dotenv import load_dotenv
import base64
from io import BytesIO

# --- NUEVAS IMPORTACIONES ---
from openai import OpenAI
import fitz  # Esta es la librería PyMuPDF

# --- Configuración de la API de OpenAI ---
load_dotenv()
try:
    # Creamos un "cliente" de OpenAI que usaremos para hacer las llamadas
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not client.api_key:
        raise ValueError("La variable de entorno OPENAI_API_KEY no se encontró.")
except (ValueError, TypeError) as e:
    raise RuntimeError(f"Error en la configuración de la API de OpenAI: {e}")

# (Las listas de campos para Bolivia no cambian, las mantenemos igual)
BOLIVIAN_COMPRAS_FIELDS = ["Nº", "ESPECIFICACION", "NIT PROVEEDOR", "RAZON SOCIAL PROVEEDOR", "CODIGO DE AUTORIZACION", "NUMERO FACTURA", "NUMERO DUI/DIM", "FECHA DE FACTURA/DUI/DIM", "IMPORTE TOTAL COMPRA", "IMPORTE ICE", "IMPORTE IEHD", "IMPORTE IPJ", "TASAS", "OTRO NO SUJETO A CREDITO FISCAL", "IMPORTES EXENTOS", "IMPORTE COMPRAS GRAVADAS A TASA CERO", "SUBTOTAL", "DESCUENTOS/BONIFICACIONES /REBAJAS SUJETAS AL IVA", "IMPORTE GIFT CARD", "IMPORTE BASE CF", "CREDITO FISCAL", "TIPO COMPRA", "CODIGO DE CONTROL"]
BOLIVIAN_VENTAS_FIELDS = ["Nº", "ESPECIFICACION", "FECHA DE LA FACTURA", "N° DE LA FACTURA", "CODIGO DE AUTORIZACION", "NIT / CI CLIENTE", "COMPLEMENTO", "NOMBRE O RAZON SOCIAL", "IMPORTE TOTAL DE LA VENTA", "IMPORTE ICE", "IMPORTE IEHD", "IMPORTE IPJ", "TASAS", "OTROS NO SUJETOS AL IVA", "EXPORTACIONES Y OPERACIONES EXENTAS", "VENTAS GRAVADAS A TASA CERO", "SUBTOTAL", "DESCUENTOS, BONIFICACIONES Y REBAJAS SUJETAS AL IVA", "IMPORTE GIFT CARD", "IMPORTE BASE PARA DEBITO FISCAL", "DEBITO FISCAL", "ESTADO", "CODIGO DE CONTROL", "TIPO DE VENTA"]


# --- Función auxiliar para preparar las imágenes para OpenAI ---
def _image_to_base64_url(image: Image.Image, format="jpeg") -> str:
    """Convierte una imagen a un formato de texto (Base64) que OpenAI entiende."""
    buffered = BytesIO()
    if image.mode == 'RGBA': # Si es PNG con transparencia
        image = image.convert('RGB') # La convertimos a JPG para evitar errores
    image.save(buffered, format=format)
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return f"data:image/{format};base64,{img_str}"

# --- La Nueva Función Principal de Extracción ---
# Esta única función reemplaza a 'extract_data_with_template' y 'extract_data_without_template'
def extract_data_with_openai(file_path: str, prompt_fields: List[str]) -> str:
    """
    Procesa un archivo PDF o de texto, extrae el texto y llama al modelo GPT-5-nano.
    """
    try:
        text_content = ""
        file_extension = os.path.splitext(file_path)[1].lower()

        # --- Extraer texto si es PDF ---
        if file_extension == ".pdf":
            doc = fitz.open(file_path)
            for page in doc:
                text_content += page.get_text("text") + "\n"
            doc.close()
        elif file_extension in [".txt", ".csv", ".json"]:
            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()
        else:
            return json.dumps({"error": "Formato no soportado para gpt-5-nano (usa texto o PDF con texto)"})

        if not text_content.strip():
            return json.dumps({"error": "No se encontró texto en el archivo."})

        # --- Construir el prompt ---
        fields_str = '", "'.join(prompt_fields)
        prompt = f"""Actúa como un experto en extracción de datos de facturas bolivianas.
                    A partir del siguiente texto, extrae los campos: "{fields_str}".
                    Devuelve exclusivamente un JSON con esos campos. Si falta alguno, usa null.
                    Texto de la factura:
                    {text_content}
                    """

        # --- Llamada a OpenAI ---
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=2048
        )

        # --- Procesar respuesta ---
        content = response.choices[0].message.content.strip()
        # Intentamos asegurar que sea JSON válido
        try:
            json.loads(content)
            return content
        except:
            return json.dumps({"error": "Respuesta no válida o error de procesamiento", "raw": content})

    except Exception as e:
        print(f"ERROR en OpenAI Service: {e}")
        return json.dumps({"error": "Ocurrió un error al procesar con OpenAI.", "details": str(e)})
