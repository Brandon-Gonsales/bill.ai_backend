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

def classify_invoice_type(file_path: str, user_name: str, user_nit: str) -> str:
    """
    Clasifica una factura extrayendo campos de cliente y aplicando lógica en Python.
    """
    # Lista de todos los posibles campos que identifican al cliente/receptor
    CUSTOMER_NAME_FIELDS = ["Nombre o Razon Social", "NOMBRE/RAZÓN SOCIAL", "RAZON SOCIAL", "Señor (es)"]
    CUSTOMER_NIT_FIELDS = ["NIT/CI/CEX", "NIT/C.I.", "NIT/CI/CEX/P", "NIT/C.I./C.Ex./P."]
    fields_to_check = CUSTOMER_NAME_FIELDS + CUSTOMER_NIT_FIELDS

    # 1. Usamos la función de extracción para obtener los valores de esos campos
    json_string = extract_data_with_template(file_path, fields_to_check)

    try:
        extracted_data = json.loads(json_string)
        
        # Preparamos los datos del usuario para una comparación robusta
        user_nit_clean = str(user_nit).strip()
        user_name_clean = user_name.lower().strip()

        # 2. Iteramos sobre los valores extraídos para buscar una coincidencia
        for field, value in extracted_data.items():
            if value is None:
                continue # Ignoramos campos no encontrados

            value_clean = str(value).lower().strip()

            # Verificación del NIT (coincidencia exacta)
            if field in CUSTOMER_NIT_FIELDS and value_clean == user_nit_clean:
                print(f"INFO: Clasificado como Compra por coincidencia de NIT: {value}")
                return "Compra"
            
            # Verificación del Nombre (coincidencia parcial, más flexible)
            if field in CUSTOMER_NAME_FIELDS and user_name_clean in value_clean:
                print(f"INFO: Clasificado como Compra por coincidencia de Nombre: {value}")
                return "Compra"

        # 3. Si el bucle termina sin encontrar coincidencias, es una Venta
        print("INFO: No se encontraron coincidencias de cliente, clasificado como Venta.")
        return "Venta"

    except (json.JSONDecodeError, Exception) as e:
        print(f"ERROR: Fallo en la clasificación. No se pudo procesar la respuesta de la IA. Error: {e}")
        return "Indeterminado"
    
def extract_data_without_template(file_path: str, user_name: str, user_nit: str) -> str:
    # Paso 1: Clasificar la factura con la nueva lógica robusta
    invoice_type = classify_invoice_type(file_path, user_name, user_nit)

    # Paso 2: Seleccionar los campos correctos y manejar errores
    if invoice_type == "Compra":
        fields_to_extract = BOLIVIAN_COMPRAS_FIELDS
    elif invoice_type == "Venta":
        fields_to_extract = BOLIVIAN_VENTAS_FIELDS
    else:
        error_data = {
            "error": "Fallo en la Clasificación",
            "details": f"No se pudo determinar si la factura es una compra o una venta."
        }
        final_error_response = {"tipo_factura": "Error", "datos": error_data}
        return json.dumps(final_error_response, ensure_ascii=False)

    # Paso 3: Extraer todos los datos usando la función de alto rendimiento
    extracted_json_string = extract_data_with_template(file_path, fields_to_extract)

    # Paso 4: Empaquetar la respuesta final
    try:
        extracted_data = json.loads(extracted_json_string)
        if invoice_type == "Compra":
            extracted_data["ESPECIFICACION"] = 1
        elif invoice_type == "Venta":
            extracted_data["ESPECIFICACION"] = 2
            extracted_data["ESTADO"] = "V"

        final_response = {
            "tipo_factura": invoice_type,
            "datos": extracted_data
        }
        return json.dumps(final_response, ensure_ascii=False)
    except json.JSONDecodeError:
        error_data = {
            "error": "Fallo en la Extracción",
            "details": "La IA devolvió un formato JSON no válido.",
            "raw_response": extracted_json_string
        }
        final_error_response = {"tipo_factura": invoice_type, "datos": error_data}
        return json.dumps(final_error_response, ensure_ascii=False)