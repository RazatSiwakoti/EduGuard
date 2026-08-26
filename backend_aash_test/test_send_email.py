"""
Interactive / CLI Email Testing Script for EduGuard
Run with:
    python test_send_email.py
or:
    python test_send_email.py --to your_email@example.com
"""

import sys
import os
import argparse
from datetime import datetime

# Configure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure backend_aash_test directory is in python path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import settings, get_current_time
from email_service import EmailService
from database import SessionLocal
from models import Student, EmailLog


def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def show_config():
    print_header("EduGuard Email Configuration")
    print(f"• SMTP_HOST:     {settings.SMTP_HOST}")
    print(f"• SMTP_PORT:     {settings.SMTP_PORT}")
    print(f"• SMTP_USERNAME: {settings.SMTP_USERNAME or '(Not configured - DEV simulation mode)'}")
    print(f"• SMTP_PASSWORD: {'*' * len(settings.SMTP_PASSWORD) if settings.SMTP_PASSWORD else '(Not configured)'}")
    print(f"• EMAIL_FROM:    {settings.EMAIL_FROM}")
    print(f"• Database URL:  {settings.DATABASE_URL}")

    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        print("\n💡 NOTE: SMTP credentials are not set in .env.")
        print("   Emails will be logged in simulated test mode without sending over the network.")
        print("   To send real emails, create/edit backend_aash_test/.env with:")
        print("     SMTP_USERNAME=your_email@gmail.com")
        print("     SMTP_PASSWORD=your_app_password")
    else:
        print("\n🔍 Testing SMTP authentication...")
        ok, msg = EmailService.verify_smtp_connection()
        if ok:
            print(f"  ✅ {msg}")
        else:
            print(f"  ❌ {msg}")


def send_direct_test_email(to_email: str, student_name: str = "Test Student", subject_code: str = "ICT724", week: int = 4):
    print_header(f"Sending Test Alert to: {to_email}")
    print(f"• Student: {student_name}")
    print(f"• Subject: {subject_code}")
    print(f"• Week:    {week}")

    db = SessionLocal()
    try:
        student = db.query(Student).filter(Student.email == to_email).first()
        student_id = student.id if student else 0

        email_log = EmailLog(
            student_id=student_id,
            student_name=student_name,
            email=to_email,
            subject=subject_code,
            email_type="Direct Test Alert",
            template=f"at_risk_alert_week{week}",
            status="Pending",
            week=week,
            sent_at=get_current_time()
        )
        db.add(email_log)
        db.flush()

        success, error_msg = EmailService.send_student_alert(
            student_email=to_email,
            student_name=student_name,
            subject_code=subject_code,
            week=week,
            log_id=email_log.id
        )

        if success:
            email_log.status = "Sent"
            email_log.sent_at = get_current_time()
            email_log.error_message = None
            if student:
                student.last_alert_sent = get_current_time()
                student.alert_count = (student.alert_count or 0) + 1
            print(f"\n🎉 Email dispatch process completed successfully! (Log ID: #{email_log.id})")
        else:
            email_log.status = "Failed"
            email_log.error_message = error_msg or "SMTP delivery failed"
            print(f"\n⚠️ Email dispatch failed: {error_msg}")

        db.commit()
    finally:
        db.close()


def send_alert_for_student_in_db(student_id: int):
    print_header(f"Sending Alert for Database Student ID: {student_id}")
    db = SessionLocal()
    try:
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            print(f"❌ Student with ID {student_id} not found in database.")
            return

        print(f"• Found: {student.full_name} ({student.student_number})")
        print(f"• Email: {student.email}")
        print(f"• Risk:  {student.risk_status}")
        print(f"• Course: {student.program}")

        if not student.email:
            print("❌ Student has no email address on file.")
            return

        week = settings.CHECKPOINT_WEEK
        
        # Pre-create log to get log_id for acknowledgment button
        email_log = EmailLog(
            student_id=student.id,
            student_name=student.full_name,
            email=student.email,
            subject=student.program or "General",
            email_type="Individual Alert",
            template=f"at_risk_alert_week{week}",
            status="Pending",
            week=week,
            sent_at=get_current_time()
        )
        db.add(email_log)
        db.flush()

        success, error_msg = EmailService.send_student_alert(
            student_email=student.email,
            student_name=student.full_name,
            subject_code=student.program or "General",
            week=week,
            log_id=email_log.id
        )

        if success:
            email_log.status = "Sent"
            email_log.sent_at = get_current_time()
            email_log.error_message = None
            student.last_alert_sent = get_current_time()
            student.alert_count = (student.alert_count or 0) + 1
            print(f"\n✅ Success: Alert sent & recorded in database (Log ID: #{email_log.id}).")
        else:
            email_log.status = "Failed"
            email_log.error_message = error_msg or "SMTP error"
            print(f"\n❌ Failed to send: {error_msg}")

        db.commit()
    finally:
        db.close()


def show_recent_logs(limit: int = 10):
    print_header(f"Recent Email Logs (Last {limit})")
    db = SessionLocal()
    try:
        logs = db.query(EmailLog).order_by(EmailLog.created_at.desc()).limit(limit).all()
        if not logs:
            print("No email logs found in database.")
            return

        print(f"{'ID':<4} {'Student':<18} {'Email':<28} {'Status':<14} {'Sent At':<17} {'Acknowledged At'}")
        print("-" * 96)
        for log in logs:
            sent_str = log.sent_at.strftime("%Y-%m-%d %H:%M") if log.sent_at else "-"
            ack_str = log.acknowledged_at.strftime("%Y-%m-%d %H:%M") if log.acknowledged_at else "-"
            status_display = log.status
            if log.error_message:
                status_display += f" ({log.error_message[:15]}...)"
            print(f"{log.id:<4} {log.student_name[:17]:<18} {log.email[:27]:<28} {status_display[:14]:<14} {sent_str:<17} {ack_str}")
    finally:
        db.close()


def list_at_risk_students():
    print_header("At-Risk Students in Database")
    db = SessionLocal()
    try:
        students = db.query(Student).filter(
            Student.risk_status.in_(["HIGH", "MEDIUM"]),
            Student.is_active == True
        ).all()

        if not students:
            print("No at-risk students found.")
            return

        print(f"{'ID':<4} {'Number':<10} {'Name':<22} {'Email':<30} {'Risk':<8} {'Program'}")
        print("-" * 85)
        for s in students:
            print(f"{s.id:<4} {s.student_number:<10} {s.full_name[:21]:<22} {str(s.email or ''):<30} {s.risk_status:<8} {s.program or ''}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EduGuard Email Testing Utility")
    parser.add_argument("--to", type=str, help="Destination email address to send a test alert to")
    parser.add_argument("--name", type=str, default="Student Name", help="Student name for test template")
    parser.add_argument("--subject", type=str, default="ICT724", help="Subject / course code")
    parser.add_argument("--week", type=int, default=4, help="Week number (e.g. 4)")
    parser.add_argument("--student-id", type=int, help="Send alert for a specific student ID in the DB")
    parser.add_argument("--list-students", action="store_true", help="List all at-risk students in DB")
    parser.add_argument("--logs", action="store_true", help="Display recent email logs")
    parser.add_argument("--config", action="store_true", help="Display email configuration")

    args = parser.parse_args()

    # If specific flags are given, run them
    if args.config:
        show_config()
    elif args.list_students:
        list_at_risk_students()
    elif args.logs:
        show_recent_logs()
    elif args.student_id:
        send_alert_for_student_in_db(args.student_id)
    elif args.to:
        send_direct_test_email(args.to, args.name, args.subject, args.week)
    else:
        # Default behavior: Show status, config, list students, and prompt
        show_config()
        list_at_risk_students()
        print("\n" + "=" * 60)
        print("  Quick Test Options:")
        print("=" * 60)
        print("1. Send a direct test alert to an email address:")
        print("   python test_send_email.py --to your_email@example.com --name \"Your Name\"")
        print("\n2. Send an alert to Student ID 1 from database:")
        print("   python test_send_email.py --student-id 1")
        print("\n3. View email logs:")
        print("   python test_send_email.py --logs")
        print("=" * 60)
