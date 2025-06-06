from flask import Blueprint, request, render_template, jsonify
from firebase_admin import db
import datetime

complaints = Blueprint('complaints', __name__)

@complaints.route('/submit_complaint', methods=['POST'])
def submit_complaint():
    data = request.get_json()
    from_user_id = data.get('from_user_id')
    message = data.get('message')

    if not from_user_id or not message:
        return jsonify({"status": "error", "message": "Missing fields"}), 400

    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    complaint_id = f"{from_user_id}-{int(datetime.datetime.now().timestamp())}"

    complaint_data = {
        "from_user_id": from_user_id,
        "message": message,
        "complaint_status": "pending",
        "response": {},
        "address": data.get("address", "Unknown"),
        "timestamp": timestamp,
        "userId": from_user_id
    }

    db.reference(f"/Makati/Magallanes/complaints/{from_user_id}/{complaint_id}").set(complaint_data)
    return jsonify({"status": "success", "message": "Complaint submitted"})


@complaints.route('/complaints')
def complaints_page():
    complaints_ref = db.reference('/Makati/Magallanes/complaints')
    user_ref = db.reference('/Makati/Magallanes/User')

    nested_complaints = complaints_ref.get() or {}
    user_data = user_ref.get() or {}

    complaint_counts = {}
    enriched_complaints = {}

    for user_id, user_complaints in nested_complaints.items():
        if not isinstance(user_complaints, dict):
            continue
        for cid, complaint in user_complaints.items():
            if not isinstance(complaint, dict):
                continue

            uid = complaint.get("userId") or complaint.get("user_id") or user_id
            user_info = user_data.get(uid, {})
            complaint_counts[uid] = complaint_counts.get(uid, 0) + 1
            display_id = f"{uid}-{complaint_counts[uid]}"

            enriched_complaints[f"{uid}/{cid}"] = {
                **complaint,
                "address": complaint.get("address", user_info.get("address", "Unknown")),
                "complaint_display_id": display_id,
                "user_id": uid,
                "complaint_id": cid
            }

    enriched_complaints = dict(sorted(
        enriched_complaints.items(),
        key=lambda item: item[1].get('timestamp', ''),
        reverse=True
    ))

    return render_template(
        'complaints.html',
        complaints=enriched_complaints,
        city="Makati",
        barangay="Magallanes"
    )


@complaints.route('/submit_admin_response', methods=['POST'])
def submit_admin_response():
    try:
        data = request.form
        message = data.get("message", "").strip()
        complaint_identifier = data.get("complaint_id", "").strip()
        new_status = data.get("new_status", "").lower().strip()

        if not all([message, complaint_identifier, new_status]):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        if "-" in complaint_identifier:
            if "/" in complaint_identifier:
                user_id, complaint_id = complaint_identifier.split("/", 1)
            else:
                parts = complaint_identifier.split("-")
                if len(parts) == 4:
                    user_id = f"{parts[1]}-{parts[2]}"
                    complaint_id = f"{user_id}-{parts[3]}"  
                else:
                    return jsonify({
                        "status": "error",
                        "message": f"Invalid complaint ID format: {complaint_identifier}"
                    }), 400
        else:
            return jsonify({
                "status": "error",
                "message": "Complaint ID must contain hyphens"
            }), 400

        complaint_ref = db.reference(f"Makati/Magallanes/complaints/{user_id}/{complaint_id}")
        
        if not complaint_ref.get():
            return jsonify({
                "status": "error",
                "message": f"Complaint not found at: complaints/{user_id}/{complaint_id}",
                "suggested_path": f"{user_id}/{complaint_id}"
            }), 404

        updates = {
            "complaint_status": new_status,
            "response": {
                f"{new_status}message_response": {
                    "message": message,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "admin_id": "admin"
                }
            }
        }
        
        complaint_ref.update(updates)
        return jsonify({
            "status": "success",
            "message": "Response saved",
            "path": f"{user_id}/{complaint_id}"
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }), 500


@complaints.route('/respond_to_complaint/<user_id>/<complaint_id>', methods=['POST'])
def respond_to_complaint(user_id, complaint_id):
    response_text = request.form.get('response_text')
    targets = request.form.getlist('targets') or []

    if not response_text:
        return jsonify({"status": "error", "message": "Response is required"}), 400

    db.reference(f'Makati/Magallanes/complaints/{user_id}/{complaint_id}').update({
        'admin_response': response_text,
        'announcement_targets': targets
    })

    return jsonify({"status": "success", "message": "Response and targets saved"})


@complaints.route('/send_admin_response/<user_id>/<complaint_id>', methods=['POST'])
def send_admin_response(user_id, complaint_id):
    message = request.form.get('response_message')
    target = request.form.get('announcement_target')

    if not message:
        return jsonify({'status': 'error', 'message': 'Response message required'}), 400

    response_payload = {
        'response_message': message,
        'announcement_target': target,
        'response_timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    db.reference(f'/Makati/Magallanes/complaints/{user_id}/{complaint_id}/admin_response').set(response_payload)

    return jsonify({'status': 'success', 'message': 'Admin response saved'})


@complaints.route('/api/get_user_complaints/<user_id>', methods=['GET'])
def get_user_complaints(user_id):
    ref = db.reference(f"/Makati/Magallanes/complaints/{user_id}")
    user_complaints = ref.get() or {}

    response = [
        {"id": cid, **details}
        for cid, details in user_complaints.items()
    ]

    return jsonify({"status": "success", "complaints": response})


@complaints.route("/get_complaints", methods=["GET"])
def get_complaints():
    complaints_list = []
    complaints_root = db.reference('/Makati/Magallanes/complaints')
    all_data = complaints_root.get() or {}

    for user_id, user_complaints in all_data.items():
        for comp_id, comp_data in (user_complaints or {}).items():
            complaints_list.append({
                **comp_data,
                "id": comp_id,
                "user_id": user_id
            })

    return jsonify(complaints_list)


@complaints.route('/submit_announcement_only', methods=['POST'])
def submit_announcement_only():
    message = request.form.get("message", "").strip()
    targets = request.form.getlist("targets") or []
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if not message or not targets:
        return jsonify({"status": "error", "message": "Missing message or targets"}), 400

    for area in targets:
        db.reference(f"Makati/Magallanes/announcements/{area}").push({
            "from": "admin",
            "message": message,
            "timestamp": timestamp,
            "type": "announcement"
        })

    return jsonify({"status": "success", "message": "Announcement posted."}), 200


@complaints.route('/update_complaint_status', methods=['POST'])
def update_complaint_status():
    try:
        full_id = request.form['complaint_id'].strip()
        new_status = request.form['new_status'].strip().lower()

        user_id, complaint_uid = full_id.split("/", 1)

        complaint_ref = db.reference(f"Makati/Magallanes/complaints/{user_id}/{complaint_uid}")

        complaint_ref.update({
            'complaint_status': new_status
        })

        return jsonify({"status": "success", "message": "Status updated"}), 200

    except Exception as e:
        print("Failed to update complaint status:", e)
        return jsonify({"status": "error", "message": "Failed to update status"}), 500
