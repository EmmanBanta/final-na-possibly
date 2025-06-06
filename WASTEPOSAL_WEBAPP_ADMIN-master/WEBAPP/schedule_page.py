from flask import Blueprint, request, jsonify
from firebase_admin import db

schedule_page = Blueprint('schedule_page', __name__)

@schedule_page.route('/api/locations')
def get_locations():
    city = request.args.get('city')
    barangay = request.args.get('barangay')
    if not city or not barangay:
        return jsonify({"error": "City and barangay required"}), 400

    ref = db.reference(f"{city}/{barangay}/Areas")
    data = ref.get() or {}

    areas = list(data.keys()) if isinstance(data, dict) else []
    return jsonify(areas)

@schedule_page.route('/api/schedule/<city>/<barangay>/<location>', methods=['POST'])
def set_schedule(city, barangay, location):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    formatted_schedule = {}
    for day, schedule in data.items():
        formatted_schedule[day] = {
            "from": schedule.get("from", ""),
            "to": schedule.get("to", ""),
            "status": "scheduled"
        }

    ref_path = f"{city}/{barangay}/Areas/{location}"
    try:
        ref = db.reference(ref_path)
        ref.set(formatted_schedule)
        return jsonify({"status": "success", "message": f"Schedule saved for {location}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@schedule_page.route('/api/schedule/<city>/<barangay>/<location>', methods=['GET'])
def get_schedule(city, barangay, location):
    ref = db.reference(f"{city}/{barangay}/Areas/{location}")
    try:
        schedule = ref.get()
        if not schedule:
            return jsonify({"error": "No schedule found"}), 404
        return jsonify(schedule)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@schedule_page.route('/api/schedule/<city>/<barangay>/<location>', methods=['DELETE'])
def delete_schedule(city, barangay, location):
    ref = db.reference(f"{city}/{barangay}/Areas/{location}")
    try:
        if ref.get() is None:
            return jsonify({"error": "Schedule not found"}), 404
        ref.delete()
        return jsonify({"status": "success", "message": f"Schedule deleted for {location}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
