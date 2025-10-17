from pydantic import BaseModel
from typing import Optional

# Importamos el schema del Usuario para poder anidarlo
from .user import User

# --- Schemas para el Lote ---

# Atributos base de un lote
class LoteBase(BaseModel):
    name: str
    company_name: str
    company_nit: str

# Schema para la creación de un lote
class LoteCreate(LoteBase):
    pass # No necesita campos adicionales por ahora

# Schema principal para leer los datos de un lote
class Lote(LoteBase):
    id: int
    excel_filename: str
    owner_id: int
    
    # Opcional pero muy útil: Muestra la información del dueño del lote
    # owner: User 

    class Config:
        from_attributes = True