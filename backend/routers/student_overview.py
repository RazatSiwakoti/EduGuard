from fastapi import APIRouter, HTTPException

from database import get_connection

router = APIRouter(
    prefix="/student-overview",
    tags=["Student Overview"],
)


@router.get("/")
def get_student_overview():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                S.STUDENT_ID AS ID,
                S.FIRST_NAME || ' ' || S.LAST_NAME AS NAME,
                LEFT(S.FIRST_NAME, 1) || LEFT(S.LAST_NAME, 1) AS INITIALS,
                S.STUDENT_ID::TEXT AS STUDENT_ID,
                G.SUBJECT_CODE AS SUBJECT,
                COALESCE(A.ATTENDANCE_PERCENTAGE, 0) AS ATTENDANCE,
                COALESCE(G.CURRENT_GPA, 0) AS GPA,
                COALESCE(P.ML_SCORE, 0) AS ML_SCORE,
                COALESCE(P.CONFIDENCE, 0) AS CONFIDENCE,
                COALESCE(P.RISK_LEVEL, 'LOW') AS RISK,
                LOWER(COALESCE(P.TREND, 'STABLE')) AS TREND
            FROM STUDENT S
            LEFT JOIN GRADES G
                ON G.STUDENT_ID = S.STUDENT_ID
            LEFT JOIN ATTENDANCE A
                ON A.STUDENT_ID = S.STUDENT_ID
                AND A.SUBJECT_CODE = G.SUBJECT_CODE
                AND A.WEEK = G.WEEK
            LEFT JOIN STUDENT_RISK_PREDICTION P
                ON P.STUDENT_ID = S.STUDENT_ID
                AND P.SUBJECT_CODE = G.SUBJECT_CODE
                AND P.WEEK = G.WEEK
            ORDER BY
                P.ML_SCORE DESC NULLS LAST,
                S.STUDENT_ID;
        """)

        rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "name": row["name"],
                "initials": row["initials"],
                "studentId": row["student_id"],
                "subject": row["subject"],
                "attendance": float(row["attendance"]),
                "gpa": float(row["gpa"]),
                "mlScore": float(row["ml_score"]),
                "confidence": float(row["confidence"]),
                "risk": row["risk"],
                "trend": row["trend"],
            }
            for row in rows
        ]

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {error}",
        )

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()