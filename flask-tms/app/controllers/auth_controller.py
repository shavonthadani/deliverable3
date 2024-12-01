from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from app.models.user_model import UserModel
import requests
import os
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup')
def signup_page():
    return render_template('signup.html')

@auth_bp.route('/logout')
def logout():
    """
    Handle user logout by clearing the session.
    """
    # Clear all session data
    session.clear()

    # Add a flash message to confirm successful logout
    flash("You have been logged out successfully.", "info")

    # Redirect to the login page
    return redirect(url_for('auth.login_page'))

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Handle user registration.
    """
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    password = request.form.get('password')
    student_number = request.form.get('student_number')
    role = request.form.get('role')

    # Additional fields for students
    study_program = request.form.get('study_program') if role == 'student' else None
    course_section = request.form.get('course_section') if role == 'student' else None

    # Validation
    if not all([first_name, last_name, email, password, student_number, role]):
        return render_template('signup.html', error="All fields are required.")

    if role == 'student' and not all([study_program, course_section]):
        return render_template('signup.html', error="Study Program and Course Section are required for students.")

    try:
        # Call the model to create a user
        UserModel.create_user(first_name, last_name, email, password, student_number, role, study_program, course_section)

        # Flash success message
        flash("You have successfully registered! Please log in.", "success")
        return redirect(url_for('auth.login_page'))  # Redirect to login page
    except Exception as e:
        return render_template('signup.html', error=str(e))



@auth_bp.route('/login')
def login_page():
    return render_template('login.html')

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Handle user login and validate credentials using Firebase REST API.
    """
    student_number = request.form.get('student_number')
    password = request.form.get('password')

    if not student_number or not password:
        return render_template('login.html', error="All fields are required.")

    try:
        # Firebase REST API endpoint
        api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={os.getenv('AUTH_KEY')}"

        # Generate pseudo-email from student number
        email = f"{student_number}@example.com"

        # Send request to Firebase
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }
        response = requests.post(api_url, json=payload)
        response_data = response.json()

        if response.status_code != 200:
            error_message = response_data.get("error", {}).get("message", "Login failed.")
            return render_template('login.html', error=error_message)

        # On success, store user details in session
        session['user_id'] = response_data['localId']
        session['student_number'] = student_number

        # Retrieve additional user info (role, etc.) from Firestore
        user_info = UserModel.get_user_info_by_student_number(student_number)
        session['role'] = user_info.get('role', 'student')  # Default to 'student' if role not set

        return redirect(url_for('auth.dashboard_page'))  # Redirect to dashboard

    except Exception as e:
        return render_template('login.html', error=f"An unexpected error occurred: {str(e)}")

@auth_bp.route('/dashboard')
def dashboard_page():
    """
    Display the dashboard only if the user is logged in.
    """
    if 'student_number' not in session:
        flash("Please log in to access the dashboard.", "warning")
        return redirect(url_for('auth.login_page'))

    student_number = session.get('student_number')
    db = UserModel.get_firestore_client()

    # Fetch user document
    user_ref = db.collection('students').document(student_number).get()

    if not user_ref.exists:
        flash("User not found.", "danger")
        return redirect(url_for('auth.login_page'))

    user_data = user_ref.to_dict()
    session['role'] = user_data.get('role')

    # Search for the user's team in the `teams` collection
    try:
        teams_ref = db.collection('teams')
        query = teams_ref.where('members', 'array_contains', student_number).get()

        if query:
            # If user is part of a team, set the team ID in the session
            team = query[0].to_dict()
            session['team_id'] = query[0].id
            team_name = team.get('team_name')
            flash(f"You are part of team: {team_name}", "info")
        else:
            # If no team found, clear any existing team ID in session
            session.pop('team_id', None)

    except Exception as e:
        flash(f"Error fetching team information: {e}", "danger")
        session.pop('team_id', None)

    return render_template('dashboard.html', user_data=user_data)





