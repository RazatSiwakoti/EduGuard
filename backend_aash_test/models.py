"""
Database Models
Defines Student and other entities
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from datetime import datetime
from database import Base


class Student(Base):
    """Student model for EduGuard system"""
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
    program = Column(String(255), nullable=True)  # e.g., "ICT724"
    enrollment_date = Column(DateTime, default=datetime.utcnow)
    
    # Academic metrics
    attendance_rate = Column(Float, default=0.0)  # 0-100%
    gpa = Column(Float, nullable=True)
    assignments_completed = Column(Integer, default=0)
    assignments_total = Column(Integer, default=0)
    
    # Risk assessment (from ML model)
    ml_score = Column(Float, default=0.0)  # Raw ML prediction (0-1)
    risk_status = Column(String(20), default="LOW")  # HIGH, MEDIUM, LOW
    confidence_score = Column(Float, default=0.0)  # Confidence of prediction (0-1)
    risk_trend = Column(String(50), default="STABLE")  # IMPROVING, STABLE, DECLINING
    
    # Email tracking
    is_emailed = Column(Boolean, default=False)
    last_alert_sent = Column(DateTime, nullable=True)
    alert_count = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Student {self.student_number}: {self.first_name} {self.last_name} - {self.risk_status}>"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def initials(self):
        return f"{self.first_name[0]}{self.last_name[0]}".upper()


class EmailLog(Base):
    """Email notification log"""
    __tablename__ = "email_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, nullable=False, index=True)
    student_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    email_type = Column(String(50), nullable=False)  # "Risk Alert", "Bulk Alert", etc.
    template = Column(String(100), nullable=False)  # "at_risk_alert_week4", etc.
    status = Column(String(20), default="Pending")  # "Sent", "Failed", "Opened", "Pending"
    sent_at = Column(DateTime, default=datetime.utcnow)
    opened_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    week = Column(Integer, nullable=True)  # Which week was this sent
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<EmailLog {self.student_id}: {self.status}>"
