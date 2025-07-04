import sqlite3
import pandas as pd
from recommender import recommend_engineers_memory_cf

# ✅ Correct path to your updated database
DB_PATH = "database/workshopnew.db"  


def get_connection():
    print(f"Connecting to DB at: {DB_PATH}")
    return sqlite3.connect(DB_PATH)


def fetch_all_jobs():
    with get_connection() as conn:
        return pd.read_sql("SELECT * FROM job_card", conn)


def fetch_unassigned_jobs():
    with get_connection() as conn:
        return pd.read_sql("SELECT * FROM job_card WHERE Engineer_Id IS NULL", conn)


def update_job_assignment(job_id, engineer_id):
    with get_connection() as conn:

        conn.execute("""
            UPDATE job_card 
            SET Engineer_Id = ?, Status = 'Assigned' 
            WHERE Job_Id = ?
        """, (engineer_id, job_id))
        conn.commit()
        print(f"Assigned Engineer {engineer_id} to Job {job_id}")


def fetch_available_engineers():
    with get_connection() as conn:
        return pd.read_sql("SELECT * FROM engineer_profiles WHERE Availability = 'Yes'", conn)


def check_availability(engineer_id):
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT Availability FROM engineer_profiles WHERE Engineer_ID = ?", (engineer_id,))
        row = cursor.fetchone()
        return row and row[0] == 'Yes'


def mark_engineer_unavailable(engineer_id):
    with get_connection() as conn:
        conn.execute(
            "UPDATE engineer_profiles SET Availability = 'No' WHERE Engineer_ID = ?", (engineer_id,))
        conn.commit()
        print(f"Engineer {engineer_id} marked as unavailable")


def mark_engineer_available(engineer_id):
    with get_connection() as conn:
        conn.execute(
            "UPDATE engineer_profiles SET Availability = 'Yes' WHERE Engineer_ID = ?", (engineer_id,))
        conn.commit()
        print(f"Engineer {engineer_id} marked as available")


def get_task_id_for_job(job_id):
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT Task_Id FROM job_card WHERE Job_Id = ?", (job_id,))
        row = cursor.fetchone()
        return row[0] if row else None


def assign_engineers_to_pending_jobs():
    jobs = fetch_unassigned_jobs()

    for _, row in jobs.iterrows():
        job_id = row["Job_Id"]
        task_id = row["Task_Id"]

        print(f"\nAssigning job: {job_id} with task: {task_id}")

        recommendations, reason = recommend_engineers_memory_cf(task_id, top_n=5)

        if isinstance(recommendations, str):
            print(f"{recommendations}")
            continue

        assigned_engineer = None

        for eng_id, score in recommendations:
            if check_availability(eng_id):
                assigned_engineer = eng_id
                break

        if assigned_engineer:
            update_job_assignment(job_id, assigned_engineer)
            mark_engineer_unavailable(assigned_engineer)
        else:
            print(f"[No available engineer for job {job_id}]")


def complete_task(task_id, outcome_score):
    with get_connection() as conn:
        conn.execute("""
            UPDATE job_card
            SET Status = 'Completed', Outcome_Score = ?
            WHERE Task_Id = ? AND Engineer_Id IS NOT NULL
        """, (outcome_score, task_id))
        conn.commit()

        eng_id = conn.execute("""
            SELECT Engineer_Id FROM job_card WHERE Task_Id = ?
        """, (task_id,)).fetchone()

        if eng_id and eng_id[0]:
            mark_engineer_available(eng_id[0])
        print(f"Task {task_id} marked completed with score {outcome_score}")


def update_task_assignment(task_id, engineer_id):
    with get_connection() as conn:
        conn.execute("""
            UPDATE job_card
            SET Engineer_Id = ?, Status = 'Assigned'
            WHERE Task_Id = ? AND Engineer_Id IS NULL
        """, (engineer_id, task_id))
        conn.commit()
        print(f"Engineer {engineer_id} assigned to Task {task_id}")
