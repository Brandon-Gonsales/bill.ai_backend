from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

# Importamos todo lo que necesitamos:
from database import crud
from schemas import user as user_schema
from schemas import token as token_schema
from database.database import SessionLocal
from .auth_utils import get_password_hash, verify_password, create_access_token

# Un "router" es como una mini-aplicación. Agrupa endpoints relacionados.
router = APIRouter(
    tags=["Authentication"],
)

# --- Dependencia ---
# Esta es una función especial que nos presta una conexión a la base de datos
# para cada petición y se asegura de cerrarla al final.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Endpoint 1: Registro de un nuevo usuario ---
@router.post("/register", response_model=user_schema.User)
def create_user(user: user_schema.UserCreate, db: Session = Depends(get_db)):
    # 1. Verificamos si el email ya existe usando nuestra función de crud.py
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # 2. Encriptamos la contraseña del usuario
    hashed_password = get_password_hash(user.password)
    
    # 3. Creamos el usuario en la base de datos
    return crud.create_user(db=db, user=user, hashed_password=hashed_password)


# --- Endpoint 2: Login para obtener un token ---
@router.post("/token", response_model=token_schema.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    # 1. Buscamos al usuario por su email
    # (OAuth2PasswordRequestForm usa el campo 'username' para el email)
    user = crud.get_user_by_email(db, email=form_data.username)
    
    # 2. Si no existe o la contraseña es incorrecta, devolvemos un error
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Si todo es correcto, creamos un token de acceso
    access_token = create_access_token(
        data={"sub": user.email} # "sub" (subject) es el nombre estándar para el identificador del usuario
    )
    
    # 4. Devolvemos el token al usuario
    return {"access_token": access_token, "token_type": "bearer"}