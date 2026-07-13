from fastapi import APIRouter, HTTPException

from database import get_connection

router = APIRouter(
    prefix="/students",
    tags=["Students"],
)


@router.get("/")
def get_students():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                S.STUDENT_ID,
                S.FIRST_NAME,
                S.LAST_NAME,
                S.AGE,
                S.GENDER,
                S.STATUS_ID,
                S.IS_EMAILED
            FROM STUDENT S
            ORDER BY S.STUDENT_ID;
        """)

        return cursor.fetchall()

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