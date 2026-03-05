from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    pdf_url = Column(String, nullable=False, unique=True)
    source_page_url = Column(String, nullable=False)
    discovered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    downloads = relationship("Download", back_populates="policy")
    structured_policies = relationship("StructuredPolicy", back_populates="policy")


class Download(Base):
    __tablename__ = "downloads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=False)
    stored_location = Column(String, nullable=True)
    downloaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    http_status = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)

    policy = relationship("Policy", back_populates="downloads")


class StructuredPolicy(Base):
    __tablename__ = "structured_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=False)
    extracted_text = Column(Text, nullable=True)
    structured_json = Column(JSON, nullable=True)
    structured_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    llm_metadata = Column(JSON, nullable=True)
    validation_error = Column(Text, nullable=True)

    policy = relationship("Policy", back_populates="structured_policies")
