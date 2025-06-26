import sqlite3
import pandas as pd
from recommender import recommend_engineers_memory_cf

DB_PATH = "database/workshop.db"

def get_connection():
    return sqlite3.connect(DB_PATH)


def fetch_all_jobs():
    with get_connection() as conn:
        return pd.read_sql("SELECT * FROM job_card", conn)


def fetch_unassigned_jobs():
    with get_connection() as conn:
        return pd.read_sql("SELECT * FROM job_card WHERE Assigned_Engineer_ID IS NULL", conn)


def update_job_assignment(job_card_id, engineer_id):
    with get_connection() as conn:
        conn.execute("""
            UPDATE job_card 
            SET Assigned_Engineer_ID = ?, Status = 'Assigned' 
            WHERE Job_Card_ID = ?
        """, (engineer_id, job_card_id))
        conn.commit()
        print(f"Assigned Engineer {engineer_id} to Job {job_card_id}")


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


def get_task_id_for_job(job_card_id):
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT Task_ID FROM job_card WHERE Job_Card_ID = ?", (job_card_id,))
        row = cursor.fetchone()
        return row[0] if row else None


def assign_engineers_to_pending_jobs():
    jobs = fetch_unassigned_jobs()

    for _, row in jobs.iterrows():
        job_id = row["Job_Card_ID"]
        task_id = row["Task_ID"]

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


def complete_job(job_card_id, outcome_score):
    with get_connection() as conn:
        conn.execute(
            "UPDATE job_card SET Status = 'Completed', Outcome_Score = ? WHERE Job_Card_ID = ?",
            (outcome_score, job_card_id)
        )
        conn.commit()

        eng_id = conn.execute(
            "SELECT Assigned_Engineer_ID FROM job_card WHERE Job_Card_ID = ?", (job_card_id,)
        ).fetchone()
        
        if eng_id and eng_id[0]:
            mark_engineer_available(eng_id[0])
        print(f"Job {job_card_id} marked completed with score {outcome_score}")

def update_task_assignment(task_id, engineer_id):
    with get_connection() as conn:
        conn.execute("""
            UPDATE job_task_mapping
            SET Assigned_Engineer_ID = ?, Status = 'Assigned'
            WHERE Task_ID = ?
        """, (engineer_id, task_id))
        conn.commit()
        print(f"Engineer {engineer_id} assigned to Task {task_id}")


