# Dockerfile

# 1. Usa una imagen base oficial de Python. La versión 3.10 es una buena elección.
FROM python:3.10-slim

# 2. Establece el directorio de trabajo dentro del contenedor.
WORKDIR /app

# 3. Copia los requerimientos PRIMERO por caché. Si no cambian, Docker no reinstalará todo.
COPY requirements.txt requirements.txt

# 4. Instala las dependencias.
# --no-cache-dir reduce el tamaño de la imagen final.
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copia TODO el resto de tu proyecto (main.py, ocr_services.py, la carpeta templates, etc.)
COPY . .

# 6. Cloud Run envía el tráfico al puerto 8080 por defecto.
ENV PORT 8080

# 7. El comando para iniciar la aplicación en producción.
# Le dice a Gunicorn que inicie 4 workers, usando la clase de worker de Uvicorn,
# que escuche en todas las interfaces en el puerto que especifica la variable $PORT,

# y que ejecute la instancia 'app' que está dentro del archivo 'main.py'.
CMD gunicorn -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT main:app