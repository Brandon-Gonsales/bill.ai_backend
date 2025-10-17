from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from database.database import SessionLocal
from database import crud
from schemas import lote as lote_schema

router = APIRouter(tags=["Lotes"], prefix="/lotes")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[lote_schema.Lote])
def list_lotes(owner_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_lotes_by_owner(db, owner_id=owner_id, skip=skip, limit=limit)


@router.get("/{lote_id}", response_model=lote_schema.Lote)
def get_lote(lote_id: int, db: Session = Depends(get_db)):
    lote = crud.get_lote_by_id(db, lote_id)
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return lote


@router.post("/", response_model=lote_schema.Lote)
def create_lote(
    data: lote_schema.LoteCreate,
    owner_id: int,
    file: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db)
):
    # Guardado simple del nombre del archivo si se proporciona; la carga real se puede añadir luego
    excel_filename = file.filename if file else ""
    return crud.create_lote(db, lote=data, excel_filename=excel_filename, owner_id=owner_id)


@router.put("/{lote_id}", response_model=lote_schema.Lote)
def update_lote(lote_id: int, data: lote_schema.LoteCreate, db: Session = Depends(get_db)):
    lote = crud.update_lote(db, lote_id=lote_id, lote_update=data)
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return lote


@router.delete("/{lote_id}")
def delete_lote(lote_id: int, db: Session = Depends(get_db)):
    lote = crud.delete_lote(db, lote_id=lote_id)
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return {"deleted": True, "lote_id": lote_id}


