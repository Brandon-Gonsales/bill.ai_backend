from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# 1. Definimos la ubicación de nuestra base de datos.
DATABASE_URL = "sqlite:///./facturas.db"

# 2. Creamos el "motor" de la base de datos.
#    Esta es la variable que tu main.py está buscando.
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3. Creamos una "sesión" para hablar con la base de datos.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Creamos una clase Base de la cual heredarán todos nuestros modelos.
Base = declarative_base()