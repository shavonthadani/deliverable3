from flask import Blueprint, request, render_template, redirect, url_for, flash
from app.models.user_model import UserModel

auth_bp = Blueprint('auth', __name__)
@auth_bp.route('/signup')
def signup_page():
    return render_template('signup.html')

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

    if not all([first_name, last_name, email, password, student_number, role]):
        return render_template('signup.html', error="All fields are required.")

    try:
        # Call the model to create a user
        UserModel.create_user(first_name, last_name, email, password, student_number, role)

        # Add a flash message for successful registration
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
    Handle user login.
    """
    student_number = request.form.get('student_number')
    password = request.form.get('password')

    if not student_number or not password:
        return render_template('login.html', error="Student/Employee number and password are required.")

    try:
        user = UserModel.get_user_by_student_number(student_number)
        # Firebase Admin SDK cannot verify passwords. Add custom validation here if needed.
        return redirect(url_for('auth.dashboard_page'))
    except Exception as e:
        return render_template('login.html', error="Invalid credentials.")

@auth_bp.route('/dashboard')
def dashboard_page():
    return "<h1>Welcome to the Dashboard!</h1>"
