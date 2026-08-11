from database import get_connection


def build_student_features(
    student_id: int,
    subject_code: str,
) -> dict[str, float]:
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

       
        # 1. Get latest attendance percentage and Moodle login count
   
        cursor.execute(
            """
            SELECT
                ATTENDANCE_PERCENTAGE,
                MOODLE_LOGIN_COUNT
            FROM ATTENDANCE
            WHERE STUDENT_ID = %s
              AND SUBJECT_CODE = %s
            ORDER BY WEEK DESC
            LIMIT 1;
            """,
            (student_id, subject_code),
        )

        attendance_row = cursor.fetchone()
       
        if attendance_row:
            attendance_pct = float(
                attendance_row["attendance_percentage"] or 0
            )

            moodle_login_count = float(
                attendance_row["moodle_login_count"] or 0
            )
        else:
            attendance_pct = 0.0
            moodle_login_count = 0.0

        # get attendance history for trend calculation
        cursor.execute(
            """
            SELECT
                WEEK,
                ATTENDANCE_PERCENTAGE
            FROM ATTENDANCE
            WHERE STUDENT_ID = %s
              AND SUBJECT_CODE = %s
            ORDER BY WEEK;
            """,
            (student_id, subject_code),
        )

        attendance_history = cursor.fetchall()

        print("Attendance history:", attendance_history)

    
        # 2. Calculate average assessment percentage
      
        cursor.execute(
            """
            SELECT
                AVG(
                    (SA.SCORE / NULLIF(A.MAX_SCORE, 0)) * 100
                ) AS ASSESSMENT_AVG_PCT
            FROM STUDENT_ASSESSMENT SA
            JOIN ASSESSMENT A
                ON A.ASSESSMENT_ID = SA.ASSESSMENT_ID
            WHERE SA.STUDENT_ID = %s
              AND A.SUBJECT_CODE = %s
              AND SA.SCORE IS NOT NULL;
            """,
            (student_id, subject_code),
        )

        assessment_row = cursor.fetchone()

        assessment_avg_pct = float(
            assessment_row["assessment_avg_pct"] or 0
        )

        # Calculate attendance trend

        # Tutorial records
        # ---------------------------------------------------------
        cursor.execute(
            """
            SELECT
                A.DUE_WEEK,
                SA.IS_SUBMITTED,
                SA.SCORE,
                A.MAX_SCORE
            FROM STUDENT_ASSESSMENT SA
            JOIN ASSESSMENT A
                ON A.ASSESSMENT_ID = SA.ASSESSMENT_ID
            WHERE SA.STUDENT_ID = %s
            AND A.SUBJECT_CODE = %s
            AND UPPER(A.ASSESSMENT_TYPE) = 'TUTORIAL'
            ORDER BY A.DUE_WEEK;
            """,
            (student_id, subject_code),
        )

        tutorial_history = cursor.fetchall()

        print("Tutorial history:", tutorial_history)

        
        
        if len(attendance_history) >= 6:
                early_values = [
                    float(row["attendance_percentage"])
                    for row in attendance_history[:3]
                    if row["attendance_percentage"] is not None
                ]

                recent_values = [
                    float(row["attendance_percentage"])
                    for row in attendance_history[-3:]
                    if row["attendance_percentage"] is not None
                ]

                if early_values and recent_values:
                    early_average = sum(early_values) / len(early_values)
                    recent_average = sum(recent_values) / len(recent_values)

                    attendance_trend = round(recent_average - early_average, 2)
                else:
                    attendance_trend = 0.0

        elif len(attendance_history) >= 2:
                first_value = float(
                    attendance_history[0]["attendance_percentage"]
                )

                last_value = float(
                    attendance_history[-1]["attendance_percentage"]
                )

                attendance_trend = round(last_value - first_value, 2)

        else:
                attendance_trend = 0.0

        #calculate tutorial completion percentage and trend
        total_tutorials = len(tutorial_history)

        submitted = sum(
            1
            for row in tutorial_history
            if row["is_submitted"]
        )

        if total_tutorials > 0:
            tut_completion_pct = (
                submitted / total_tutorials
            ) * 100
        else:
            tut_completion_pct = 0.0

        #calculate tutorial completion percentage and trend
        if len(tutorial_history) >= 2:

            first = (
                float(tutorial_history[0]["score"])
                / float(tutorial_history[0]["max_score"])
            ) * 100

            last = (
                float(tutorial_history[-1]["score"])
                / float(tutorial_history[-1]["max_score"])
            ) * 100

            tut_trend = round(last - first, 2)

        else:
            tut_trend = 0.0

        # 4. Return the exact six features expected by the model

        return {
            "moodle_login_count": moodle_login_count,
            "attendance_pct": attendance_pct,
            "attendance_trend": attendance_trend,
            "tut_completion_pct": tut_completion_pct,
            "tut_trend": tut_trend,
            "assessment_avg_pct": assessment_avg_pct,
            
            
        }

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()