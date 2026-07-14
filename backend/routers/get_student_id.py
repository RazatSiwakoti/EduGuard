from fastapi import APIRouter, HTTPException

from database import get_connection

router = APIRouter(
    prefix="/student_individual",
    tags=["Student Individual"],
)


@router.get("/{student_id}")
def get_student(student_id: int):
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
                S.EMAIL,
                S.PHONE,
                S.PROGRAM,
                S.STUDENT_NUMBER,
                S.IS_EMAILED,
                ST.STATUS_DESCRIPTION
            FROM STUDENT S
            LEFT JOIN STATUS ST
                ON ST.STATUS_ID = S.STATUS_ID
            WHERE S.STUDENT_ID = %s;
        """, (student_id,))

        student = cursor.fetchone()

        if student is None:
            raise HTTPException(
                status_code=404,
                detail="Student not found."
            )

        return student

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {error}"
        )

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()