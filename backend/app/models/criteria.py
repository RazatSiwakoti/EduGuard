from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class Criteria(Base):
    __tablename__ = "criteria"

    id = Column(Integer, primary_key=True, index=True)

    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)

    name = Column(String, nullable=False)
    weight = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    enabled = Column(Boolean, default=True)

    unit = relationship("Unit", back_populates="criteria")