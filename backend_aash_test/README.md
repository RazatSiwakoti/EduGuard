# EduGuard Alerts Backend - Clean Setup

Standalone FastAPI backend for the alerts system with email integration.

## Quick Start

### 1. Setup Environment

```bash
cd backend_aash_test

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Email

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` with your Gmail app password:
```
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

**To get Gmail App Password:**
1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification
3. Go to App passwords
4. Select Mail → Windows Computer
5. Copy the generated password

### 3. Run Backend

```bash
python -m uvicorn main:app --reload
```

Backend will be available at: **http://localhost:8000**
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## API Endpoints

### GET /alerts/logs
Fetch email notification logs

### GET /alerts/queue
Get pending alerts (HIGH/MEDIUM risk students)

### GET /alerts/stats
Alert statistics (total, sent, opened, failed)

### POST /alerts/send/{student_id}
Send alert to specific student

### POST /alerts/send-bulk
Send bulk alerts to all pending students
```json
{"week": 4}
```

### POST /alerts/retry-failed
Retry failed email sends

## Database

By default uses SQLite (`eduguard.db`). For PostgreSQL:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/eduguard
```

## File Structure

```
backend_aash_test/
├── main.py              # FastAPI app
├── config.py            # Configuration
├── database.py          # SQLAlchemy setup
├── models.py            # Student & EmailLog models
├── email_service.py     # Email sending service
├── alerts_routes.py     # Alert endpoints
├── requirements.txt     # Dependencies
├── .env.example         # Environment template
└── README.md           # This file
```

## Testing

Add a test student to database:

```python
from database import SessionLocal
from models import Student

db = SessionLocal()
student = Student(
    student_number="TEST001",
    first_name="John",
    last_name="Doe",
    email="john@example.com",
    program="ICT724",
    risk_status="HIGH",
    ml_score=0.85,
    confidence_score=0.92
)
db.add(student)
db.commit()
db.close()
```

Then send alert:
```
POST /alerts/send/1
```

## Troubleshooting

### Email send fails
- Verify SMTP credentials in `.env`
- Check Gmail App Password is correct
- Verify SMTP_PORT is 587
- Check internet connection

### Database errors
- Delete `eduguard.db` to reset
- Check DATABASE_URL in `.env`

### CORS errors
- Verify ALLOWED_ORIGINS includes your frontend URL
- Check frontend is running on correct port
