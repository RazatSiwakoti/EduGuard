from sqlalchemy import Column, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class RuleVersion(Base):
    __tablename__ = "rule_versions"

    id = Column(Integer, primary_key=True, index=True)

    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    version_number = Column(Integer, nullable=False)
    active = Column(Boolean, default=True)

    timestamp = Column(DateTime, server_default=func.now())

    unit = relationship("Unit", back_populates="rule_versions")
    creator = relationship("User", back_populates="rule_versions")