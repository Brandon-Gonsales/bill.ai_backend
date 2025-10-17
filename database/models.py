from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

# Importamos la Base declarativa desde la configuración de la DB
from database.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    # Rol del usuario, por simplicidad: "user" o "admin"
    role = Column(String, nullable=False, default="user")

    # Relación con lotes
    lotes = relationship("Lote", back_populates="owner", cascade="all, delete-orphan")


class Lote(Base):
    __tablename__ = "lotes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    company_nit = Column(String, nullable=False)
    excel_filename = Column(String, nullable=False)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    owner = relationship("User", back_populates="lotes")


