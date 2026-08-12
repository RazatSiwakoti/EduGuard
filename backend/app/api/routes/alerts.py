"""
Alerts & Email Notifications API

Handles:
- Email log retrieval
- Alert queue management
- Bulk alert sending
- Single alert sending
- Failed email retries
- SMTP integration
"""

import smtplib
import logging
import json
from datetime import datetime
from typing import List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.student import Student
from app.models.enums import UserRole
from app.config import settings
from app.core.dependencies import require_role

router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"],
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  MODELS
# ─────────────────────────────────────────────

class EmailLog:
    """In-memory email log (can be replaced with database model)"""
    def __init__(self, student_id: str, student_name: str, email: str, subject: str, 
                 email_type: str, template: str, status: str, sent_at: str, opened_at: str = None):
        self.id = f"{student_id}_{sent_at.replace(':', '').replace('-', '')}"
        self.student = student_name
        self.studentId = student_id
        self.subject = subject
        self.type = email_type
        self.template = template
        self.status = status
        self.sentAt = sent_at
        self.openedAt = opened_at or "—"

# In-memory storage (replace with database in production)
email_logs: List[dict] = []
sent_log: dict = {}  # Track already-sent students


# ─────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────

def load_sent_log():
    """Load tracking of already-sent alerts"""
    global sent_log
    try:
        with open("sent_log.json", "r") as f:
            sent_log = json.load(f)
    except FileNotFoundError:
        sent_log = {}


def save_sent_log():
    """Save sent log to file"""
    try:
        with open("sent_log.json", "w") as f:
            json.dump(sent_log, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save sent log: {e}")


def already_sent(student_id: int, week: int) -> bool:
    """Check if student was already notified this week"""
    key = f"{student_id}_week{week}"
    return key in sent_log


def mark_sent(student_id: int, email: str, week: int):
    """Mark student as notified"""
    key = f"{student_id}_week{week}"
    sent_log[key] = {
        "student_id": student_id,
        "email": email,
        "week": week,
        "sent_at": datetime.now().isoformat()
    }
    save_sent_log()


def build_student_email(student_name: str, subject_code: str, week: int) -> tuple[str, str]:
    """Build student alert email HTML and plain text"""
    name = student_name.strip().title()
    
    html = f"""<html><body style="font-family:Arial,sans-serif;color:#333;line-height:1.6;">
<div style="max-width:600px;margin:auto;padding:24px;">
  <div style="background:#1F4E79;padding:16px 24px;border-radius:6px 6px 0 0;">
    <h2 style="color:#fff;margin:0;">EduGuard - At-Risk Student Alert</h2>
    <p style="color:#c9d9e8;margin:4px 0 0;">Student Academic Support — Week {week} Alert</p>
  </div>
  <div style="background:#f9f9f9;padding:24px;border:1px solid #ddd;border-top:none;border-radius:0 0 6px 6px;">
    <p>Dear <strong>{name}</strong>,</p>
    <p>Our academic monitoring system has flagged you as potentially at academic risk
    in <strong>{subject_code}</strong> as of <strong>Week {week}</strong>.
    Please take action as soon as possible — early support makes a real difference.</p>
    <h3 style="color:#1F4E79;">What You Should Do Now</h3>
    <ul>
      <li>Contact your lecturer or tutor to discuss your current progress</li>
      <li>Submit any outstanding tutorials or assessments immediately</li>
      <li>Check your attendance and submission records on the student portal</li>
      <li>Visit Student Support if you are facing personal, health, or financial difficulties</li>
    </ul>
    <div style="background:#e8f4fd;padding:12px 16px;border-radius:4px;margin-top:16px;">
      <strong>Student Support Centre</strong><br>
      Email: <a href="mailto:support@eduguard.edu">support@eduguard.edu</a><br>
      Web: <a href="https://www.eduguard.edu">www.eduguard.edu</a>
    </div>
    <p style="margin-top:24px;">Warm regards,<br><strong>EduGuard Support Team</strong></p>
  </div>
  <p style="font-size:11px;color:#999;text-align:center;margin-top:12px;">
    This is an automated message. Please do not reply directly to this email.
  </p>
</div>
</body></html>"""

    plain = (
        f"Dear {name},\n\n"
        f"You have been flagged as potentially at risk in {subject_code} at Week {week}.\n\n"
        f"Please contact your lecturer or Student Support: support@eduguard.edu\n\n"
        f"EduGuard Support Team"
    )
    
    return html, plain


def send_smtp_email(to_email: str, subject: str, html: str, plain: str) -> bool:
    """Send email via SMTP"""
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"EduGuard <{settings.SMTP_USERNAME}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html, "html"))
        
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_USERNAME, to_email, msg.as_string())
        server.quit()
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


# ─────────────────────────────────────────────
#  ENDPOINTS
# ─────────────────────────────────────────────

@router.get("/logs")
def get_email_logs(db: Session = Depends(get_db)):
    """
    Fetch email notification logs
    Returns all email send history
    """
    global email_logs
    return email_logs if email_logs else []


@router.get("/queue")
def get_alert_queue(db: Session = Depends(get_db)):
    """
    Fetch pending alert queue (at-risk students not yet notified)
    Returns list of HIGH/MEDIUM risk students
    """
    try:
        # Get all at-risk students
        at_risk_students = db.query(Student).filter(
            Student.risk_status.in_(["HIGH", "MEDIUM"])
        ).all()
        
        queue = []
        for student in at_risk_students:
            # Check if already sent this week
            if not already_sent(student.id, week=4):
                queue.append({
                    "id": student.id,
                    "name": student.first_name + " " + student.last_name,
                    "initials": (student.first_name[0] + student.last_name[0]).upper(),
                    "studentId": student.student_number,
                    "email": student.email or "N/A",
                    "subject": student.program or "General",
                    "risk": student.risk_status
                })
        
        return queue
    except Exception as e:
        logger.error(f"Error fetching alert queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
def get_alert_stats(db: Session = Depends(get_db)):
    """
    Fetch alert statistics
    Returns counts of sent, opened, failed emails
    """
    global email_logs
    
    total = len(email_logs)
    opened = len([log for log in email_logs if log.get("status") == "Opened"])
    sent = len([log for log in email_logs if log.get("status") == "Sent"])
    failed = len([log for log in email_logs if log.get("status") == "Failed"])
    
    return {
        "total": total,
        "opened": opened,
        "sent": sent,
        "failed": failed
    }


@router.post("/send/{student_id}")
def send_alert_to_student(student_id: int, db: Session = Depends(get_db)):
    """
    Send alert email to a specific student
    """
    try:
        load_sent_log()
        
        # Get student
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        if not student.email:
            return {
                "success": False,
                "message": "Student has no email address on file"
            }
        
        # Check if already sent
        if already_sent(student_id, week=4):
            return {
                "success": False,
                "message": "Alert already sent to this student this week"
            }
        
        # Build and send email
        subject_code = student.program or "your enrolled subject"
        html, plain = build_student_email(
            f"{student.first_name} {student.last_name}",
            subject_code,
            week=4
        )
        subject = f"[EduGuard] Academic Alert – {subject_code} Week 4"
        
        if send_smtp_email(student.email, subject, html, plain):
            mark_sent(student_id, student.email, week=4)
            
            # Log email
            global email_logs
            email_logs.append({
                "id": f"email_{len(email_logs)}",
                "student": f"{student.first_name} {student.last_name}",
                "studentId": student.student_number,
                "subject": subject_code,
                "type": "Risk Alert",
                "template": "at_risk_alert_week4",
                "status": "Sent",
                "sentAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "openedAt": "—"
            })
            
            return {
                "success": True,
                "message": f"Alert sent to {student.email}"
            }
        else:
            return {
                "success": False,
                "message": "Failed to send email"
            }
    
    except Exception as e:
        logger.error(f"Error sending alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-bulk")
def send_bulk_alerts(payload: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Send bulk alerts to all pending at-risk students
    Runs in background
    """
    week = payload.get("week", 4)
    load_sent_log()
    
    try:
        # Get at-risk students
        at_risk_students = db.query(Student).filter(
            Student.risk_status.in_(["HIGH", "MEDIUM"])
        ).all()
        
        sent_count = 0
        failed_count = 0
        skipped_count = 0
        
        global email_logs
        
        for student in at_risk_students:
            if not student.email:
                continue
            
            # Check if already sent
            if already_sent(student.id, week):
                skipped_count += 1
                continue
            
            # Build email
            subject_code = student.program or "your enrolled subject"
            html, plain = build_student_email(
                f"{student.first_name} {student.last_name}",
                subject_code,
                week
            )
            subject = f"[EduGuard] Academic Alert – {subject_code} Week {week}"
            
            # Send
            if send_smtp_email(student.email, subject, html, plain):
                mark_sent(student.id, student.email, week)
                sent_count += 1
                
                # Log
                email_logs.append({
                    "id": f"email_{len(email_logs)}",
                    "student": f"{student.first_name} {student.last_name}",
                    "studentId": student.student_number,
                    "subject": subject_code,
                    "type": "Bulk Risk Alert",
                    "template": f"at_risk_alert_week{week}",
                    "status": "Sent",
                    "sentAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "openedAt": "—"
                })
            else:
                failed_count += 1
                
                # Log failure
                email_logs.append({
                    "id": f"email_{len(email_logs)}",
                    "student": f"{student.first_name} {student.last_name}",
                    "studentId": student.student_number,
                    "subject": subject_code,
                    "type": "Bulk Risk Alert",
                    "template": f"at_risk_alert_week{week}",
                    "status": "Failed",
                    "sentAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "openedAt": "—"
                })
        
        return {
            "success": True,
            "message": f"Bulk alerts sent. {sent_count} sent, {failed_count} failed, {skipped_count} skipped",
            "sent_count": sent_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count
        }
    
    except Exception as e:
        logger.error(f"Error sending bulk alerts: {e}")
        return {
            "success": False,
            "message": str(e),
            "sent_count": 0,
            "failed_count": 0,
            "skipped_count": 0
        }


@router.post("/retry-failed")
def retry_failed_alerts(db: Session = Depends(get_db)):
    """
    Retry sending failed alerts
    """
    global email_logs
    
    try:
        failed_logs = [log for log in email_logs if log.get("status") == "Failed"]
        
        if not failed_logs:
            return {
                "success": True,
                "message": "No failed alerts to retry",
                "sent_count": 0,
                "failed_count": 0,
                "skipped_count": 0
            }
        
        sent_count = 0
        failed_count = 0
        
        for log in failed_logs:
            student_id = int(log.get("studentId", 0))
            
            # Get student
            student = db.query(Student).filter(Student.id == student_id).first()
            if not student or not student.email:
                continue
            
            # Retry send
            subject_code = student.program or "your enrolled subject"
            html, plain = build_student_email(
                f"{student.first_name} {student.last_name}",
                subject_code,
                week=4
            )
            subject = f"[EduGuard] Academic Alert – {subject_code} Week 4 (Retry)"
            
            if send_smtp_email(student.email, subject, html, plain):
                log["status"] = "Sent"
                sent_count += 1
            else:
                failed_count += 1
        
        return {
            "success": True,
            "message": f"Retry complete. {sent_count} sent, {failed_count} still failed",
            "sent_count": sent_count,
            "failed_count": failed_count,
            "skipped_count": 0
        }
    
    except Exception as e:
        logger.error(f"Error retrying failed alerts: {e}")
        return {
            "success": False,
            "message": str(e),
            "sent_count": 0,
            "failed_count": 0,
            "skipped_count": 0
        }
