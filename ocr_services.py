import easyocr
import google.generativeai as genai
from PIL import Image
import cv2
import numpy as np
import os
from pdf2image import convert_from_path
from typing import List

# --- Configuración de APIs (Carga desde variables de entorno) ---
# Crea un archivo .env en la raíz y añade tu clave: GOOGLE_API_KEY="AIza..."
from dotenv import load_dotenv
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Inicializa el lector de EasyOCR (solo una vez para mejorar el rendimiento)
reader = easyocr.Reader(['es', 'en']) # Puedes añadir más idiomas

def preprocess_image(image_path):
    """Mejora la calidad de la imagen para el OCR."""
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    # Aplicar umbral adaptativo para mejorar la binarización
    img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    # Opcional: Reducción de ruido
    img = cv2.medianBlur(img, 1)
    return Image.fromarray(img)

def file_to_text(file_path: str, ocr_engine: str, prompt_fields: List[str]) -> str:
    """Función principal que convierte un archivo (imagen o PDF) a texto usando el motor OCR especificado."""
    
    text_results = []
    
    if file_path.lower().endswith('.pdf'):
        images = convert_from_path(file_path)
        for i, image in enumerate(images):
            if ocr_engine == 'gemini':
                # Gemini puede manejar imágenes directamente
                 text_results.append(ocr_with_gemini(image, prompt_fields))
            else: # easyocr
                temp_image_path = f"temp_page_{i}.png"
                image.save(temp_image_path, 'PNG')
                text_results.append(ocr_with_easyocr(temp_image_path))
                os.remove(temp_image_path)
    else: # Es una imagen
        if ocr_engine == 'gemini':
             return ocr_with_gemini(Image.open(file_path), prompt_fields)
        elif ocr_engine == 'easyocr':
            return ocr_with_easyocr(file_path)

    # Si fue un PDF, Gemini ya devolvió datos estructurados, los otros devuelven texto plano
    return "\n".join(text_results)

def ocr_with_easyocr(image_path: str) -> str:
    """Extrae texto de una imagen usando EasyOCR."""
    try:
        # detail=0 devuelve solo el texto, paragraph=True intenta agruparlo
        result = reader.readtext(image_path, detail=0, paragraph=True)
        return "\n".join(result)
    except Exception as e:
        return f"Error con EasyOCR: {e}"

def ocr_with_gemini(image: Image.Image, fields_to_extract: List[str]) -> str:
    """Extrae datos estructurados de una imagen usando Gemini Pro Vision."""
    try:
        model = genai.GenerativeModel('gemini-pro-vision')
        
        # Crear un prompt dinámico basado en los campos del Excel
        prompt = f"""
        Analiza la siguiente imagen de una factura. Extrae los siguientes campos y devuelve el resultado en formato JSON.
        Los campos a extraer son: {', '.join(fields_to_extract)}.
        
        Si un campo no se encuentra, devuélvelo como "N/A".
        
        Ejemplo de respuesta esperada:
        {{
          "{fields_to_extract[0]}": "valor_extraido_1",
          "{fields_to_extract[1]}": "valor_extraido_2",
          ...
        }}
        """
        
        response = model.generate_content([prompt, image])
        # Limpiar la respuesta para que sea un JSON válido
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        return cleaned_response
    except Exception as e:
        return f"Error con Gemini API: {e}"