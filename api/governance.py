# API endpoints for governance and voting

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from db.connection import SessionLocal
from models.governance import GovernanceProposalModel, VoteModel, ProposalStatus
from models.identity import UserIdentityModel
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ProposalCreate(BaseModel):
    title: str
    description: str
    proposer: str
    days_until_expiry: int = 7

class ProposalOut(BaseModel):
    id: int
    title: str
    description: str
    proposer: str
    status: str
    votes_for: float
    votes_against: float
    created_at: datetime
    expires_at: datetime
    
    model_config = {"from_attributes": True}

class VoteCreate(BaseModel):
    proposal_id: int
    voter: str
    support: int  # 1 for yes, -1 for no

@router.post("/governance/proposal", response_model=ProposalOut)
def create_proposal(proposal: ProposalCreate, db: Session = Depends(get_db)):
    """
    Create a new governance proposal.
    """
    # Verify proposer exists
    identity = db.query(UserIdentityModel).filter(
        UserIdentityModel.username == proposal.proposer
    ).first()
    
    if not identity:
        raise HTTPException(status_code=404, detail="Proposer identity not found")
    
    # Create proposal
    new_proposal = GovernanceProposalModel(
        title=proposal.title,
        description=proposal.description,
        proposer=proposal.proposer,
        status=ProposalStatus.ACTIVE,
        expires_at=datetime.utcnow() + timedelta(days=proposal.days_until_expiry)
    )
    
    db.add(new_proposal)
    db.commit()
    db.refresh(new_proposal)
    
    return new_proposal

@router.get("/governance/proposals", response_model=List[ProposalOut])
def list_proposals(status: str = None, db: Session = Depends(get_db)):
    """
    List governance proposals, optionally filtered by status.
    """
    query = db.query(GovernanceProposalModel)
    
    if status:
        query = query.filter(GovernanceProposalModel.status == status)
    
    proposals = query.order_by(GovernanceProposalModel.created_at.desc()).all()
    return proposals

@router.get("/governance/proposal/{proposal_id}", response_model=ProposalOut)
def get_proposal(proposal_id: int, db: Session = Depends(get_db)):
    """
    Get a specific proposal by ID.
    """
    proposal = db.query(GovernanceProposalModel).filter(
        GovernanceProposalModel.id == proposal_id
    ).first()
    
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return proposal

@router.post("/governance/vote")
def cast_vote(vote: VoteCreate, db: Session = Depends(get_db)):
    """
    Cast a vote on a proposal (one vote per identity).
    """
    # Check if proposal exists and is active
    proposal = db.query(GovernanceProposalModel).filter(
        GovernanceProposalModel.id == vote.proposal_id
    ).first()
    
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    if proposal.status != ProposalStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Proposal is not active")
    
    if datetime.utcnow() > proposal.expires_at:
        proposal.status = ProposalStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=400, detail="Proposal has expired")
    
    # Check if voter has already voted
    existing_vote = db.query(VoteModel).filter(
        VoteModel.proposal_id == vote.proposal_id,
        VoteModel.voter == vote.voter
    ).first()
    
    if existing_vote:
        raise HTTPException(status_code=400, detail="Already voted on this proposal")
    
    # Verify voter identity exists
    identity = db.query(UserIdentityModel).filter(
        UserIdentityModel.username == vote.voter
    ).first()
    
    if not identity:
        raise HTTPException(status_code=404, detail="Voter identity not found")
    
    # Each identity counts as one vote
    vote_weight = 1.0
    
    # Record vote
    new_vote = VoteModel(
        proposal_id=vote.proposal_id,
        voter=vote.voter,
        vote_value=vote_weight,
        support=vote.support
    )
    
    db.add(new_vote)
    
    # Update proposal vote counts
    if vote.support > 0:
        proposal.votes_for += vote_weight
    else:
        proposal.votes_against += vote_weight
    
    db.commit()
    
    return {
        "proposal_id": vote.proposal_id,
        "voter": vote.voter,
        "vote_weight": vote_weight,
        "support": vote.support,
        "message": "Vote recorded successfully"
    }

@router.post("/governance/proposal/{proposal_id}/finalize")
def finalize_proposal(proposal_id: int, db: Session = Depends(get_db)):
    """
    Finalize a proposal after voting period ends.
    """
    proposal = db.query(GovernanceProposalModel).filter(
        GovernanceProposalModel.id == proposal_id
    ).first()
    
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    if proposal.status != ProposalStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Proposal is not active")
    
    # Check if voting period has ended
    if datetime.utcnow() < proposal.expires_at:
        raise HTTPException(status_code=400, detail="Voting period has not ended")
    
    # Determine outcome
    if proposal.votes_for > proposal.votes_against:
        proposal.status = ProposalStatus.PASSED
    else:
        proposal.status = ProposalStatus.REJECTED
    
    db.commit()
    
    return {
        "proposal_id": proposal_id,
        "status": proposal.status,
        "votes_for": proposal.votes_for,
        "votes_against": proposal.votes_against
    }
