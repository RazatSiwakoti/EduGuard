from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import student_overview, students, dashboard

app = FastAPI(title="InRisk API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(students.router)
app.include_router(student_overview.router)
app.include_router(dashboard.router)


@app.get("/")
def root():
    return {"message": "InRisk API is running"}