"""
Setup instructions for EduGuard Alerts System
Integrates ML-based risk detection with automated email notifications
"""

# ─────────────────────────────────────────────
#  BACKEND SETUP
# ─────────────────────────────────────────────

## 1. ENVIRONMENT CONFIGURATION

Create a `.env` file in the project root with:

```
# Application
APP_NAME=EduGuard
ENVIRONMENT=development
DEBUG=True
FRONTEND_URL=http://localhost:5173
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/eduguard

# JWT Authentication
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email Notifications (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@eduguard.com

# ML Configuration
MODEL_PATH=backend/app/ml/models/risk_model.pkl
RISK_THRESHOLD=0.5

# Scheduler
CHECKPOINT_WEEK=4
SCHEDULER_TIMEZONE=UTC
```

## 2. GMAIL APP PASSWORD SETUP

1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification (if not already enabled)
3. Go to App passwords (https://myaccount.google.com/apppasswords)
4. Select "Mail" and "Windows Computer"
5. Copy the generated app password
6. Paste into `SMTP_PASSWORD` in `.env`

## 3. INSTALL PYTHON DEPENDENCIES

```bash
cd backend
pip install -r requirements.txt
```

Required packages:
- fastapi
- sqlalchemy
- psycopg2-binary
- pydantic-settings
- python-multipart
- email-validator
- python-dotenv

## 4. DATABASE MIGRATION

```bash
# Create tables
alembic upgrade head

# Or manually create tables by running the app once
python -m uvicorn app.main:app --reload
```

## 5. RUN BACKEND

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: `http://localhost:8000`
API docs: `http://localhost:8000/docs`


# ─────────────────────────────────────────────
#  FRONTEND SETUP
# ─────────────────────────────────────────────

## 1. INSTALL DEPENDENCIES

```bash
cd frontend
npm install
```

## 2. RUN FRONTEND

```bash
npm run dev
```

Frontend will be available at: `http://localhost:5173`


# ─────────────────────────────────────────────
#  ALERTS API ENDPOINTS
# ─────────────────────────────────────────────

## GET /alerts/logs
Fetch email notification logs

**Response:**
```json
[
  {
    "id": "email_0",
    "student": "John Smith",
    "studentId": "KOI001",
    "subject": "ICT724",
    "type": "Risk Alert",
    "template": "at_risk_alert_week4",
    "status": "Sent",
    "sentAt": "2025-01-15 14:32",
    "openedAt": "—"
  }
]
```

## GET /alerts/queue
Fetch pending alerts (students not yet notified this week)

**Response:**
```json
[
  {
    "id": 1,
    "name": "Jane Doe",
    "initials": "JD",
    "studentId": "KOI002",
    "email": "jane@koi.edu.au",
    "subject": "ICT724",
    "risk": "HIGH"
  }
]
```

## GET /alerts/stats
Fetch alert statistics

**Response:**
```json
{
  "total": 45,
  "opened": 23,
  "sent": 15,
  "failed": 7
}
```

## POST /alerts/send/{student_id}
Send alert to a single student

**Response:**
```json
{
  "success": true,
  "message": "Alert sent to jane@koi.edu.au"
}
```

## POST /alerts/send-bulk
Send bulk alerts to all pending at-risk students

**Request Body:**
```json
{
  "week": 4
}
```

**Response:**
```json
{
  "success": true,
  "message": "Bulk alerts sent. 12 sent, 2 failed, 3 skipped",
  "sent_count": 12,
  "failed_count": 2,
  "skipped_count": 3
}
```

## POST /alerts/retry-failed
Retry sending failed alerts

**Response:**
```json
{
  "success": true,
  "message": "Retry complete. 2 sent, 0 still failed",
  "sent_count": 2,
  "failed_count": 0,
  "skipped_count": 0
}
```


# ─────────────────────────────────────────────
#  FRONTEND INTEGRATION
# ─────────────────────────────────────────────

## Updated AlertsPage Component

The AlertsPage now:
✅ Fetches real data from backend APIs
✅ Shows live alert queue from database
✅ Displays email notification logs
✅ Sends individual alerts to students
✅ Supports bulk alert sending
✅ Shows email statistics

## API Service (src/app/api/alerts.ts)

Functions available:
- `fetchEmailLogs()` - Get all email logs
- `fetchAlertQueue()` - Get pending alerts
- `fetchAlertStats()` - Get statistics
- `sendAlertToStudent(studentId)` - Send single alert
- `sendBulkAlerts(week)` - Send bulk alerts
- `retryFailedAlerts()` - Retry failed emails


# ─────────────────────────────────────────────
#  STUDENT MODEL SCHEMA
# ─────────────────────────────────────────────

The Student model tracks:

**Basic Info:**
- student_number (unique ID)
- first_name, last_name
- email, phone
- age, gender

**Academic Info:**
- program (e.g., ICT724)
- attendance_rate (0-100%)
- gpa
- assignments_completed / assignments_total

**Risk Assessment (from ML model):**
- ml_score (0-1, raw prediction)
- risk_status (HIGH, MEDIUM, LOW)
- confidence_score (0-1)
- risk_trend (IMPROVING, STABLE, DECLINING)

**Email Tracking:**
- is_emailed (boolean)
- last_alert_sent (timestamp)
- alert_count (number of alerts sent)

**Status:**
- is_active (boolean)
- created_at, updated_at (timestamps)


# ─────────────────────────────────────────────
#  DATABASE IMPORT (EXCEL TO DATABASE)
# ─────────────────────────────────────────────

To import student data from Excel:

```python
import pandas as pd
from app.models.student import Student
from app.database import SessionLocal

# Read Excel file
df = pd.read_excel('students.xlsx', sheet_name='Sheet1')

# Connect to database
db = SessionLocal()

# Create student records
for _, row in df.iterrows():
    student = Student(
        student_number=row['student_id'],
        first_name=row['first_name'],
        last_name=row['last_name'],
        email=row['email'],
        program=row['subject'],
        attendance_rate=row.get('attendance', 0),
        gpa=row.get('gpa'),
        ml_score=row.get('ml_score', 0),
        risk_status=row.get('risk_status', 'LOW'),
        confidence_score=row.get('confidence', 0),
    )
    db.add(student)

db.commit()
db.close()
```


# ─────────────────────────────────────────────
#  PRODUCTION CHECKLIST
# ─────────────────────────────────────────────

Before deploying to production:

□ Change SECRET_KEY in .env
□ Set ENVIRONMENT=production
□ Set DEBUG=False
□ Update FRONTEND_URL and ALLOWED_ORIGINS
□ Use real database (PostgreSQL)
□ Configure SMTP with production email
□ Enable HTTPS/SSL
□ Set up rate limiting
□ Configure logging
□ Test email delivery
□ Backup database regularly
□ Monitor error logs
□ Set up alert retention policy


# ─────────────────────────────────────────────
#  TROUBLESHOOTING
# ─────────────────────────────────────────────

### Issue: SMTP connection fails
- Verify Gmail app password is correct
- Check SMTP_HOST and SMTP_PORT in .env
- Enable "Less secure app access" if using regular password
- Check firewall/antivirus blocking port 587

### Issue: No students found in alert queue
- Verify students exist in database with risk_status HIGH/MEDIUM
- Check that is_active=True for students
- Verify email addresses are populated

### Issue: Emails marked as Failed
- Check SMTP credentials
- Check email recipient addresses are valid
- View backend logs for error details
- Retry failed emails using /alerts/retry-failed endpoint

### Issue: CORS errors in frontend
- Verify backend ALLOWED_ORIGINS includes frontend URL
- Check that both frontend and backend are running
- Clear browser cache and cookies

### Issue: Database connection error
- Verify DATABASE_URL is correct
- Check PostgreSQL is running
- Verify database exists
- Check username/password


# ─────────────────────────────────────────────
#  FILE STRUCTURE
# ─────────────────────────────────────────────

```
EduGuard/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI application
│   │   ├── config.py                  # Environment configuration
│   │   ├── database.py                # Database setup
│   │   ├── models/
│   │   │   ├── student.py             # Student model
│   │   │   ├── user.py                # User/auth model
│   │   │   └── enums.py               # Enums
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── alerts.py          # Alerts endpoints
│   │   │       ├── students.py        # Student endpoints
│   │   │       └── super_admin.py     # Admin endpoints
│   │   ├── core/
│   │   │   ├── security.py            # Auth utilities
│   │   │   └── dependencies.py        # FastAPI dependencies
│   │   └── ml/
│   │       └── models/                # ML model files
│   └── requirements.txt               # Python dependencies
│
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── pages/
    │   │   │   └── AlertsPage.tsx      # Alerts page (updated)
    │   │   ├── api/
    │   │   │   └── alerts.ts           # Alerts API service (new)
    │   │   ├── components/
    │   │   ├── context/
    │   │   └── data/
    │   └── main.tsx
    └── package.json
```


# ─────────────────────────────────────────────
#  DEPLOYMENT
# ─────────────────────────────────────────────

### Docker Deployment

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: eduguard
      POSTGRES_USER: eduguard
      POSTGRES_PASSWORD: secure_password
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://eduguard:secure_password@postgres:5432/eduguard
    ports:
      - "8000:8000"
    depends_on:
      - postgres

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
```

Run:
```bash
docker-compose up -d
```

### Heroku Deployment

```bash
# Add Procfile to backend/
echo "web: gunicorn app.main:app" > backend/Procfile

# Deploy
git push heroku main
```
