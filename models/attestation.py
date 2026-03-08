# attestation model

from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from db.connection import Base

class AttestationModel(Base):
    __tablename__ = "attestations"

    id = Column(Integer, primary_key=True, index=True)
    issuer = Column(String, index=True)
    subject = Column(String, index=True)
    attestation_type = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    signature = Column(Text)
    anchor = Column(String)
