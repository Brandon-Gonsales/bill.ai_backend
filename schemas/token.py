from pydantic import BaseModel, EmailStr
from typing import Optional

# --- Schemas para la Autenticación (Tokens) ---

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[EmailStr] = None