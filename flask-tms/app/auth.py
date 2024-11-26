from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from firebase_admin import auth, firestore

auth_bp = Blueprint('auth', __name__)
db = firestore.client()

# Serve the sign-up page
@auth_bp.route('/signup')
def signup_page():
    return render_template('signup.html')

# Handle sign-up form submission
@auth_bp.route('/register', methods=['POST'])
def register():
    # Collect data from the form
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    password = request.form.get('password')
    student_number = request.form.get('student_number')
    role = request.form.get('role')

    # Validate required fields
    if not all([first_name, last_name, email, password, student_number, role]):
        return jsonify({"error": "All fields are required"}), 400

    try:
        # Create a pseudo-email if needed (or use the actual email directly)
        pseudo_email = f"{student_number}@example.com"

        # Create user in Firebase Authentication
        user = auth.create_user(
            email=pseudo_email,
            password=password,
            display_name=f"{first_name} {last_name}"
        )

        # Store user metadata in Firestore
        db.collection('users').document(user.uid).set({
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'student_number': student_number,
            'role': role
        })

        # Redirect to the login page after successful registration
        return redirect(url_for('auth.login_page'))
    except Exception as e:
        error = "Invalid Student/Employee number or password."
        return render_template('login.html', error=error)

# Serve the login page
@auth_bp.route('/login')
def login_page():
    return render_template('login.html')

# Handle login form submission
@auth_bp.route('/login', methods=['POST'])
def login():
    student_number = request.form.get('student_number')  # Get the student/employee number
    password = request.form.get('password')             # Get the password

    # Validate required fields
    if not student_number or not password:
        return jsonify({"error": "Student/employee number and password are required"}), 400

    try:
        # Map the student/employee number to a pseudo-email
        pseudo_email = f"{student_number}@example.com"

        # Use Firebase Admin SDK to find the user by email
        user = auth.get_user_by_email(pseudo_email)

        # Note: Firebase Admin SDK cannot verify passwords directly.
        # For now, we assume login is successful if the user exists.
        # You can add a custom password validation layer or Firebase Client SDK for secure login.

        return redirect(url_for('auth.dashboard_page'))  # Redirect to dashboard on successful login
    except Exception as e:
        error = "Invalid Student/Employee number or password."
        return render_template('login.html', error=error)


# Serve the dashboard page
@auth_bp.route('/dashboard')
def dashboard_page():
    return "<h1>Welcome to the Dashboard!</h1>"
