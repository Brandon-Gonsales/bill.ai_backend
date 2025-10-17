from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import models
from database.database import engine

# 1. Importamos nuestro nuevo router de autenticación
from routers import auth
from routers import lotes

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Factura OCR API (con Usuarios y Lotes)",
    description="API para procesar facturas en lotes persistentes."
)

# ... (tu configuración de CORS no cambia)
origins = [
    "http://localhost:5173", "http://localhost:5174", "http://localhost:5175",
    "https://bill-ai-frontend.vercel.app",
    "https://bill-ai-frontend-git-develop-brandon-gonsales-projects.vercel.app",
]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


# 2. "Enchufamos" el router de autenticación a la aplicación principal.
# Ahora, FastAPI sabe que existen los endpoints /register y /token.
app.include_router(auth.router)
app.include_router(lotes.router)


@app.get("/")
def read_root():
    return {"message": "Bienvenido a la nueva API de Facturas v2.0"}