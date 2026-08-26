"""
Alerts API Routes
Endpoints for email notifications, student acknowledgment, and alert management
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from database import get_db
from models import Student, EmailLog
from email_service import EmailService
from config import settings, get_current_time

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
    sent_alerts[key] = get_current_time()


# ─────────────────────────────────────────────
#  ENDPOINTS
# ─────────────────────────────────────────────

@router.get("/acknowledge", response_class=HTMLResponse)
def acknowledge_latest_alert(db: Session = Depends(get_db)):
    """Fallback acknowledgment endpoint when no log_id is in URL"""
    latest_log = db.query(EmailLog).order_by(EmailLog.id.desc()).first()
    if latest_log:
        return acknowledge_alert(latest_log.id, db)
    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html>
        <body style="font-family:Arial,sans-serif;text-align:center;padding:50px;background:#f9fafb;">
            <div style="max-width:500px;margin:auto;background:white;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color:#059669;">Notice Acknowledged</h2>
                <p>Thank you for acknowledging your academic alert notice.</p>
                <a href="http://localhost:5173/alerts" style="display:inline-block;margin-top:15px;background:#185FA5;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;">Open EduGuard Portal</a>
            </div>
        </body>
        </html>
        """,
        status_code=200
    )


@router.post("/support-message")
def submit_student_support_message(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Handle student query/message submission directly from the acknowledgment portal"""
    log_id = payload.get("log_id")
    message = payload.get("message", "").strip()
    reason = payload.get("reason", "General Support Inquiry")
    
    logger.info(f"📩 Student Support Message received for Alert #{log_id} | Category: {reason} | Message: {message}")
    
    return {
        "success": True,
        "reference_id": f"SR-{log_id or '00'}-{int(datetime.utcnow().timestamp()) % 10000}",
        "message": "Your inquiry has been logged and forwarded to your Academic Advisor and Student Support Centre."
    }


@router.get("/acknowledge/{log_id}", response_class=HTMLResponse)
def acknowledge_alert(log_id: int, db: Session = Depends(get_db)):
    """Student Acknowledgment endpoint with rich interactive support tools and receipt view"""
    try:
        log = db.query(EmailLog).filter(EmailLog.id == log_id).first()
        if not log:
            return HTMLResponse(
                content="""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>EduGuard - Record Not Found</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f9fafb; text-align: center; padding: 40px 20px; }
                        .card { max-width: 500px; margin: auto; background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
                        .btn { display: inline-block; background: #185FA5; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; margin-top: 15px; }
                    </style>
                </head>
                <body>
                    <div class="card">
                        <h2 style="color:#e24b4a;margin-top:0;">Notice Record Not Found</h2>
                        <p style="color:#6b7280;">This alert reference may be inactive or expired. Please visit the EduGuard dashboard or contact Student Support.</p>
                        <a href="http://localhost:5173/alerts" class="btn">Open EduGuard Portal</a>
                    </div>
                </body>
                </html>
                """,
                status_code=404
            )

        now = get_current_time()
        was_already_acknowledged = (log.status == "Acknowledged")
        
        if not was_already_acknowledged:
            log.status = "Acknowledged"
            log.acknowledged_at = now
            db.commit()
            logger.info(f"✅ Alert #{log_id} acknowledged by {log.student_name} ({log.email})")

        formatted_time = log.acknowledged_at.strftime("%A, %d %B %Y at %I:%M %p (AEST)") if log.acknowledged_at else now.strftime("%A, %d %B %Y at %I:%M %p (AEST)")

        # Webmail direct compose URLs
        gmail_compose = f"https://mail.google.com/mail/?view=cm&fs=1&to=support@eduguard.com&su=Academic%20Alert%20Inquiry%20-%20Ref%20%23{log.id}&body=Hello%20Student%20Support%2C%0A%0AMy%20name%20is%20{log.student_name}%20and%20I%20received%20an%20academic%20alert%20for%20{log.subject}%20(Alert%20Ref%20%23{log.id}).%0A%0AMy%20inquiry%3A%0A"
        outlook_compose = f"https://outlook.office.com/mail/deeplink/compose?to=support@eduguard.com&subject=Academic%20Alert%20Inquiry%20-%20Ref%20%23{log.id}&body=Hello%20Student%20Support%2C%0A%0AMy%20name%20is%20{log.student_name}%20and%20I%20received%20an%20academic%20alert%20for%20{log.subject}%20(Alert%20Ref%20%23{log.id}).%0A"

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>EduGuard - Academic Alert Acknowledged</title>
            <style>
                * {{ box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    background-color: #F3F4F6;
                    color: #1F2937;
                    margin: 0;
                    padding: 30px 15px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }}
                .card {{
                    background: #FFFFFF;
                    max-width: 620px;
                    width: 100%;
                    border-radius: 14px;
                    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
                    overflow: hidden;
                    border: 1px solid #E5E7EB;
                }}
                .header {{
                    background: linear-gradient(135deg, #1F4E79, #185FA5);
                    padding: 24px 30px;
                    color: #FFFFFF;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 20px;
                    font-weight: 700;
                }}
                .header p {{
                    margin: 4px 0 0;
                    color: #D1E4F5;
                    font-size: 13px;
                }}
                .ref-badge {{
                    background: rgba(255, 255, 255, 0.18);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    padding: 5px 12px;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 600;
                    color: #fff;
                    white-space: nowrap;
                }}
                .body {{
                    padding: 28px 30px;
                }}
                .success-badge {{
                    background-color: #ECFDF5;
                    border: 1.5px solid #A7F3D0;
                    border-radius: 10px;
                    padding: 16px 20px;
                    margin-bottom: 24px;
                    display: flex;
                    align-items: flex-start;
                    gap: 14px;
                }}
                .success-badge h3 {{
                    margin: 0 0 4px;
                    color: #065F46;
                    font-size: 16px;
                }}
                .success-badge p {{
                    margin: 0;
                    color: #047857;
                    font-size: 13px;
                    line-height: 1.4;
                }}
                .details-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 24px;
                    background: #F9FAFB;
                    border-radius: 8px;
                    overflow: hidden;
                    border: 1px solid #F3F4F6;
                }}
                .details-table td {{
                    padding: 11px 16px;
                    font-size: 13px;
                    border-bottom: 1px solid #F3F4F6;
                }}
                .details-table tr:last-child td {{
                    border-bottom: none;
                }}
                .details-table td.label {{
                    color: #6B7280;
                    font-weight: 600;
                    width: 38%;
                }}
                .details-table td.value {{
                    color: #111827;
                    font-weight: 500;
                }}
                
                /* Action buttons row */
                .actions-row {{
                    display: flex;
                    gap: 10px;
                    margin-bottom: 24px;
                }}
                .action-btn {{
                    flex: 1;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 6px;
                    padding: 10px 14px;
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: 600;
                    text-decoration: none;
                    cursor: pointer;
                    transition: all 0.15s ease;
                    border: none;
                }}
                .btn-primary {{
                    background: #185FA5;
                    color: #FFFFFF;
                }}
                .btn-primary:hover {{
                    background: #144E8A;
                }}
                .btn-outline {{
                    background: #FFFFFF;
                    color: #374151;
                    border: 1.5px solid #D1D5DB;
                }}
                .btn-outline:hover {{
                    background: #F9FAFB;
                    border-color: #9CA3AF;
                }}

                /* Support Section */
                .support-box {{
                    background: #EFF6FF;
                    border: 1.5px solid #BFDBFE;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                }}
                .support-box h4 {{
                    margin: 0 0 10px;
                    color: #1E3A8A;
                    font-size: 15px;
                }}
                .contact-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 10px;
                    margin-top: 14px;
                }}
                .contact-card {{
                    background: #FFFFFF;
                    border: 1px solid #DBEAFE;
                    padding: 12px 14px;
                    border-radius: 8px;
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }}
                .contact-card .title {{
                    font-size: 11px;
                    font-weight: 700;
                    color: #6B7280;
                    text-transform: uppercase;
                }}
                .contact-card .val {{
                    font-size: 13px;
                    font-weight: 600;
                    color: #1E40AF;
                    text-decoration: none;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                }}

                /* Interactive message box */
                .inquiry-box {{
                    background: #FAFAFA;
                    border: 1px solid #E5E7EB;
                    border-radius: 10px;
                    padding: 18px 20px;
                    margin-top: 20px;
                }}
                .inquiry-box h4 {{
                    margin: 0 0 8px;
                    color: #1F2937;
                    font-size: 14px;
                }}
                .form-control {{
                    width: 100%;
                    padding: 9px 12px;
                    border: 1.5px solid #D1D5DB;
                    border-radius: 7px;
                    font-size: 13px;
                    margin-bottom: 10px;
                    font-family: inherit;
                    outline: none;
                }}
                .form-control:focus {{
                    border-color: #185FA5;
                }}
                .submit-inquiry-btn {{
                    background: #10B981;
                    color: #fff;
                    border: none;
                    padding: 9px 16px;
                    border-radius: 7px;
                    font-weight: 600;
                    font-size: 13px;
                    cursor: pointer;
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                }}
                .submit-inquiry-btn:hover {{
                    background: #059669;
                }}

                /* Toast message */
                #toast {{
                    display: none;
                    position: fixed;
                    bottom: 24px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: #111827;
                    color: #FFFFFF;
                    padding: 10px 20px;
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: 500;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    z-index: 1000;
                }}

                .footer {{
                    background: #F9FAFB;
                    padding: 16px 30px;
                    border-top: 1px solid #E5E7EB;
                    text-align: center;
                    font-size: 12px;
                    color: #9CA3AF;
                }}

                @media print {{
                    body {{ background: #fff; padding: 0; }}
                    .card {{ box-shadow: none; border: none; max-width: 100%; }}
                    .actions-row, .inquiry-box, .email-options {{ display: none !important; }}
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="header">
                    <div>
                        <h1>EduGuard Student Support</h1>
                        <p>Academic Alert Confirmation Receipt</p>
                    </div>
                    <div class="ref-badge">Ref: #{log.id}</div>
                </div>

                <div class="body">
                    <div class="success-badge">
                        <div style="font-size: 24px;">✅</div>
                        <div>
                            <h3>Academic Notice Successfully Acknowledged</h3>
                            <p>{'Your receipt has been updated and confirmed in the university monitoring system.' if was_already_acknowledged else 'Thank you for confirming receipt of your academic alert. Your student file has been updated.'}</p>
                        </div>
                    </div>

                    <table class="details-table">
                        <tr>
                            <td class="label">Student Name</td>
                            <td class="value"><strong>{log.student_name}</strong></td>
                        </tr>
                        <tr>
                            <td class="label">Student ID</td>
                            <td class="value">{log.student_id}</td>
                        </tr>
                        <tr>
                            <td class="label">Course / Unit</td>
                            <td class="value"><strong>{log.subject}</strong></td>
                        </tr>
                        <tr>
                            <td class="label">Notice Type</td>
                            <td class="value">Week {log.week or 4} Academic Progress Alert</td>
                        </tr>
                        <tr>
                            <td class="label">Acknowledgment Time</td>
                            <td class="value">{formatted_time}</td>
                        </tr>
                        <tr>
                            <td class="label">Official Status</td>
                            <td class="value"><span style="color:#059669;font-weight:700;">● Confirmed by Student</span></td>
                        </tr>
                    </table>

                    <!-- Action buttons -->
                    <div class="actions-row">
                        <button onclick="window.print()" class="action-btn btn-outline" title="Print this receipt for your records">
                            🖨️ Print / Save PDF
                        </button>
                        <a href="http://localhost:5173/alerts" class="action-btn btn-primary" title="Open EduGuard Dashboard">
                            📊 View Alerts Dashboard
                        </a>
                    </div>

                    <!-- Interactive Student Support Section -->
                    <div class="support-box">
                        <h4>Need Help or Study Assistance?</h4>
                        <p style="margin:0 0 12px;color:#3B82F6;font-size:13px;line-height:1.4;">
                            Your course coordinator and student support team are ready to assist you. Choose how you would like to get in touch:
                        </p>

                        <div class="contact-grid">
                            <!-- Email with Copy & Webmail -->
                            <div class="contact-card">
                                <span class="title">Email Support</span>
                                <div style="display:flex;align-items:center;justify-content:space-between;margin-top:2px;">
                                    <span style="font-size:13px;font-weight:600;color:#185FA5;">support@eduguard.com</span>
                                    <button onclick="copySupportEmail()" style="background:#EBF4FF;border:1px solid #BFDBFE;color:#185FA5;padding:3px 8px;border-radius:5px;font-size:11px;cursor:pointer;font-weight:600;">
                                        📋 Copy
                                    </button>
                                </div>
                                <div style="display:flex;gap:6px;margin-top:6px;">
                                    <a href="{gmail_compose}" target="_blank" style="font-size:11px;color:#DC2626;text-decoration:none;font-weight:600;">✉️ Open Gmail</a>
                                    <span style="color:#D1D5DB;">·</span>
                                    <a href="{outlook_compose}" target="_blank" style="font-size:11px;color:#0284C7;text-decoration:none;font-weight:600;">✉️ Open Outlook</a>
                                </div>
                            </div>

                            <!-- Direct Phone -->
                            <div class="contact-card">
                                <span class="title">Student Centre Phone</span>
                                <a href="tel:+61292833583" class="val" style="margin-top:2px;">
                                    📞 +61 (02) 9283 3583
                                </a>
                                <span style="font-size:11px;color:#6B7280;margin-top:4px;">Mon–Fri, 9:00 AM – 5:00 PM</span>
                            </div>
                        </div>

                        <!-- Interactive Message Box to Advisor -->
                        <div class="inquiry-box" style="margin-top:16px;">
                            <h4>Send a Quick Update to Your Academic Advisor:</h4>
                            <select id="inquiryReason" class="form-control">
                                <option value="I have submitted my outstanding assignments">I have submitted my outstanding assignments</option>
                                <option value="I would like to request an academic consultation">I would like to request a 1-on-1 consultation</option>
                                <option value="I am having technical / LMS access issues">I am having technical / LMS access issues</option>
                                <option value="I would like to discuss special consideration">I would like to discuss special consideration</option>
                                <option value="Other general question">Other inquiry</option>
                            </select>
                            <textarea id="inquiryMessage" rows="2" class="form-control" placeholder="Add optional details or note for your advisor..."></textarea>
                            <button onclick="submitSupportInquiry()" class="submit-inquiry-btn">
                                📤 Send Message to Advisor
                            </button>
                            <div id="inquirySuccess" style="display:none;margin-top:12px;background:#ECFDF5;border:1px solid #A7F3D0;color:#065F46;padding:10px 14px;border-radius:7px;font-size:13px;font-weight:600;">
                                ✅ Your message has been sent to your Academic Advisor and Student Support Centre!
                            </div>
                        </div>
                    </div>
                </div>

                <div class="footer">
                    EduGuard Academic Alert & Intervention System · Official University Receipt
                </div>
            </div>

            <!-- Toast notification -->
            <div id="toast">✅ Email address copied to clipboard!</div>

            <script>
                function copySupportEmail() {{
                    const email = 'support@eduguard.com';
                    navigator.clipboard.writeText(email).then(() => {{
                        showToast('📋 Copied support@eduguard.com to clipboard!');
                    }}).catch(() => {{
                        showToast('Email: support@eduguard.com');
                    }});
                }}

                function showToast(msg) {{
                    const toast = document.getElementById('toast');
                    toast.innerText = msg;
                    toast.style.display = 'block';
                    setTimeout(() => {{
                        toast.style.display = 'none';
                    }}, 3000);
                }}

                function submitSupportInquiry() {{
                    const reason = document.getElementById('inquiryReason').value;
                    const message = document.getElementById('inquiryMessage').value;
                    const btn = document.querySelector('.submit-inquiry-btn');
                    
                    btn.disabled = true;
                    btn.innerText = 'Sending...';

                    fetch('/alerts/support-message', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            log_id: {log.id},
                            student_name: '{log.student_name}',
                            subject: '{log.subject}',
                            reason: reason,
                            message: message
                        }})
                    }})
                    .then(res => res.json())
                    .then(data => {{
                        document.getElementById('inquirySuccess').style.display = 'block';
                        btn.style.display = 'none';
                        showToast('✅ Message dispatched to Academic Advisor!');
                    }})
                    .catch(err => {{
                        document.getElementById('inquirySuccess').style.display = 'block';
                        btn.style.display = 'none';
                    }});
                }}
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=200)
    except Exception as e:
        logger.error(f"Error processing student acknowledgment: {e}")
        return HTMLResponse(content=f"<h3>Error processing acknowledgment: {str(e)}</h3>", status_code=500)


@router.get("/logs")
def get_email_logs(db: Session = Depends(get_db)):
    """Fetch all email logs with acknowledgment and error details"""
    try:
        logs = db.query(EmailLog).order_by(EmailLog.created_at.desc()).all()

        def format_date(dt_val):
            if not dt_val:
                return "—"
            if hasattr(dt_val, "strftime"):
                return dt_val.strftime("%Y-%m-%d %H:%M")
            return str(dt_val)[:16]

        return [
            {
                "id": str(log.id),
                "student": log.student_name,
                "studentId": f"ID_{log.student_id}",
                "email": log.email,
                "subject": log.subject,
                "type": log.email_type,
                "template": log.template,
                "status": log.status,
                "sentAt": format_date(log.sent_at),
                "openedAt": format_date(log.opened_at),
                "acknowledgedAt": format_date(log.acknowledged_at),
                "rawSentAt": log.sent_at.isoformat() if log.sent_at else None,
                "rawAcknowledgedAt": log.acknowledged_at.isoformat() if log.acknowledged_at else None,
                "errorMessage": log.error_message
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
    """Fetch alert statistics (total, acknowledged, sent/awaiting, failed)"""
    try:
        total = db.query(EmailLog).count()
        acknowledged = db.query(EmailLog).filter(EmailLog.status == "Acknowledged").count()
        sent = db.query(EmailLog).filter(EmailLog.status == "Sent").count()
        failed = db.query(EmailLog).filter(EmailLog.status == "Failed").count()
        
        return {
            "total": total,
            "acknowledged": acknowledged,
            "opened": acknowledged,  # for backward compatibility
            "sent": sent,
            "failed": failed
        }
    except Exception as e:
        logger.error(f"Error fetching alert stats: {e}")
        return {"total": 0, "acknowledged": 0, "opened": 0, "sent": 0, "failed": 0}


@router.post("/send/{student_id}")
def send_alert_to_student(student_id: int, db: Session = Depends(get_db)):
    """Send alert email to specific student with acknowledgment tracking"""
    try:
        week = settings.CHECKPOINT_WEEK
        
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        if not student.email:
            return {"success": False, "message": "Student has no email address on file"}
        
        # Pre-create email log to obtain unique log ID for acknowledgment link
        email_log = EmailLog(
            student_id=student_id,
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
        db.flush()  # Generates email_log.id
        
        # Send email with acknowledgment link embedded
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
            
            mark_sent(student_id, week)
            student.last_alert_sent = get_current_time()
            student.alert_count = (student.alert_count or 0) + 1
            
            db.commit()
            logger.info(f"✅ Alert #{email_log.id} sent to {student.full_name} ({student.email})")
            return {"success": True, "message": f"Alert sent to {student.email}"}
        else:
            email_log.status = "Failed"
            email_log.error_message = error_msg or "SMTP delivery failed"
            db.commit()
            
            logger.error(f"❌ Failed to send alert to {student.full_name}: {error_msg}")
            return {"success": False, "message": error_msg or "Failed to send email"}
    
    except Exception as e:
        logger.error(f"Error sending alert: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-bulk")
def send_bulk_alerts(payload: dict = None, db: Session = Depends(get_db)):
    """Send bulk alerts to all pending at-risk students"""
    try:
        if payload is None:
            payload = {}
        week = payload.get("week", settings.CHECKPOINT_WEEK)
        logger.info(f"📧 Starting bulk alert send for week {week}")
        
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
            
            if already_sent(student.id, week):
                skipped_count += 1
                continue
            
            # Pre-create log
            email_log = EmailLog(
                student_id=student.id,
                student_name=student.full_name,
                email=student.email,
                subject=student.program or "General",
                email_type="Bulk Alert",
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
                mark_sent(student.id, week)
                email_log.status = "Sent"
                email_log.sent_at = get_current_time()
                email_log.error_message = None
                
                student.last_alert_sent = get_current_time()
                student.alert_count = (student.alert_count or 0) + 1
                sent_count += 1
            else:
                failed_count += 1
                email_log.status = "Failed"
                email_log.error_message = error_msg or "Delivery failed"
        
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
        db.rollback()
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
            student = db.query(Student).filter(Student.id == log.student_id).first()
            if not student or not student.email:
                continue
            
            success, error_msg = EmailService.send_student_alert(
                student_email=student.email,
                student_name=student.full_name,
                subject_code=student.program or "General",
                week=log.week or settings.CHECKPOINT_WEEK,
                log_id=log.id
            )
            
            if success:
                log.status = "Sent"
                log.sent_at = get_current_time()
                log.error_message = None
                sent_count += 1
                logger.info(f"✅ Retry successful for {student.full_name}")
            else:
                log.retry_count += 1
                log.error_message = error_msg or "Retry failed"
                failed_count += 1
                logger.warning(f"⚠️ Retry failed for {student.full_name}: {error_msg}")
        
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
        db.rollback()
        return {
            "success": False,
            "message": str(e),
            "sent_count": 0,
            "failed_count": 0,
            "skipped_count": 0
        }
