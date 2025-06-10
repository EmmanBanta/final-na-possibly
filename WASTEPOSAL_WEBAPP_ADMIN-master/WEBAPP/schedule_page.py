from flask import Blueprint, request, jsonify
from firebase_admin import db
import re

schedule_page = Blueprint('schedule_page', __name__)

def normalize_location(name):
    return re.sub(r'\s+', ' ', name.replace('-', ' ').replace('_', ' ')).strip().lower()

@schedule_page.route('/api/locations')
def get_locations():
    city = request.args.get('city')
    barangay = request.args.get('barangay')
    if not city or not barangay:
        return jsonify({"error": "City and barangay required"}), 400

    try:
        ref = db.reference(f"{city}/{barangay}/Areas")
        data = ref.get() or {}
        areas = list(data.keys()) if isinstance(data, dict) else []
        return jsonify(areas)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@schedule_page.route('/api/schedule/<city>/<barangay>/<location>', methods=['POST'])
def set_schedule(city, barangay, location):
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid schedule data"}), 400

    location = normalize_location(location)

    formatted_schedule = {}
    for day, value in data.items():
        if isinstance(value, dict) and 'from' in value and 'to' in value:
            formatted_schedule[day] = {
                "from": value.get("from", ""),
                "to": value.get("to", ""),
                "status": "scheduled"
            }

    if not formatted_schedule:
        return jsonify({"error": "No valid schedule entries provided"}), 400

    ref_path = f"{city}/{barangay}/Areas/{location}"
    try:
        ref = db.reference(ref_path)
        ref.set(formatted_schedule)
        return jsonify({"status": "success", "message": f"Schedule saved for {location}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@schedule_page.route('/api/schedule/<city>/<barangay>/<location>', methods=['GET'])
def get_schedule(city, barangay, location):
    location = normalize_location(location)
    ref = db.reference(f"{city}/{barangay}/Areas/{location}")
    try:
        schedule = ref.get()
        if not schedule:
            return jsonify({}) 
        return jsonify(schedule), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@schedule_page.route('/api/schedule/<city>/<barangay>/<location>', methods=['DELETE'])
def delete_schedule(city, barangay, location):
    location = normalize_location(location)
    ref = db.reference(f"{city}/{barangay}/Areas/{location}")
    try:
        if ref.get() is None:
            return jsonify({"error": "Schedule not found"}), 404
        ref.delete()
        return jsonify({"status": "success", "message": f"Schedule deleted for {location}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
