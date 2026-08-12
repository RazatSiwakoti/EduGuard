"""
Alerts API Routes
Endpoints for email notifications and alert management
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from database import get_db
from models import Student, EmailLog
from email_service import EmailService
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["Alerts"])

# In-memory tracking of sent alerts
sent_alerts = {}  # {"student_id_week": timestamp}


# ─────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────

def already_sent(student_id: int, week: int) -> bool:
    """Check if alert already sent to student this week"""
    key = f"{student_id}_week{week}"
    return key in sent_alerts


def mark_sent(student_id: int, week: int):
    """Mark alert as sent for this student"""
    key = f"{student_id}_week{week}"
    sent_alerts[key] = datetime.utcnow()


# ─────────────────────────────────────────────
#  ENDPOINTS
# ─────────────────────────────────────────────

@router.get("/logs")
def get_email_logs(db: Session = Depends(get_db)):
    """Fetch all email logs"""
    try:
        logs = db.query(EmailLog).order_by(EmailLog.created_at.desc()).all()
        
        return [
            {
                "id": str(log.id),
                "student": log.student_name,
                "studentId": f"ID_{log.student_id}",
                "subject": log.subject,
                "type": log.email_type,
                "template": log.template,
                "status": log.status,
                "sentAt": log.sent_at.strftime("%Y-%m-%d %H:%M"),
                "openedAt": log.opened_at.strftime("%Y-%m-%d %H:%M") if log.opened_at else "—"
            }
            for log in logs
        ]
    except Exception as e:
        logger.error(f"Error fetching email logs: {e}")
        return []


@router.get("/queue")
def get_alert_queue(db: Session = Depends(get_db)):
    """Fetch pending alert queue (HIGH/MEDIUM risk students)"""
    try:
        # Get at-risk students
        at_risk_students = db.query(Student).filter(
            Student.risk_status.in_(["HIGH", "MEDIUM"]),
            Student.is_active == True
        ).all()
        
        queue = []
        week = settings.CHECKPOINT_WEEK
        
        for student in at_risk_students:
            if not student.email:
                continue
            
            # Skip if already sent this week
            if already_sent(student.id, week):
                continue
            
            queue.append({
                "id": student.id,
                "name": student.full_name,
                "initials": student.initials,
                "studentId": student.student_number,
                "email": student.email,
                "subject": student.program or "General",
                "risk": student.risk_status
            })
        
        logger.info(f"Alert queue: {len(queue)} students pending")
        return queue
        
    except Exception as e:
        logger.error(f"Error fetching alert queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
def get_alert_stats(db: Session = Depends(get_db)):
    """Fetch alert statistics"""
    try:
        total = db.query(EmailLog).count()
        opened = db.query(EmailLog).filter(EmailLog.status == "Opened").count()
        sent = db.query(EmailLog).filter(EmailLog.status == "Sent").count()
        failed = db.query(EmailLog).filter(EmailLog.status == "Failed").count()
        
        return {
            "total": total,
            "opened": opened,
            "sent": sent,
            "failed": failed
        }
    except Exception as e:
        logger.error(f"Error fetching alert stats: {e}")
        return {"total": 0, "opened": 0, "sent": 0, "failed": 0}


@router.post("/send/{student_id}")
def send_alert_to_student(student_id: int, db: Session = Depends(get_db)):
    """Send alert email to specific student"""
    try:
        week = settings.CHECKPOINT_WEEK
        
        # Get student
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        if not student.email:
            return {"success": False, "message": "Student has no email on file"}
        
        # Check if already sent
        if already_sent(student_id, week):
            return {"success": False, "message": "Alert already sent this week"}
        
        # Send email
        success = EmailService.send_student_alert(
            student.email,
            student.full_name,
            student.program or "General",
            week
        )
        
        if success:
            # Mark as sent
            mark_sent(student_id, week)
            
            # Log in database
            email_log = EmailLog(
                student_id=student_id,
                student_name=student.full_name,
                email=student.email,
                subject=student.program or "General",
                email_type="Individual Alert",
                template=f"at_risk_alert_week{week}",
                status="Sent",
                week=week
            )
            db.add(email_log)
            
            # Update student
            student.last_alert_sent = datetime.utcnow()
            student.alert_count += 1
            
            db.commit()
            logger.info(f"✅ Alert sent to {student.full_name} ({student.email})")
            
            return {"success": True, "message": f"Alert sent to {student.email}"}
        else:
            # Log failure
            email_log = EmailLog(
                student_id=student_id,
                student_name=student.full_name,
                email=student.email,
                subject=student.program or "General",
                email_type="Individual Alert",
                template=f"at_risk_alert_week{week}",
                status="Failed",
                week=week,
                error_message="SMTP send failed"
            )
            db.add(email_log)
            db.commit()
            
            logger.error(f"❌ Failed to send alert to {student.full_name}")
            return {"success": False, "message": "Failed to send email"}
    
    except Exception as e:
        logger.error(f"Error sending alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-bulk")
def send_bulk_alerts(payload: dict, db: Session = Depends(get_db)):
    """Send bulk alerts to all pending at-risk students"""
    try:
        week = payload.get("week", settings.CHECKPOINT_WEEK)
        logger.info(f"📧 Starting bulk alert send for week {week}")
        
        # Get at-risk students
        at_risk_students = db.query(Student).filter(
            Student.risk_status.in_(["HIGH", "MEDIUM"]),
            Student.is_active == True
        ).all()
        
        sent_count = 0
        failed_count = 0
        skipped_count = 0
        
        for student in at_risk_students:
            if not student.email:
                continue
            
            # Skip if already sent
            if already_sent(student.id, week):
                skipped_count += 1
                continue
            
            # Send email
            success = EmailService.send_student_alert(
                student.email,
                student.full_name,
                student.program or "General",
                week
            )
            
            if success:
                # Mark as sent
                mark_sent(student.id, week)
                sent_count += 1
                
                # Log
                email_log = EmailLog(
                    student_id=student.id,
                    student_name=student.full_name,
                    email=student.email,
                    subject=student.program or "General",
                    email_type="Bulk Alert",
                    template=f"at_risk_alert_week{week}",
                    status="Sent",
                    week=week
                )
                
                # Update student
                student.last_alert_sent = datetime.utcnow()
                student.alert_count += 1
            else:
                failed_count += 1
                
                # Log failure
                email_log = EmailLog(
                    student_id=student.id,
                    student_name=student.full_name,
                    email=student.email,
                    subject=student.program or "General",
                    email_type="Bulk Alert",
                    template=f"at_risk_alert_week{week}",
                    status="Failed",
                    week=week,
                    error_message="SMTP send failed"
                )
            
            db.add(email_log)
        
        db.commit()
        logger.info(f"✅ Bulk send complete: {sent_count} sent, {failed_count} failed, {skipped_count} skipped")
        
        return {
            "success": True,
            "message": f"Bulk alerts processed. {sent_count} sent, {failed_count} failed, {skipped_count} skipped",
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
    """Retry sending failed alerts"""
    try:
        logger.info("🔄 Starting retry of failed alerts")
        
        # Get failed logs
        failed_logs = db.query(EmailLog).filter(
            EmailLog.status == "Failed",
            EmailLog.retry_count < 3
        ).all()
        
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
            # Get student
            student = db.query(Student).filter(Student.id == log.student_id).first()
            if not student or not student.email:
                continue
            
            # Retry send
            success = EmailService.send_student_alert(
                student.email,
                student.full_name,
                student.program or "General",
                log.week or settings.CHECKPOINT_WEEK
            )
            
            if success:
                log.status = "Sent"
                log.sent_at = datetime.utcnow()
                sent_count += 1
                logger.info(f"✅ Retry successful for {student.full_name}")
            else:
                log.retry_count += 1
                failed_count += 1
                logger.warning(f"⚠️ Retry failed for {student.full_name}")
        
        db.commit()
        logger.info(f"Retry complete: {sent_count} sent, {failed_count} still failed")
        
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
