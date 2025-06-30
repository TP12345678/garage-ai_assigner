from flask import Flask, request, jsonify
from flask_cors import CORS
from recommender import recommend_engineers_memory_cf
import job_manager

app = Flask(__name__)
CORS(app)


@app.route('/jobs', methods=['GET'])
def get_jobs():
    jobs_df = job_manager.fetch_all_jobs()
    jobs = jobs_df.to_dict(orient='records')
    return jsonify(jobs)


@app.route('/jobs/unassigned', methods=['GET'])
def get_unassigned_jobs():
    jobs_df = job_manager.fetch_unassigned_jobs()
    jobs = jobs_df.to_dict(orient='records')
    return jsonify(jobs)


@app.route('/engineers/available', methods=['GET'])
def get_available_engineers():
    eng_df = job_manager.fetch_available_engineers()
    engineers = eng_df.to_dict(orient='records')
    return jsonify(engineers)


@app.route('/tasks/assign', methods=['POST'])
def assign_engineer_to_task():
    data = request.get_json()
    task_id = data.get('task_id')

    if not task_id:
        return jsonify({"error": "Missing task_id"}), 400

    recommendations, reason = recommend_engineers_memory_cf(task_id, top_n=5)
    if isinstance(recommendations, str):
        return jsonify({"error": recommendations}), 400

    assigned_engineer = None
    for eng_id, score in recommendations:
        if job_manager.check_availability(eng_id):
            assigned_engineer = eng_id
            break

    if not assigned_engineer:
        return jsonify({"error": "No available engineer found"}), 409

    job_manager.update_task_assignment(task_id, assigned_engineer)
    job_manager.mark_engineer_unavailable(assigned_engineer)

    return jsonify({
        "message": f"Engineer {assigned_engineer} assigned to task {task_id}",
        "recommendation_reason": reason
    }), 200


@app.route('/tasks/complete', methods=['POST'])
def complete_task_endpoint():
    data = request.get_json()
    task_id = data.get('task_id')
    outcome_score = data.get('outcome_score')

    if not task_id or outcome_score is None:
        return jsonify({"error": "Missing task_id or outcome_score"}), 400

    try:
        job_manager.complete_task(task_id, outcome_score)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"message": f"Task {task_id} marked as completed with score {outcome_score}"}), 200


if __name__ == "__main__":
    app.run(debug=True)
