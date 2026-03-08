# Third-party attestation model for bootstrapping trust

from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime
from db.connection import Base

class ThirdPartyAttestationModel(Base):
    __tablename__ = "third_party_attestations"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    platform = Column(String, index=True)  # e.g., "github", "ebay", "linkedin"
    platform_username = Column(String)
    attestation_type = Column(String)  # e.g., "commits", "reviews", "transactions"
    value = Column(Float)
    attestation_metadata = Column(Text)  # JSON metadata about the attestation (renamed from 'metadata')
    verified = Column(Integer, default=0)  # 0 = pending, 1 = verified, -1 = rejected
    timestamp = Column(DateTime, default=datetime.utcnow)
