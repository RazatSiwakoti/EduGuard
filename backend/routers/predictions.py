from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel, Field
from ML.feature_builder import build_student_features
from ML.predictor import predict_risk
from database import get_connection


router = APIRouter(
    prefix="/predictions",
    tags=["Predictions"],
)


# class PredictionInput(BaseModel):
#     moodle_login_count: float = Field(ge=0)
#     attendance_pct: float = Field(ge=0, le=100)
#     attendance_trend: float
#     tut_completion_pct: float = Field(ge=0, le=100)
#     tut_trend: float
#     assessment_avg_pct: float = Field(ge=0, le=100)


@router.post("/student/{student_id}")
def predict_student(
    student_id: int,
    subject_code: str,
):
    connection = None
    cursor = None

    try:
        # 1. Build real ML features from PostgreSQL
        # ---------------------------------------------------------
        features = build_student_features(
            student_id=student_id,
            subject_code=subject_code,
        )

       
        # 2. Run XGBoost prediction
        # ---------------------------------------------------------
        result = predict_risk(features)

        prediction_label = result["prediction"]
        confidence = result["confidence"]
        probabilities = result["probabilities"]

        
        # 3. Translate ML labels into EduGuard risk levels
        # ---------------------------------------------------------
        risk_mapping = {
            "high_risk": "HIGH",
            "low_risk": "MEDIUM",
            "safe": "LOW",
        }

        risk_level = risk_mapping[prediction_label]

        # Continuous ML risk score:
        # probability that the student belongs to high_risk
        ml_score = probabilities["high_risk"]

        # Existing database stores confidence as percentage
        confidence_pct = confidence * 100

       
        # 4. Determine simple trend
        # ---------------------------------------------------------
        attendance_trend = features["attendance_trend"]

        if attendance_trend <= -5:
            trend = "DETERIORATING"
        elif attendance_trend >= 5:
            trend = "IMPROVING"
        else:
            trend = "STABLE"

        
        # 5. Open DB connection
        # ---------------------------------------------------------
        connection = get_connection()
        cursor = connection.cursor()

        # Find latest academic week for this student/subject
        cursor.execute(
            """
            SELECT COALESCE(MAX(WEEK), 1) AS CURRENT_WEEK
            FROM ATTENDANCE
            WHERE STUDENT_ID = %s
              AND SUBJECT_CODE = %s;
            """,
            (student_id, subject_code),
        )

        week_row = cursor.fetchone()
        current_week = int(
            week_row["current_week"] or 1
        )

        
        # 6. Update existing prediction first
        # ---------------------------------------------------------
        cursor.execute(
            """
            UPDATE STUDENT_RISK_PREDICTION
            SET
                RISK_LEVEL = %s,
                ML_SCORE = %s,
                CONFIDENCE = %s,
                TREND = %s
            WHERE STUDENT_ID = %s
              AND SUBJECT_CODE = %s
              AND WEEK = %s;
            """,
            (
                risk_level,
                ml_score,
                confidence_pct,
                trend,
                student_id,
                subject_code,
                current_week,
            ),
        )

       
        # 7. If nothing existed, insert a new prediction
        # ---------------------------------------------------------
        if cursor.rowcount == 0:
            cursor.execute(
                """
                INSERT INTO STUDENT_RISK_PREDICTION (
                    STUDENT_ID,
                    SUBJECT_CODE,
                    WEEK,
                    RISK_LEVEL,
                    ML_SCORE,
                    CONFIDENCE,
                    TREND
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    student_id,
                    subject_code,
                    current_week,
                    risk_level,
                    ml_score,
                    confidence_pct,
                    trend,
                ),
            )

        connection.commit()

        
        # 8. Return useful response
        # ---------------------------------------------------------
        return {
            "student_id": student_id,
            "subject_code": subject_code,
            "week": current_week,
            "features": features,
            "prediction": {
                **result,
                "risk_level": risk_level,
                "ml_score": ml_score,
                "confidence_percent": confidence_pct,
                "trend": trend,
            },
            "saved": True,
        }

    except Exception as error:
        if connection:
            connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Prediction error: {error}",
        )

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()