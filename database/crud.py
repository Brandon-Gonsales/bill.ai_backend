from sqlalchemy.orm import Session

# Importamos los modelos (la estructura de la DB) y los schemas (la estructura de la API)
from database import models
from schemas import user as user_schema
from schemas import lote as lote_schema

# --- Funciones CRUD para el Usuario ---

def get_user_by_email(db: Session, email: str):
    """
    Busca y devuelve un usuario por su email.
    """
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: user_schema.UserCreate, hashed_password: str):
    """
    Crea un nuevo usuario en la base de datos.
    """
    # Creamos un objeto User del modelo de SQLAlchemy
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user) # Lo añadimos a la sesión de la base de datos
    db.commit() # Guardamos los cambios en la base de datos
    db.refresh(db_user) # Refrescamos el objeto para obtener su nuevo ID
    return db_user


# --- Funciones CRUD para el Lote ---

def get_lotes_by_owner(db: Session, owner_id: int, skip: int = 0, limit: int = 100):
    """
    Obtiene una lista de todos los lotes que pertenecen a un usuario.
    Incluye paginación simple (skip, limit).
    """
    return db.query(models.Lote).filter(models.Lote.owner_id == owner_id).offset(skip).limit(limit).all()

def get_lote_by_id(db: Session, lote_id: int):
    """
    Busca y devuelve un lote por su ID.
    """
    return db.query(models.Lote).filter(models.Lote.id == lote_id).first()

def create_lote(db: Session, lote: lote_schema.LoteCreate, excel_filename: str, owner_id: int):
    """
    Crea un nuevo lote en la base de datos.
    """
    # Usamos **lote.dict() para desempacar los datos del schema
    db_lote = models.Lote(
        **lote.dict(), 
        excel_filename=excel_filename, 
        owner_id=owner_id
    )
    db.add(db_lote)
    db.commit()
    db.refresh(db_lote)
    return db_lote

def update_lote(db: Session, lote_id: int, lote_update: lote_schema.LoteCreate):
    """
    Actualiza los datos de un lote existente.
    """
    db_lote = get_lote_by_id(db, lote_id)
    if db_lote:
        db_lote.name = lote_update.name
        db_lote.company_name = lote_update.company_name
        db_lote.company_nit = lote_update.company_nit
        db.commit()
        db.refresh(db_lote)
    return db_lote

def delete_lote(db: Session, lote_id: int):
    """
    Elimina un lote de la base de datos.
    """
    db_lote = get_lote_by_id(db, lote_id)
    if db_lote:
        db.delete(db_lote)
        db.commit()
    return db_lote