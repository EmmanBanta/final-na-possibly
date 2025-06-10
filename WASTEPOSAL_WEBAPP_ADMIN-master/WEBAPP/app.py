from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# Firebase configuration
FIREBASE_BASE_URL = "https://wasteposal-c1fe3afa-default-rtdb.asia-southeast1.firebasedatabase.app"
FIREBASE_USER_PATH = "/Makati/Magallanes/User"

# Generate unique collector ID
def generate_unique_collector_id(existing_ids):
    prefix = "02"
    used_numbers = set()

    for user_id in existing_ids:
        if user_id.startswith(prefix + "-"):
            try:
                num = int(user_id.split("-")[1])
                used_numbers.add(num)
            except (IndexError, ValueError):
                continue

    for i in range(1, 10000):
        if i not in used_numbers:
            return f"{prefix}-{i:04}"

    raise Exception("Unable to generate unique collector ID")

# Render the registration page
@app.route('/')
def home():
    return render_template('reg-collector.html')

# Handle collector registration
@app.route('/register', methods=['POST', 'GET', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    if request.method == 'GET':
        return jsonify({'message': 'Use POST to register', 'endpoint': '/register'}), 200

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        required = ['firstName', 'lastName', 'mobile', 'password']
        missing_fields = [field for field in required if field not in data]
        if missing_fields:
            return jsonify({
                "error": "Missing required fields",
                "missing_fields": missing_fields
            }), 400

        # Fetch existing users
        get_url = f"{FIREBASE_BASE_URL}{FIREBASE_USER_PATH}.json"
        get_response = requests.get(get_url)
        get_response.raise_for_status()
        current_users = get_response.json() or {}
        existing_ids = set(current_users.keys())

        # Generate a unique ID
        user_id = generate_unique_collector_id(existing_ids)

        # Create user data
        user_data = {
            "First name": data["firstName"],
            "Last Name": data["lastName"],
            "mobile": data["mobile"],
            "password": data["password"],
            "role": "collector"
        }

        # Save to Firebase
        put_url = f"{FIREBASE_BASE_URL}{FIREBASE_USER_PATH}/{user_id}.json"
        put_response = requests.put(put_url, json=user_data)
        put_response.raise_for_status()

        return jsonify({
            "success": True,
            "id": user_id,
            "message": "Registration successful"
        }), 201

    except requests.RequestException as re:
        print("Firebase error:", re)
        return jsonify({
            "error": "Failed to communicate with Firebase",
            "details": str(re)
        }), 502

    except Exception as e:
        print("Registration failed:", e)
        return jsonify({
            "error": "Registration failed",
            "details": str(e)
        }), 500

# Run the server
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
