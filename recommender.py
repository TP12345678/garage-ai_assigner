import pandas as pd
import numpy as np
import sqlite3
from sklearn.metrics.pairwise import cosine_similarity


job_data_path = "data/generated_flat_job_history_FINAL.xlsx"
df_jobs = pd.read_excel(job_data_path)

# --- Feature engineering ---
df_jobs['Job_Duration_Deviation'] = df_jobs['Time_Taken_minutes'] - df_jobs['Estimated_Standard_Time']
df_jobs['Engineer_Efficiency'] = df_jobs['Outcome_Score'] / df_jobs['Time_Taken_minutes']

urgency_map = {'Low': 1, 'Normal': 2, 'High': 3}
df_jobs['Urgency_Level'] = df_jobs['Urgency'].map(urgency_map)
df_jobs['Time_Pressure_Score'] = df_jobs['Urgency_Level'] * df_jobs['Job_Duration_Deviation']


engineer_task_features = df_jobs.groupby(['Assigned_Engineer_Id', 'Task_Id']).agg({
    'Outcome_Score': 'mean',
    'Engineer_Efficiency': 'mean',
    'Time_Pressure_Score': 'mean',
    'Urgency_Level': 'mean'
}).reset_index()

feature_cols = ['Outcome_Score', 'Engineer_Efficiency', 'Time_Pressure_Score', 'Urgency_Level']
engineer_task_matrix = engineer_task_features.set_index(['Task_Id', 'Assigned_Engineer_Id'])[feature_cols]
task_profiles = engineer_task_matrix.groupby('Task_Id').mean()


DB_PATH = "database/workshopnew.db"

def get_available_engineers_from_db():
    """Fetch available engineer IDs from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("SELECT Engineer_Id FROM engineer_profiles WHERE Availability = 'Yes'")
    available_engs = {row[0] for row in cursor.fetchall()}
    conn.close()
    return available_engs

def get_top_similar_tasks(task_id, top_k=3):
    """Return top-k most similar task IDs to the given task ID."""
    if task_id not in task_profiles.index:
        return [], []

    task_vector = task_profiles.loc[task_id].values.reshape(1, -1)
    similarities = cosine_similarity(task_vector, task_profiles)[0]

    similar_task_df = pd.DataFrame({
        'task_id': task_profiles.index,
        'similarity': similarities
    })

    similar_task_df = similar_task_df[similar_task_df['task_id'] != task_id]
    similar_task_df = similar_task_df.sort_values(by='similarity', ascending=False).head(top_k)

    return similar_task_df['task_id'].tolist(), similar_task_df['similarity'].round(2).tolist()

def recommend_engineers_memory_cf(task_id, top_n=5):

    if task_id not in task_profiles.index:
        return f"Task '{task_id}' not found in profiles."

    task_vector = task_profiles.loc[task_id].values.reshape(1, -1)

    try:
        engineers_for_task = engineer_task_matrix.loc[task_id]
    except KeyError:
        return f"No engineers found for task '{task_id}'."

    engineer_vectors = engineers_for_task.values
    engineer_ids = engineers_for_task.index.tolist()

    similarities = cosine_similarity(engineer_vectors, task_vector).flatten()
    top_indices = np.argsort(similarities)[::-1]


    full_recommendations = [(engineer_ids[i], round(similarities[i], 4)) for i in top_indices[:top_n]]


    available_engineers = get_available_engineers_from_db()


    filtered_recommendations = [
        (eng_id, sim_score) for eng_id, sim_score in full_recommendations
        if eng_id in available_engineers
    ]

    similar_tasks, similar_scores = get_top_similar_tasks(task_id, top_k=3)

    if filtered_recommendations:
        eng_list = ', '.join([str(eng) for eng, _ in filtered_recommendations])
        task_list = ', '.join(similar_tasks)
        score_list = ', '.join(map(str, similar_scores))
        reason = (
            f"Engineers {eng_list} are recommended because they performed well on tasks similar to {task_id} "
            f"— such as {task_list} — with similarity scores of {score_list}."
        )
        return filtered_recommendations, reason
    else:
        return [], f"No available engineers found for task {task_id}."
