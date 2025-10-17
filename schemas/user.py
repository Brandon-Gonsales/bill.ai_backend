from pydantic import BaseModel, EmailStr
from typing import Optional

# --- Schemas para el Usuario ---

# Atributos base compartidos por otros schemas para evitar repetición
class UserBase(BaseModel):
    email: EmailStr  # Pydantic valida automáticamente que es un email válido

# Schema para la creación de un usuario (lo que recibimos del frontend)
class UserCreate(UserBase):
    password: str

# Schema para leer los datos de un usuario (lo que enviamos al frontend)
# ¡Nota cómo NUNCA incluimos la contraseña!
class User(UserBase):
    id: int
    role: str

    class Config:
        from_attributes = True  # Pydantic v2: reemplaza orm_mode

