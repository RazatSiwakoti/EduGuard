"""
Email Service
Handles SMTP email sending and template generation
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Email sending service"""
    
    @staticmethod
    def build_student_alert_email(student_name: str, subject_code: str, week: int) -> tuple[str, str]:
        """Build student at-risk alert email"""
        
        name = student_name.strip().title()
        
        html = f"""
        <html>
        <body style="font-family:Arial,sans-serif;color:#333;line-height:1.6;">
            <div style="max-width:600px;margin:auto;padding:24px;">
                <div style="background:#1F4E79;padding:16px 24px;border-radius:6px 6px 0 0;">
                    <h2 style="color:#fff;margin:0;">EduGuard - Academic Alert</h2>
                    <p style="color:#c9d9e8;margin:4px 0 0;">Student Support - Week {week}</p>
                </div>
                <div style="background:#f9f9f9;padding:24px;border:1px solid #ddd;border-top:none;border-radius:0 0 6px 6px;">
                    <p>Dear <strong>{name}</strong>,</p>
                    
                    <p>Our academic monitoring system has flagged you as <strong>potentially at risk</strong> in <strong>{subject_code}</strong> as of <strong>Week {week}</strong>.</p>
                    
                    <p>This is important - please take action immediately:</p>
                    
                    <h3 style="color:#1F4E79;">What You Should Do Now</h3>
                    <ul>
                        <li>Contact your lecturer or tutor to discuss your progress</li>
                        <li>Submit any outstanding assignments immediately</li>
                        <li>Check your attendance and submission records</li>
                        <li>Visit Student Support if facing difficulties</li>
                    </ul>
                    
                    <div style="background:#e8f4fd;padding:12px 16px;border-radius:4px;margin-top:16px;">
                        <strong>Student Support Centre</strong><br>
                        Email: <a href="mailto:support@eduguard.com">support@eduguard.com</a><br>
                        Phone: (02) XXXX XXXX<br>
                        Hours: Mon-Fri 9AM-5PM
                    </div>
                    
                    <p style="margin-top:24px;color:#666;font-size:13px;">
                        Early intervention makes a real difference. Don't hesitate to reach out.
                    </p>
                    
                    <p style="margin-top:24px;">Best regards,<br><strong>EduGuard Support Team</strong></p>
                </div>
                
                <p style="font-size:11px;color:#999;text-align:center;margin-top:12px;">
                    This is an automated message from EduGuard. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        plain = f"""
        Dear {name},
        
        Our academic monitoring system has flagged you as potentially at risk in {subject_code} as of Week {week}.
        
        WHAT YOU SHOULD DO:
        - Contact your lecturer or tutor
        - Submit outstanding assignments
        - Check your attendance records
        - Visit Student Support if you need help
        
        STUDENT SUPPORT CENTRE
        Email: support@eduguard.com
        Phone: (02) XXXX XXXX
        
        Early intervention makes a real difference.
        
        Best regards,
        EduGuard Support Team
        """
        
        return html, plain
    
    @staticmethod
    def send_email(to_email: str, subject: str, html: str, plain: str) -> bool:
        """Send email via SMTP"""
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = f"EduGuard <{settings.SMTP_USERNAME}>"
            msg["To"] = to_email
            msg["Subject"] = subject
            
            # Attach plain text and HTML
            msg.attach(MIMEText(plain, "plain"))
            msg.attach(MIMEText(html, "html"))
            
            # Send via SMTP
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USERNAME, to_email, msg.as_string())
            server.quit()
            
            logger.info(f"✅ Email sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {str(e)}")
            return False
    
    @staticmethod
    def send_student_alert(student_email: str, student_name: str, subject_code: str, week: int) -> bool:
        """Convenience method to send student alert"""
        html, plain = EmailService.build_student_alert_email(student_name, subject_code, week)
        subject = f"[EduGuard] Academic Alert – {subject_code} Week {week}"
        return EmailService.send_email(student_email, subject, html, plain)
