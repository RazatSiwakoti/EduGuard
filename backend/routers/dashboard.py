from fastapi import APIRouter, HTTPException

from database import get_connection

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get("/")
def get_dashboard_summary():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM STUDENT) AS TOTAL_STUDENTS,

                (
                    SELECT COUNT(*)
                    FROM STUDENT S
                    JOIN STATUS ST
                        ON ST.STATUS_ID = S.STATUS_ID
                    WHERE UPPER(ST.STATUS_DESCRIPTION) IN ('HIGH', 'MEDIUM')
                ) AS AT_RISK_STUDENTS,

                (
                    SELECT COUNT(*)
                    FROM EMAIL_LOG
                ) AS ALERTS_DISPATCHED;
        """)

        summary = cursor.fetchone()

        return {
            "total_students": summary["total_students"],
            "at_risk_students": summary["at_risk_students"],
            "alerts_dispatched": summary["alerts_dispatched"],

            # Temporary until the ML pipeline provides this dynamically.
            "model_accuracy": 74.0,
        }

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