# API endpoints for privacy features and zero-knowledge proofs

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.connection import SessionLocal
from models.identity import UserIdentityModel
from models.attestation import AttestationModel
from models.user import ZKProof
from utils.zkproof import generate_zk_proof, verify_zk_proof, create_selective_disclosure_proof
from pydantic import BaseModel
from typing import List

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ThresholdProofRequest(BaseModel):
    username: str
    threshold: int

class SelectiveDisclosureRequest(BaseModel):
    username: str
    selected_indices: List[int]

@router.post("/privacy/prove-threshold", response_model=ZKProof)
def prove_attestation_threshold(request: ThresholdProofRequest, db: Session = Depends(get_db)):
    """
    Generate a zero-knowledge proof that a user's attestation count meets a threshold.
    Does not reveal the exact number of attestations.
    """
    # Verify user exists
    identity = db.query(UserIdentityModel).filter(
        UserIdentityModel.username == request.username
    ).first()
    
    if not identity:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Count attestations for this user
    attestation_count = db.query(AttestationModel).filter(
        AttestationModel.subject == request.username
    ).count()
    
    # Generate ZK proof
    proof_string, meets_threshold = generate_zk_proof(
        attestation_count,
        request.threshold
    )
    
    return ZKProof(
        proof=proof_string,
        threshold=request.threshold,
        verified=meets_threshold
    )

@router.post("/privacy/verify-threshold")
def verify_attestation_threshold(proof_data: ZKProof):
    """
    Verify a zero-knowledge proof without learning the actual attestation count.
    """
    is_valid = verify_zk_proof(
        proof_data.proof,
        proof_data.threshold,
        proof_data.verified
    )
    
    return {
        "valid": is_valid,
        "threshold": proof_data.threshold,
        "meets_threshold": proof_data.verified if is_valid else None
    }

@router.post("/privacy/selective-disclosure")
def create_selective_disclosure(request: SelectiveDisclosureRequest, db: Session = Depends(get_db)):
    """
    Create a selective disclosure proof for specific attestations.
    Allows proving certain attestations exist without revealing all.
    """
    # Get all user attestations
    attestations = db.query(AttestationModel).filter(
        AttestationModel.subject == request.username
    ).all()
    
    if not attestations:
        raise HTTPException(status_code=404, detail="No attestations found")
    
    # Convert to list of dicts
    attestation_list = []
    for att in attestations:
        attestation_list.append({
            "id": att.id,
            "issuer": att.issuer,
            "subject": att.subject,
            "attestation_type": att.attestation_type,
            "timestamp": str(att.timestamp)
        })
    
    # Validate selected indices
    if any(i < 0 or i >= len(attestation_list) for i in request.selected_indices):
        raise HTTPException(status_code=400, detail="Invalid attestation indices")
    
    # Create selective disclosure proof
    disclosure_proof = create_selective_disclosure_proof(
        attestation_list,
        request.selected_indices
    )
    
    return {
        "username": request.username,
        "proof": disclosure_proof,
        "message": "Selective disclosure proof created"
    }
