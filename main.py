from flask import Flask, redirect, url_for, render_template, request, jsonify
import firebase_admin
from firebase_admin import credentials, db
from auth import auth
from schedule_page import schedule_page
from complaints import complaints

app = Flask(__name__)
app.secret_key = 'EATBOLAGA'

cred = credentials.Certificate("../serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://wasteposal-c1fe3afa-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

app.register_blueprint(auth)
app.register_blueprint(schedule_page)
app.register_blueprint(complaints)

@app.route("/")
def login():
    return redirect(url_for('auth.login'))

@app.route('/home')
def home():
    city = "Makati"
    barangay = "Magallanes"
    return render_template("dashboard.html", city=city, barangay=barangay)

@app.route('/schedule')
def schedule_page_view():
    city = "Makati"
    barangay = "Magallanes"
    return render_template('schedule.html', city=city, barangay=barangay)

@app.route('/reg-collector')
def reg_collector():
    return render_template('reg-collector.html')

# Function to generate unique collector ID
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

    for i in range(1, 1000):
        if i not in used_numbers:
            return f"{prefix}-{i:04}"

    raise Exception("Unable to generate unique collector ID")

# Route: Register Collector (API endpoint)
@app.route("/register", methods=["POST", "GET", "OPTIONS"])
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

        # Get existing users from Firebase
        get_url = f"{FIREBASE_BASE_URL}{FIREBASE_USER_PATH}.json"
        get_response = requests.get(get_url)
        get_response.raise_for_status()
        current_users = get_response.json() or {}
        existing_ids = set(current_users.keys())

        # Generate unique ID
        user_id = generate_unique_collector_id(existing_ids)

        # Format new collector data
        user_data = {
            "First name": data["firstName"],
            "Last Name": data["lastName"],
            "mobile": data["mobile"],
            "password": data["password"],
            "role": "collector"
        }

        # Store new user in Firebase
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
            "error": "Firebase request failed",
            "details": str(re)
        }), 502

    except Exception as e:
        print("Registration failed:", e)
        return jsonify({
            "error": "Registration failed",
            "details": str(e)
        }), 500



@app.route("/test-firebase")
def test_firebase():
    try:
        ref = db.reference('/')
        data = ref.get()
        return f"Firebase DB connected! Root data: {data}"
    except Exception as e:
        return f"Failed to connect to Firebase DB: {str(e)}"

@app.route("/add_area", methods=["POST"])
def add_area():
    city = request.form.get("city")
    barangay = request.form.get("barangay")
    area_name = request.form.get("area_name")

    if not city or not barangay or not area_name:
        return "Missing city, barangay, or area_name", 400

    area_data = {
        "days": [],
        "from": "",
        "to": ""
    }

    try:
        ref_path = f"{city}/{barangay}/{area_name}"
        ref = db.reference(ref_path)
        ref.set(area_data)
        return redirect("/home")
    except Exception as e:
        return f"Error adding area: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)
