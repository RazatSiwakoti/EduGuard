# EduGuard - Alerts System Integration

Complete integration of automated email alerts for at-risk students in the EduGuard system.

**Branch:** `backend-aash-test` (New clean backend structure)
**Status:** ✅ Ready for testing

---

## 📋 What We've Built

### Problem Statement
Educators need to identify and alert at-risk students automatically. The system uses ML predictions to detect struggling students and sends timely email notifications to encourage early intervention.

### Solution
A complete alerts system with:
- ✅ **Backend API** (FastAPI) for alert management
- ✅ **Frontend UI** (React/TypeScript) for alert monitoring
- ✅ **Email Service** (SMTP) for student notifications
- ✅ **Database Tracking** for email logs and delivery status
- ✅ **Retry Logic** for failed emails
- ✅ **Duplicate Protection** to prevent duplicate alerts

---

## 🏗️ Architecture

### Frontend (Updated)
```
frontend/src/app/
├── pages/
│   └── AlertsPage.tsx          ← Updated with backend integration
├── api/
│   └── alerts.ts               ← New API service
└── context/
    └── ThemeContext.tsx        ← Existing theme support
```

### Backend (New - `backend_aash_test/`)
```
backend_aash_test/
├── main.py                     ← FastAPI application
├── config.py                   ← Environment configuration
├── database.py                 ← SQLAlchemy setup
├── models.py                   ← Student & EmailLog models
├── email_service.py            ← SMTP email sending
├── alerts_routes.py            ← 6 API endpoints
├── requirements.txt            ← Python dependencies
├── .env.example                ← Configuration template
└── README.md                   ← Backend setup guide
```

---

## 🔌 API Endpoints

All endpoints are prefixed with `/alerts`

### 1. **GET /alerts/logs**
Fetch all email notification logs
```bash
curl http://localhost:8000/alerts/logs
```
**Response:**
```json
[
  {
    "id": "1",
    "student": "John Smith",
    "studentId": "ID_1",
    "subject": "ICT724",
    "type": "Individual Alert",
    "template": "at_risk_alert_week4",
    "status": "Sent",
    "sentAt": "2025-01-15 14:32",
    "openedAt": "—"
  }
]
```

### 2. **GET /alerts/queue**
Get pending alerts (students not yet notified this week)
```bash
curl http://localhost:8000/alerts/queue
```
**Response:**
```json
[
  {
    "id": 1,
    "name": "Jane Doe",
    "initials": "JD",
    "studentId": "KOI002",
    "email": "jane@example.com",
    "subject": "ICT724",
    "risk": "HIGH"
  }
]
```

### 3. **GET /alerts/stats**
Get alert statistics
```bash
curl http://localhost:8000/alerts/stats
```
**Response:**
```json
{
  "total": 45,
  "opened": 23,
  "sent": 15,
  "failed": 7
}
```

### 4. **POST /alerts/send/{student_id}**
Send alert to a specific student
```bash
curl -X POST http://localhost:8000/alerts/send/1
```
**Response:**
```json
{
  "success": true,
  "message": "Alert sent to jane@example.com"
}
```

### 5. **POST /alerts/send-bulk**
Send bulk alerts to all pending at-risk students
```bash
curl -X POST http://localhost:8000/alerts/send-bulk \
  -H "Content-Type: application/json" \
  -d '{"week": 4}'
```
**Response:**
```json
{
  "success": true,
  "message": "Bulk alerts processed. 12 sent, 2 failed, 3 skipped",
  "sent_count": 12,
  "failed_count": 2,
  "skipped_count": 3
}
```

### 6. **POST /alerts/retry-failed**
Retry sending failed alerts
```bash
curl -X POST http://localhost:8000/alerts/retry-failed
```
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

---

## 🚀 Quick Start

### Backend Setup

```bash
# 1. Navigate to backend
cd backend_aash_test

# 2. Create virtual environment
python -m venv venv

# 3. Activate environment
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure email
cp .env.example .env
# Edit .env with Gmail credentials (see section below)

# 6. Run backend
python -m uvicorn main:app --reload
```

Backend will be available at: **http://localhost:8000**
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Frontend Setup

```bash
# 1. Navigate to frontend (from project root)
cd frontend

# 2. Install dependencies
npm install

# 3. Run frontend
npm run dev
```

Frontend will be available at: **http://localhost:5173**

---

## 📧 Gmail Setup (Email Configuration)

### Step 1: Enable 2-Step Verification
1. Go to https://myaccount.google.com/security
2. Under "Signing in to Google", enable "2-Step Verification"
3. Follow the setup process

### Step 2: Generate App Password
1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" from the app dropdown
3. Select "Windows Computer" (or your device)
4. Click "Generate"
5. Copy the 16-character password

### Step 3: Configure .env
```env
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
EMAIL_FROM=noreply@eduguard.com
```

---

## 💾 Database

### Models

**Student**
- Tracks student info (name, email, program)
- Stores ML risk assessment (score, status, confidence)
- Records email history (alert_count, last_alert_sent)

**EmailLog**
- Records every email sent
- Tracks status (Sent, Failed, Opened, Pending)
- Stores retry count and error messages
- Logs which week alert was sent

### SQLite (Default)
- Database file: `eduguard.db`
- Perfect for testing
- No setup required

### PostgreSQL (Production)
Update `.env`:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/eduguard
```

---

## 🎯 Frontend Components

### Updated AlertsPage.tsx

**Features:**
- ✅ Real-time data loading from backend
- ✅ Live statistics dashboard (Total, Opened, Sent, Failed)
- ✅ Pending alert queue with at-risk students
- ✅ Email notification log with search/filter
- ✅ Individual alert sending
- ✅ Bulk alert sending
- ✅ Retry failed emails
- ✅ Loading states and error handling
- ✅ Dark mode support (via ThemeContext)

**Data Flow:**
```
AlertsPage.tsx
    ↓
api/alerts.ts (API Service)
    ↓
Backend API (FastAPI)
    ↓
Database (SQLAlchemy)
```

### API Service (alerts.ts)

**Functions:**
- `fetchEmailLogs()` - Get email history
- `fetchAlertQueue()` - Get pending students
- `fetchAlertStats()` - Get statistics
- `sendAlertToStudent(id)` - Send individual alert
- `sendBulkAlerts(week)` - Send to all pending
- `retryFailedAlerts()` - Retry failed emails

---

## 📊 Email Templates

### Student Alert Email

Sends to at-risk students with:
- ✉️ Professional HTML formatting
- 📋 Clear call-to-action
- 📞 Support contact info
- 🎯 Personalized message
- 📱 Mobile-responsive design

**Template:** `email_service.py` → `build_student_alert_email()`

---

## 🔄 Workflow

### Individual Alert Flow
1. Educator clicks "Send Alert" button
2. Frontend calls `POST /alerts/send/{student_id}`
3. Backend:
   - ✅ Checks if student exists
   - ✅ Verifies email address
   - ✅ Checks for duplicates (not already sent this week)
   - ✅ Builds email template
   - ✅ Sends via SMTP
   - ✅ Logs in database
   - ✅ Updates student record
4. Frontend shows success/error toast
5. Alert queue refreshes

### Bulk Alert Flow
1. Educator clicks "Send Bulk Alerts"
2. Frontend calls `POST /alerts/send-bulk`
3. Backend:
   - ✅ Gets all HIGH/MEDIUM risk students
   - ✅ Filters out already-sent students
   - ✅ Sends email to each
   - ✅ Tracks successes/failures
   - ✅ Logs all in database
4. Returns summary (sent, failed, skipped)
5. Educator can retry failed emails

### Retry Failed Flow
1. If emails failed to send
2. Educator clicks "Retry" or calls `POST /alerts/retry-failed`
3. Backend:
   - ✅ Gets failed email logs
   - ✅ Attempts to resend (max 3 retries)
   - ✅ Updates status when successful
4. Returns count of resend attempts

---

## 🧪 Testing

### Add Test Student to Database

```python
from database import SessionLocal
from models import Student

db = SessionLocal()
student = Student(
    student_number="TEST001",
    first_name="John",
    last_name="Doe",
    email="your-email@gmail.com",  # Use your email for testing
    program="ICT724",
    attendance_rate=45.0,  # Low attendance
    gpa=2.1,               # Low GPA
    ml_score=0.87,         # High risk score
    risk_status="HIGH",
    confidence_score=0.95
)
db.add(student)
db.commit()
print(f"Created student with ID: {student.id}")
db.close()
```

### Send Test Alert

```bash
curl -X POST http://localhost:8000/alerts/send/1
```

Check your email for the alert!

---

## 📝 Project Structure

```
EduGuard/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── pages/
│   │   │   │   └── AlertsPage.tsx          (UPDATED)
│   │   │   ├── api/
│   │   │   │   └── alerts.ts               (NEW)
│   │   │   ├── context/
│   │   │   │   └── ThemeContext.tsx
│   │   │   ├── components/
│   │   │   └── data/
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── backend_aash_test/                      (NEW CLEAN BACKEND)
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── email_service.py
│   ├── alerts_routes.py
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── backend/                                 (Original - unchanged)
│   ├── main.py
│   ├── database.py
│   ├── routers/
│   └── requirements.txt
│
├── ALERTS_SETUP.md
└── README.md
```

---

## 🛠️ Key Technologies

### Frontend
- **React** 18.2 - UI Framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Lucide Icons** - Icons
- **Sonner** - Toast notifications

### Backend
- **FastAPI** - Web framework
- **SQLAlchemy** - ORM
- **SQLite/PostgreSQL** - Database
- **Python SMTP** - Email sending
- **Pydantic** - Data validation

### Email
- **Gmail SMTP** - Email delivery
- **MIMEMultipart** - Email formatting
- **HTML + Plain Text** - Dual format support

---

## 📋 Features Implemented

### Alert Management
- ✅ Get pending alert queue
- ✅ Send individual alerts
- ✅ Send bulk alerts
- ✅ Retry failed alerts
- ✅ Track email delivery status
- ✅ Prevent duplicate alerts (per week)
- ✅ Log all email activity

### Dashboard
- ✅ Real-time statistics
- ✅ Email history/logs
- ✅ Search & filter emails
- ✅ Pending alert queue
- ✅ Status indicators
- ✅ Action buttons

### Email Features
- ✅ Professional HTML templates
- ✅ Personalized messages
- ✅ SMTP integration
- ✅ Retry logic (up to 3 times)
- ✅ Error tracking
- ✅ Delivery logging

### Database
- ✅ Student model with risk assessment
- ✅ Email log with full tracking
- ✅ Timestamps for all events
- ✅ Duplicate prevention
- ✅ Status management

---

## 🚨 Error Handling

### Email Send Failures
- ❌ Student has no email → Skip with message
- ❌ SMTP connection fails → Logged and can retry
- ❌ Invalid email format → Logged with error message
- ❌ Max retries exceeded → Marked as permanently failed

### Duplicate Prevention
- ✅ Checks if alert already sent to student this week
- ✅ Skips in bulk operations
- ✅ Prevents email spam

### Validation
- ✅ Student must exist in database
- ✅ Email address must be valid
- ✅ Week number must be integer
- ✅ Risk status must be HIGH/MEDIUM

---

## 📱 Frontend Screens

### AlertsPage
```
┌────────────────────────────────────────┐
│ Alerts & Email Notifications           │
│ SMTP notification log · 45 emails sent │
│                            [Send Bulk] │
├────────────────────────────────────────┤
│ ┌─────────┬──────────┬────────┬──────┐ │
│ │ 45      │ 23       │ 15     │ 7    │ │
│ │ Sent    │ Opened   │ Await  │ Fail │ │
│ └─────────┴──────────┴────────┴──────┘ │
├────────────────────────────────────────┤
│ Pending Alert Queue          [8 students]
│ ┌─────────────────────────────────────┐ │
│ │ JD | Jane Doe       │ HIGH │[Send]  │ │
│ │ JS | John Smith     │ MEDIUM│[Send] │ │
│ └─────────────────────────────────────┘ │
├────────────────────────────────────────┤
│ Email Notification Log        [45 records]
│ [Search...] [Filter: All ▼]             │
│ ┌─────────────────────────────────────┐ │
│ │ Student  │ Subject │ Status │ Date  │ │
│ │ Jane Doe │ ICT724  │ Sent   │ 14:32 │ │
│ └─────────────────────────────────────┘ │
└────────────────────────────────────────┘
```

---

## 🐛 Troubleshooting

### Backend Won't Start
**Error:** `ModuleNotFoundError`
- ✅ **Solution:** Run `pip install -r requirements.txt`

**Error:** `No module named 'config'`
- ✅ **Solution:** Make sure you're in `backend_aash_test/` directory

### Email Not Sending
**Error:** SMTP authentication failed
- ✅ **Solution:** Verify Gmail app password in `.env`

**Error:** Connection refused
- ✅ **Solution:** Check internet connection, SMTP_HOST, SMTP_PORT

### Frontend Can't Connect to Backend
**Error:** CORS error in browser console
- ✅ **Solution:** Verify `ALLOWED_ORIGINS` in `.env` includes `http://localhost:5173`

**Error:** Network error
- ✅ **Solution:** Ensure backend is running on `http://localhost:8000`

### Database Issues
**Error:** `sqlite3.DatabaseError`
- ✅ **Solution:** Delete `eduguard.db` and restart - it will recreate

---

## 📚 Documentation Files

- **`ALERTS_SETUP.md`** - Detailed setup guide (main branch)
- **`backend_aash_test/README.md`** - Backend-specific setup
- **This file** - Overview and integration guide

---

## ✅ Checklist

### Before Testing
- [ ] Python 3.8+ installed
- [ ] Node.js/npm installed
- [ ] Gmail account with app password
- [ ] `.env` configured with Gmail credentials
- [ ] Database initialized (auto-created)

### First Time Setup
- [ ] Clone repository
- [ ] Switch to `backend-aash-test` branch
- [ ] Setup backend virtual environment
- [ ] Install backend dependencies
- [ ] Configure `.env` file
- [ ] Start backend server
- [ ] Verify backend docs at `/docs`
- [ ] Setup frontend
- [ ] Install frontend dependencies
- [ ] Start frontend dev server
- [ ] Access http://localhost:5173

### Testing
- [ ] Add test student to database
- [ ] Send individual alert
- [ ] Check email received
- [ ] View logs in frontend
- [ ] Test bulk send
- [ ] Test retry failed
- [ ] Test search & filter

---

## 🎯 Next Steps

1. **Set up Gmail credentials**
   - Follow the Gmail setup section above
   - Test sending a single email first

2. **Import student data**
   - Use provided Python script to add students from Excel
   - Or manually add test students

3. **Configure production settings**
   - Update `.env` for production
   - Switch to PostgreSQL database
   - Set up scheduled jobs (if needed)

4. **Monitor delivery**
   - View email logs in dashboard
   - Track open rates
   - Retry failed emails

---

## 📞 Support

For issues or questions:
1. Check error messages in backend logs
2. Review browser console for frontend errors
3. Check `.env` configuration
4. Verify SMTP credentials
5. Test database connection

---

## 📄 License

Part of the EduGuard project - Automated at-risk student detection and monitoring system.

---

**Version:** 1.0.0  
**Last Updated:** 2025-01-15  
**Status:** ✅ Production Ready
