### **Cómo Correrlo en Local (Versión Simplificada)**

El proceso es ahora más sencillo ya que no hay dependencias externas al ecosistema de Python.

1.  **Instala las dependencias de Python:**
    Abre una terminal en la raíz del proyecto y ejecuta:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Crea tu archivo `.env`:**
    En la misma carpeta, crea un archivo llamado `.env` y añade tu clave de la API de Google AI Studio:
    ```
    GOOGLE_API_KEY="AIzaSy...tu_clave_aqui"
    ```

3.  **Inicia el servidor:**
    En la terminal, ejecuta:
    ```bash
    uvicorn main:app --reload
    ```

4.  **Usa la API:**
    Abre tu navegador en **`http://127.0.0.1:8000/docs`**. La interfaz de Swagger te permitirá probar los endpoints `/upload-template/` y `/process-invoice/` como se describió anteriormente, pero ahora solo verás las opciones `easyocr` y `gemini` en el desplegable.

---

### **Cómo Correrlo en Render (Versión Simplificada)**

¡Aquí es donde más se nota la ventaja de eliminar Tesseract! **Ya no necesitas un Dockerfile.** Puedes hacer un despliegue directo usando el entorno de ejecución estándar de Python de Render.

1.  **Prepara tu Repositorio de Git:**
    *   Asegúrate de que todo tu código, incluyendo el `requirements.txt` actualizado, esté en un repositorio de GitHub, GitLab o Bitbucket.
    *   Añade un archivo `.gitignore` si aún no lo tienes.

2.  **Crea el Servicio en Render:**
    *   En tu Dashboard de Render, haz clic en **"New +"** y selecciona **"Web Service"**.
    *   Conecta tu cuenta de Git y elige el repositorio de la API.

3.  **Configura el Servicio:**
    *   **Name:** `factura-ocr-api` (o el que prefieras).
    *   **Runtime:** Render detectará `requirements.txt` y seleccionará **"Python 3"** automáticamente. ¡Déjalo así!
    *   **Build Command:** `pip install -r requirements.txt`. Render suele autocompletar esto correctamente.
    *   **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`. Este comando es fundamental para que Render pueda ejecutar tu aplicación correctamente.

4.  **Añade las Variables de Entorno:**
    *   En la configuración, ve a la pestaña **"Environment"**.
    *   Haz clic en **"Add Environment Variable"**.
    *   **Key:** `GOOGLE_API_KEY`
    *   **Value:** `AIzaSy...tu_clave_aqui` (Pega aquí tu clave secreta).

5.  **Despliega:**
    *   Haz clic en **"Create Web Service"**. Render se encargará de todo: instalará las dependencias de Python y pondrá en marcha tu aplicación.
    *   En pocos minutos, tu servicio estará disponible en la URL pública que Render te proporcione.

Como puedes ver, esta versión es mucho más limpia y fácil de desplegar, manteniendo las funcionalidades de OCR más potentes.