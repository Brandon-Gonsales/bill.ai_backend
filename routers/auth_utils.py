from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

# Importamos la configuración que acabamos de crear
from core.config import settings

# --- Herramienta 1: Manejo de Contraseñas ---
# Esto configura el algoritmo para encriptar contraseñas (bcrypt es el estándar).
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """Compara una contraseña de texto plano con una encriptada."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Encripta una contraseña de texto plano."""
    return pwd_context.hash(password)


# --- Herramienta 2: Creación de Tokens de Acceso (JWT) ---
def create_access_token(data: dict):
    """Crea un token JWT que el usuario usará para autenticarse."""
    to_encode = data.copy()
    
    # Calculamos cuándo debe expirar el token
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    # Creamos el token usando nuestra llave secreta
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt