# EduGuard
Automated at-risk student detection and monitoring system built for KOI.

## Tech Stack
- **Frontend:** React + TailwindCSS
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL
- **ML Engine:** scikit-learn, XGBoost, SHAP
- **Auth:** JWT

## Project Structure
backend/    → FastAPI application
frontend/   → React application  
docs/       → Architecture and API documentation
scripts/    → Database and setup scripts

## Getting Started
1. Clone the repo
2. Copy .env.example to .env and fill in your values
3. See docs/ for backend and frontend setup instructions

## Branching Strategy
- main      → production-ready only
- develop   → integration branch
- feature/* → individual features