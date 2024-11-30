from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models.team_model import TeamModel

team_bp = Blueprint('team', __name__)

@team_bp.route('/create_team', methods=['GET', 'POST'])
def create_team():
    """
    Handle team creation by students.
    """
    if request.method == 'GET':
        # Check if team parameters are set for the student's course
        course_code = session.get('course_code')
        db = TeamModel.get_firestore_client()
        params_ref = db.collection('team_creation_params').document(course_code).get()

        if not params_ref.exists:
            flash("Team parameters have not been set for your course.", "danger")
            return redirect(url_for('auth.dashboard_page'))

        # Render the team creation form
        return render_template('create_team.html')

    elif request.method == 'POST':
        # Get the form data
        team_name = request.form.get('team_name')
        invited_members = request.form.get('invited_members').split(',')  # Comma-separated list
        invited_members = [member.strip() for member in invited_members if member.strip()]
        student_id = session.get('user_id')

        try:
            # Validate team name uniqueness
            if not TeamModel.is_team_name_unique(team_name):
                flash("A team with this name already exists.", "danger")
                return redirect(url_for('team.create_team'))

            # Validate invited members
            valid, error_message = TeamModel.are_members_valid(invited_members)
            if not valid:
                flash(error_message, "danger")
                return redirect(url_for('team.create_team'))

            # Create the team
            TeamModel.create_team(team_name, student_id, invited_members)
            flash("Team created successfully!", "success")
            return redirect(url_for('auth.dashboard_page'))

        except Exception as e:
            flash(f"Error: {e}", "danger")
            return redirect(url_for('team.create_team'))
