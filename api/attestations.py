# endpoints for attestations

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session
from db.connection import SessionLocal
from models.attestation import AttestationModel
from models.user import AttestationOut, AttestationIn
from utils.crypto import sign_attestation, verify_signature

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/attest", response_model=AttestationOut)
def create_attestation(att: AttestationIn, db: Session = Depends(get_db)):
    db_att = AttestationModel(
        issuer=att.issuer,
        subject=att.subject,
        attestation_type=att.attestation_type,
        signature=att.signature,
        anchor=att.anchor
    )
    db.add(db_att)
    db.commit()
    db.refresh(db_att)
    return db_att

