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

@app.route("/home")
def home():
    return render_template("dashboard.html")

@app.route('/schedule')
def schedule_page_view():
    city = "Makati"
    barangay = "Magallanes"
    return render_template('schedule.html', city=city, barangay=barangay)

@app.route('/reg-collector')
def reg_collector():
    return render_template('reg-collector.html')

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
