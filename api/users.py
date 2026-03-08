from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.connection import SessionLocal
from models.attestation import AttestationModel
from models.user import UserAttestations, AttestationOut

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/user/{username}", response_model=UserAttestations)
def get_user_attestations(username: str, db: Session = Depends(get_db)):
    rows = (
        db.query(AttestationModel)
        .filter(AttestationModel.subject == username)
        .all()
    )

    if not rows:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        attestation_list = [AttestationOut.model_validate(r) for r in rows]
    except Exception:
        raise HTTPException(status_code=500, detail="Error serializing attestations")

    return UserAttestations(
        user=username,
        attestations=attestation_list,
    )
