from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="lecturer")  # lecturer/admin later
    is_active = Column(Boolean, default=True)

    # relationships
    units = relationship("Unit", back_populates="lecturer")
    rule_versions = relationship("RuleVersion", back_populates="creator")
   