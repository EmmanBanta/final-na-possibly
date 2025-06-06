from flask import Blueprint, render_template, request, redirect, url_for, flash
import requests

auth = Blueprint('auth', __name__)

FIREBASE_DB_URL = "https://wasteposal-c1fe3afa-default-rtdb.asia-southeast1.firebasedatabase.app"

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mobile = request.form.get('mobile')
        password = request.form.get('password')

        
        response = requests.get(f"{FIREBASE_DB_URL}/.json")
        if response.status_code != 200:
            flash("Failed to connect to database", "danger")
            return render_template("login.html")

        data = response.json()
        for city in data.values():
            for barangay in city.values():
                users = barangay.get("User", {})
                for user in users.values():
                    if user.get("mobile") == mobile and user.get("password") == password:
                        if user.get("role") == "admin":
                            flash("Login successful!", "success")
                            return redirect('home')
                        
                        else:
                            flash("Access denied. Not an admin.", "warning")
                            return render_template("login.html")

        flash("Invalid credentials", "danger")

    return render_template("login.html")
