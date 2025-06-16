from flask import Blueprint, request, render_template, jsonify
from firebase_admin import db
import datetime

complaints = Blueprint('complaints', __name__)

@complaints.after_request
def add_header(response):
    if request.path.startswith('/api/'):
        response.headers['Content-Type'] = 'application/json'
    return response


@complaints.route('/submit_complaint/<city>/<barangay>', methods=['POST'])
def submit_complaint(city, barangay):
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
        "userId": from_user_id,
        "city": city,  
        "barangay": barangay,
    }

    db.reference(f"/{city}/{barangay}/complaints/{from_user_id}/{complaint_id}").set(complaint_data)
    return jsonify({"status": "success", "message": "Complaint submitted"})


@complaints.route('/complaints/<city>/<barangay>')
def complaints_page(city, barangay):
    
    try:
        # 1. Validate inputs first
        if not city or not barangay:
            raise ValueError("City and barangay are required")
            
        # 2. Add debug logging
        print(f"Loading complaints for {city}/{barangay}")

        # 3. Get data with timeout protection
        complaints_ref = db.reference(f'/{city}/{barangay}/complaints')
        user_ref = db.reference(f'/{city}/{barangay}/User')

        

        try:
            nested_complaints = complaints_ref.get() or {}
            user_data = user_ref.get() or {}
        except Exception as firebase_error:
            raise RuntimeError(f"Database error: {str(firebase_error)}")

        # 4. Enhanced data validation
        if not isinstance(nested_complaints, dict):
            raise ValueError("Complaints data is malformed")
            
        if not isinstance(user_data, dict):
            raise ValueError("User data is malformed")

        # 5. Process data
        complaint_counts = {}
        enriched_complaints = {}

        for user_id, user_complaints in nested_complaints.items():
            if not isinstance(user_complaints, dict):
                print(f"Warning: Non-dict complaints for user {user_id}")
                continue
                
            for cid, complaint in user_complaints.items():
                try:
                    if not isinstance(complaint, dict):
                        print(f"Warning: Non-dict complaint {cid} for user {user_id}")
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
                        "complaint_id": cid,
                        "city": city,
                        "barangay": barangay,
                    }
                except Exception as processing_error:
                    print(f"Error processing complaint {cid}: {str(processing_error)}")
                    continue

        # 6. Sort only if we have data
        if enriched_complaints:
            enriched_complaints = dict(sorted(
                enriched_complaints.items(),
                key=lambda item: item[1].get('timestamp', ''),
                reverse=True
            ))

        return render_template(
            'complaints.html',
            complaints=enriched_complaints or {},
            city=city,
            barangay=barangay,
            success=bool(enriched_complaints)
        )
            
    except Exception as e:
        print(f"CRITICAL ERROR in complaints_page: {str(e)}", flush=True)
        return render_template(
            'complaints.html',
            complaints={},
            city=city,
            barangay=barangay,
            error=f"System error: {str(e)}",
            success=False
        ), 500 if isinstance(e, RuntimeError) else 400

    

@complaints.route('/submit_admin_response/<city>/<barangay>', methods=['POST'])
def submit_admin_response(city, barangay):
    try:
        data = request.form or request.get_json(force=True, silent=True) or {}
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

        complaint_ref = db.reference(f"{city}/{barangay}/complaints/{user_id}/{complaint_id}")
        
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


@complaints.route('/respond_to_complaint/<city>/<barangay>/<user_id>/<complaint_id>', methods=['POST'])
def respond_to_complaint(city, barangay, user_id, complaint_id):
    response_text = request.form.get('response_text')
    targets = request.form.getlist('targets') or []

    if not response_text:
        return jsonify({"status": "error", "message": "Response is required"}), 400

    db.reference(f'/{city}/{barangay}/complaints/{user_id}/{complaint_id}').update({
        'admin_response': response_text,
        'announcement_targets': targets
    })

    return jsonify({"status": "success", "message": "Response and targets saved"})


@complaints.route('/send_admin_response/<city>/<barangay>/<user_id>/<complaint_id>', methods=['POST'])
def send_admin_response(city, barangay, user_id, complaint_id):
    message = request.form.get('response_message')
    target = request.form.get('announcement_target')

    if not message:
        return jsonify({'status': 'error', 'message': 'Response message required'}), 400

    response_payload = {
        'response_message': message,
        'announcement_target': target,
        'response_timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    db.reference(f'/{city}/{barangay}/complaints/{user_id}/{complaint_id}/admin_response').set(response_payload)


    return jsonify({'status': 'success', 'message': 'Admin response saved'})


@complaints.route('/api/get_user_complaints/<city>/<barangay>/<user_id>', methods=['GET'])
def get_user_complaints(city, barangay, user_id):
    city = request.args.get('city')
    barangay = request.args.get('barangay')
    ref = db.reference(f"{city}/{barangay}/complaints/{user_id}")
    user_complaints = ref.get() or {}

    response = [
        {"id": cid, **details}
        for cid, details in user_complaints.items()
    ]

    return jsonify({"status": "success", "complaints": response})


@complaints.route('/api/complaints/<city>/<barangay>', methods=["GET"])
def get_complaints(city, barangay):
    try:
        # Parse pagination params
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 10))

        complaints_root = db.reference(f'/{city}/{barangay}/complaints')
        all_data = complaints_root.get() or {}

        complaints_list = []
        for user_id, user_complaints in all_data.items():
            if not isinstance(user_complaints, dict):
                continue
            for comp_id, comp_data in (user_complaints or {}).items():
                if isinstance(comp_data, dict):
                    complaints_list.append({
                        **comp_data,
                        "id": comp_id,
                        "user_id": user_id
                    })

        # Sort by timestamp (optional)
        complaints_list.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Pagination logic
        total_items = len(complaints_list)
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = complaints_list[start:end]

        return jsonify({
            "status": "success",
            "complaints": paginated,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "total_items": total_items
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



@complaints.route('/submit_announcement_only/<city>/<barangay>', methods=['POST'])
def submit_announcement_only(city, barangay):
    try:
        # Ensure we're getting form data
        if request.is_json:
            data = request.get_json()
            message = data.get("message", "").strip()
            targets = data.get("targets", [])
        else:
            data = request.form or request.get_json(force=True, silent=True) or {}
            message = request.form.get("message", "").strip()
            targets = request.form.getlist("targets") or []
            
        if not request.form:
            return jsonify({"status": "error", "message": "Form data required"}), 400

        if not message:
            return jsonify({"status": "error", "message": "Message is required"}), 400
        if not targets:
            return jsonify({"status": "error", "message": "At least one target is required"}), 400

        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        announcement_ref = db.reference(f"{city}/{barangay}/announcements")
        
        # Store all targets in a single operation
        updates = {}
        for area in targets:
            area_ref = db.reference(f"{city}/{barangay}/announcements/{area}")
            key = area_ref.push().key  
            updates[f"{area}/{key}"] = {
                "from": "admin",
                "message": message,
                "timestamp": timestamp,
                "type": "announcement",
                "city": city,
                "barangay": barangay
            }
        
        announcement_ref.update(updates)
        return jsonify({
            "status": "success", 
            "message": "Announcement posted",
            "targets": targets
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to post announcement: {str(e)}"
        }), 500

@complaints.route('/api/recent_announcements/<city>/<barangay>', methods=['GET'])
def get_recent_announcements(city, barangay):
    try:
        area_filter = request.args.get('area')
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 5))

        announcements_ref = db.reference(f"{city}/{barangay}/announcements")
        all_data = announcements_ref.get() or {}

        announcements = []
        for area, area_announcements in all_data.items():
            if area_filter and area != area_filter:
                continue
            for aid, ann in (area_announcements or {}).items():
                announcements.append({
                    "id": aid,
                    "message": ann.get("message", ""),
                    "timestamp": ann.get("timestamp", ""),
                    "area": area,
                    "from": ann.get("from", "admin"),
                    "type": ann.get("type", "announcement")
                })

        # Sort by newest first
        announcements.sort(key=lambda a: a["timestamp"], reverse=True)

        # Pagination
        total_items = len(announcements)
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = announcements[start:end]

        return jsonify({
            "status": "success",
            "announcements": paginated,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "total_items": total_items
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
        
@complaints.route('/api/announcement_areas/<city>/<barangay>', methods=['GET'])
def get_announcement_areas(city, barangay):
    try:
        ref = db.reference(f'{city}/{barangay}/announcements')
        data = ref.get() or {}

        areas = sorted(data.keys())
        return jsonify({"status": "success", "areas": areas})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@complaints.route('/update_complaint_status/<city>/<barangay>', methods=['POST'])
def update_complaint_status(city, barangay):

    try:
        full_id = request.form['complaint_id'].strip()
        new_status = request.form['new_status'].strip().lower()

        user_id, complaint_uid = full_id.split("/", 1)

        complaint_ref = db.reference(f"{city}/{barangay}/complaints/{user_id}/{complaint_uid}")

        complaint_ref.update({
            'complaint_status': new_status
        })

        return jsonify({"status": "success", "message": "Status updated"}), 200

    except Exception as e:
        print("Failed to update complaint status:", e)
        return jsonify({"status": "error", "message": "Failed to update status"}), 500

