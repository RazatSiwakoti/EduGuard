"""
Student Model
Represents student records with risk assessment data
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Student(Base):
    """
    Student model for EduGuard system
    Stores student information, academic metrics, and risk assessment
    """
    __tablename__ = "students"

    # Primary identifiers
    id = Column(Integer, primary_key=True, index=True)
    student_number = Column(String(50), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    
    # Contact information
    email = Column(String(255), unique=True, index=True, nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Demographics
    age = Column(Integer, nullable=True)
    gender = Column(String(50), nullable=True)
    
    # Academic information
    program = Column(String(255), nullable=True)  # e.g., "ICT724", "ICT726"
    enrollment_date = Column(DateTime, default=datetime.utcnow)
    
    # Academic metrics
    attendance_rate = Column(Float, default=0.0)  # 0-100%
    gpa = Column(Float, nullable=True)
    assignments_completed = Column(Integer, default=0)
    assignments_total = Column(Integer, default=0)
    
    # Risk assessment (from ML model)
    ml_score = Column(Float, default=0.0)  # Raw ML prediction score (0-1)
    risk_status = Column(String(20), default="LOW")  # HIGH, MEDIUM, LOW
    confidence_score = Column(Float, default=0.0)  # Confidence of prediction
    risk_trend = Column(String(50), default="STABLE")  # IMPROVING, STABLE, DECLINING
    
    # Email tracking
    is_emailed = Column(Boolean, default=False)
    last_alert_sent = Column(DateTime, nullable=True)
    alert_count = Column(Integer, default=0)  # Number of alerts sent
    
    # Status
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Student {self.student_number}: {self.first_name} {self.last_name} - {self.risk_status}>"

    @property
    def full_name(self):
        """Return full name"""
        return f"{self.first_name} {self.last_name}"

    @property
    def initials(self):
        """Return name initials"""
        return f"{self.first_name[0]}{self.last_name[0]}".upper()

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "student_number": self.student_number,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "program": self.program,
            "attendance_rate": self.attendance_rate,
            "gpa": self.gpa,
            "assignments_completed": self.assignments_completed,
            "assignments_total": self.assignments_total,
            "ml_score": self.ml_score,
            "risk_status": self.risk_status,
            "confidence_score": self.confidence_score,
            "risk_trend": self.risk_trend,
            "is_emailed": self.is_emailed,
            "last_alert_sent": self.last_alert_sent,
            "alert_count": self.alert_count,
            "is_active": self.is_active,
        }
