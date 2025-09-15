import os
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

def file_to_text(file_path: str, prompt_fields: List[str]) -> str:
    """
    Dispatcher principal que detecta el tipo de archivo y lo procesa de forma nativa con Gemini.
    - Imágenes se envían directamente.
    - PDFs se suben con la File API y luego se procesan.

    Args:
        file_path: La ruta al archivo local (PDF o imagen).
        prompt_fields: Lista de campos a extraer.

    Returns:
        Una cadena con formato JSON que contiene los datos extraídos.
    """
    media_part: Union[Image.Image, File]
    
    try:
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            # Flujo para PDFs: Subir el archivo y obtener una referencia.
            pdf_file = genai.upload_file(path=file_path, display_name=os.path.basename(file_path))
            media_part = pdf_file
        elif file_extension in ['.png', '.jpg', '.jpeg', '.webp']:
            # Flujo para imágenes: Abrir el archivo.
            media_part = Image.open(file_path)
        else:
            return f'{{"error": "Formato de archivo no soportado: {file_extension}"}}'

        # Llamar a la función interna que se comunica con Gemini
        return _call_gemini_api(media_part, prompt_fields)

    except Exception as e:
        return f'{{"error": "Ocurrió un error al procesar el archivo.", "details": "{str(e)}"}}'

def _call_gemini_api(media_part: Union[Image.Image, File], fields_to_extract: List[str]) -> str:
    """
    Función interna que construye el prompt y llama a la API de Gemini.
    """
    try:
        # gemini-1.5-pro-latest es ideal para analizar documentos complejos como PDFs.
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        fields_str = '", "'.join(fields_to_extract)
        prompt = f"""
Actúa como un experto en extracción de datos de facturas.
Analiza el documento adjunto. Extrae únicamente los siguientes campos y devuelve el resultado estrictamente en formato JSON:

"{fields_str}"

REGLAS ESTRICTAS:
1. El resultado DEBE SER un único objeto JSON válido. No incluyas texto, explicaciones, ni la palabra "json" antes o después del objeto.
2. El JSON debe contener exclusivamente los campos de la lista indicada.
3. Si un campo no se encuentra en la factura, su valor debe ser `null`.
4. Para los campos numéricos (como montos o totales), devuelve un tipo de dato numérico (ej: 123.45), no un string (ej: "123.45").

Ejemplo de salida esperada:
{{
  "Fecha": "2025-09-07",
  "Total": 356.40,
  "Cliente": "KEVIN RODRIGO SOTO HERRERA"
}}
"""
        content = [prompt, media_part]
        response = model.generate_content(content)
        
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        return cleaned_response

    except Exception as e:
        return f'{{"error": "Ocurrió un error al contactar la API de Gemini.", "details": "{str(e)}"}}'