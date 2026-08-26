"""
Email Service
Handles SMTP email sending, recipient validation, acknowledgment link embedding, and template generation
"""

import smtplib
import re
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def safe_print(msg: str):
    """Safely print message even on Windows non-UTF8 console encodings"""
    try:
        print(msg)
    except Exception:
        try:
            print(msg.encode("ascii", "replace").decode("ascii"))
        except Exception:
            pass



class EmailService:
    """Email sending service"""

    @staticmethod
    def validate_email_address(email: str) -> tuple[bool, str | None]:
        """Validate email format and basic domain sanity"""
        if not email or not isinstance(email, str):
            return False, "Email address is missing or empty"
        email = email.strip()
        if not EMAIL_REGEX.match(email):
            return False, f"Invalid email format: '{email}'"
        return True, None
    
    @staticmethod
    def build_student_alert_email(
        student_name: str,
        subject_code: str,
        week: int,
        log_id: int | None = None,
        base_url: str = "http://localhost:8000"
    ) -> tuple[str, str]:
        """Build student at-risk alert email with acknowledgment link"""
        
        name = student_name.strip().title()
        acknowledge_url = f"{base_url}/alerts/acknowledge/{log_id}" if log_id else f"{base_url}/alerts/acknowledge"
        
        html = f"""
        <html>
        <body style="font-family:Arial,sans-serif;color:#333;line-height:1.6;background-color:#f4f6f8;margin:0;padding:20px;">
            <div style="max-width:600px;margin:auto;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
                <div style="background:#1F4E79;padding:20px 24px;border-radius:8px 8px 0 0;">
                    <h2 style="color:#ffffff;margin:0;font-size:20px;">EduGuard - Academic Alert</h2>
                    <p style="color:#c9d9e8;margin:4px 0 0;font-size:13px;">Student Support Notification · Week {week}</p>
                </div>
                <div style="padding:24px 28px;border:1px solid #e5e7eb;border-top:none;">
                    <p style="font-size:15px;margin-top:0;">Dear <strong>{name}</strong>,</p>
                    
                    <p>Our academic monitoring system has flagged you as <strong>potentially at risk</strong> in <strong>{subject_code}</strong> as of <strong>Week {week}</strong>.</p>
                    
                    <!-- Mandatory Acknowledgment Box -->
                    <div style="background:#f0fdf4;border:1.5px solid #86efac;padding:18px 20px;border-radius:8px;margin:22px 0;text-align:center;">
                        <h4 style="margin:0 0 6px;color:#166534;font-size:14px;text-transform:uppercase;letter-spacing:0.04em;">Mandatory Student Acknowledgment</h4>
                        <p style="margin:0 0 14px;color:#15803d;font-size:13px;">Please click below to confirm that you have read and received this academic notice.</p>
                        <a href="{acknowledge_url}" target="_blank" style="display:inline-block;background:#16a34a;color:#ffffff;text-decoration:none;padding:11px 22px;border-radius:6px;font-weight:bold;font-size:13px;box-shadow:0 2px 6px rgba(22,163,74,0.35);">
                            ✅ I Acknowledge I Have Received This Notice
                        </a>
                        <p style="margin:10px 0 0;color:#6b7280;font-size:11px;">Receipt will be recorded automatically for your student file.</p>
                    </div>

                    <h3 style="color:#1F4E79;font-size:15px;margin-top:20px;margin-bottom:8px;">Recommended Next Steps:</h3>
                    <ul style="padding-left:20px;margin-top:4px;">
                        <li style="margin-bottom:6px;">Contact your lecturer or tutor to discuss your progress</li>
                        <li style="margin-bottom:6px;">Submit any outstanding assignments immediately</li>
                        <li style="margin-bottom:6px;">Check your attendance and LMS submission records</li>
                        <li style="margin-bottom:6px;">Visit Student Support if experiencing difficulties</li>
                    </ul>
                    
                    <div style="background:#e8f4fd;padding:14px 18px;border-radius:6px;margin-top:20px;border-left:4px solid #1F4E79;">
                        <strong style="color:#1F4E79;">Student Support Centre</strong><br>
                        <span style="font-size:13px;color:#4b5563;">
                        Email: <a href="mailto:support@eduguard.com" style="color:#1F4E79;font-weight:600;">support@eduguard.com</a><br>
                        Phone: <a href="tel:+61292833583" style="color:#1F4E79;text-decoration:none;">+61 (02) 9283 3583</a><br>
                        Hours: Monday – Friday, 9:00 AM – 5:00 PM (AEST)
                        </span>
                    </div>
                    
                    <p style="margin-top:22px;color:#666;font-size:12px;">
                        Early intervention makes a real difference. Please do not hesitate to reach out for assistance.
                    </p>
                    
                    <p style="margin-top:20px;margin-bottom:0;font-size:13px;">Best regards,<br><strong>EduGuard Academic Support Team</strong></p>
                </div>
                
                <div style="background:#f9fafb;padding:12px 24px;border-top:1px solid #e5e7eb;text-align:center;">
                    <p style="font-size:11px;color:#9ca3af;margin:0;">
                        This is an automated notification from EduGuard System.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        plain = f"""
Dear {name},

Our academic monitoring system has flagged you as potentially at risk in {subject_code} as of Week {week}.

MANDATORY STUDENT ACKNOWLEDGMENT:
Please click the link below to confirm you have received this notice:
{acknowledge_url}

WHAT YOU SHOULD DO:
- Contact your lecturer or tutor to discuss your progress
- Submit any outstanding assignments immediately
- Check your attendance and submission records
- Visit Student Support if facing difficulties

STUDENT SUPPORT CENTRE
Email: support@eduguard.com
Hours: Monday – Friday, 9:00 AM – 5:00 PM (AEST)

Early intervention makes a real difference.

Best regards,
EduGuard Academic Support Team
"""
        
        return html, plain
    
    @staticmethod
    def send_email(to_email: str, subject: str, html: str, plain: str) -> tuple[bool, str | None]:
        """Send email via SMTP or simulate in development mode. Returns (success, error_message)"""
        try:
            # 1. Validate recipient email syntax
            is_valid, validation_err = EmailService.validate_email_address(to_email)
            if not is_valid:
                logger.error(f"❌ Invalid recipient email: {validation_err}")
                safe_print(f"❌ Invalid recipient email: {validation_err}")
                return False, validation_err

            # 2. Check if SMTP credentials are configured; if not, simulate
            if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
                logger.info(f"📧 [DEV/TEST MODE - Simulated Send] To: {to_email} | Subject: {subject}")
                safe_print(f"📧 [DEV/TEST MODE - Simulated Send] To: {to_email} | Subject: {subject}")
                return True, None

            sender = settings.EMAIL_FROM if settings.EMAIL_FROM else settings.SMTP_USERNAME

            # 3. Create MIME message
            msg = MIMEMultipart("alternative")
            msg["From"] = f"EduGuard <{sender}>"
            msg["To"] = to_email
            msg["Subject"] = subject
            
            # Attach plain text and HTML
            msg.attach(MIMEText(plain, "plain"))
            msg.attach(MIMEText(html, "html"))
            
            # 4. Connect to SMTP server
            if settings.SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
                server.starttls()

            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(sender, to_email, msg.as_string())
            server.quit()
            
            logger.info(f"✅ Email sent successfully to {to_email}")
            safe_print(f"✅ Email sent successfully to {to_email}")
            return True, None
            
        except smtplib.SMTPRecipientsRefused as e:
            err = f"Recipient email address rejected or not found (550): {str(e)}"
            logger.error(f"❌ {err}")
            safe_print(f"❌ {err}")
            return False, err
        except smtplib.SMTPSenderRefused as e:
            err = f"Sender email address rejected: {str(e)}"
            logger.error(f"❌ {err}")
            safe_print(f"❌ {err}")
            return False, err
        except smtplib.SMTPAuthenticationError as e:
            err = f"SMTP Authentication failed: {str(e)}"
            logger.error(f"❌ {err}")
            safe_print(f"❌ {err}")
            return False, err
        except smtplib.SMTPConnectError as e:
            err = f"Failed to connect to SMTP server: {str(e)}"
            logger.error(f"❌ {err}")
            safe_print(f"❌ {err}")
            return False, err
        except Exception as e:
            err = f"SMTP send error: {str(e)}"
            logger.error(f"❌ Failed to send email to {to_email}: {err}")
            safe_print(f"❌ Failed to send email to {to_email}: {err}")
            return False, err
    
    @staticmethod
    def send_student_alert(
        student_email: str,
        student_name: str,
        subject_code: str,
        week: int,
        log_id: int | None = None
    ) -> tuple[bool, str | None]:
        """Convenience method to send student alert with embedded acknowledgment link"""
        html, plain = EmailService.build_student_alert_email(student_name, subject_code, week, log_id)
        ref_tag = f" [Ref: #{log_id}]" if log_id else ""
        subject = f"[EduGuard] Academic Alert – {subject_code} Week {week}{ref_tag}"
        return EmailService.send_email(student_email, subject, html, plain)

    @staticmethod
    def verify_smtp_connection() -> tuple[bool, str]:
        """Test the SMTP server connection and authentication"""
        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            return False, "SMTP_USERNAME or SMTP_PASSWORD is not set in environment / .env"
        try:
            if settings.SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
                server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.quit()
            return True, f"Successfully authenticated to {settings.SMTP_HOST}:{settings.SMTP_PORT} as {settings.SMTP_USERNAME}"
        except Exception as e:
            return False, f"SMTP Connection failed: {str(e)}"
