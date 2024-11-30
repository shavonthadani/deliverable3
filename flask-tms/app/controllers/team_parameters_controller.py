from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models.team_parameters_model import TeamParametersModel
from app.models.team_model import TeamModel
from datetime import datetime

team_parameters_bp = Blueprint('team_parameters', __name__)

@team_parameters_bp.route('/manage', methods=['GET'])
def manage_team_parameters():
    """
    Render the form to manage team parameters.
    Display current settings if they exist.
    """
    try:
        current_settings = TeamParametersModel.get_team_parameters()
    except Exception as e:
        flash(f"Error fetching current parameters: {e}", "danger")
        current_settings = None

    return render_template('manage_team_parameters.html', current_settings=current_settings)

@team_parameters_bp.route('/save', methods=['POST'])
def save_team_parameters():
    """
    Save team parameters to Firestore with validation.
    """
    course_code = request.form.get('course_code')
    min_members = request.form.get('min_members')
    max_members = request.form.get('max_members')
    deadline = request.form.get('deadline')

    # Validation
    if not all([course_code, min_members, max_members, deadline]):
        flash("All fields are required.", "danger")
        return redirect(url_for('team_parameters.manage_team_parameters'))

    try:
        min_members = int(min_members)
        max_members = int(max_members)
        deadline_date = datetime.strptime(deadline, "%Y-%m-%d")

        # Logical validations
        if min_members <= 0:
            flash("Minimum members must be greater than 0.", "danger")
            return redirect(url_for('team_parameters.manage_team_parameters'))

        if max_members <= 1:
            flash("Maximum members must be greater than 1.", "danger")
            return redirect(url_for('team_parameters.manage_team_parameters'))

        if min_members >= max_members:
            flash("Minimum members must be less than maximum members.", "danger")
            return redirect(url_for('team_parameters.manage_team_parameters'))

        if deadline_date <= datetime.now():
            flash("Deadline must be a future date.", "danger")
            return redirect(url_for('team_parameters.manage_team_parameters'))

        # Save parameters using the model
        TeamParametersModel.set_team_parameters(
            min_members=min_members,
            max_members=max_members,
            formation_deadline=deadline_date,
            course_code=course_code
        )

        TeamModel.re_evaluate_teams(min_members, max_members)

        flash("Team parameters saved successfully!", "success")
        return redirect(url_for('auth.dashboard_page'))

    except ValueError:
        flash("Invalid input. Ensure numbers are entered for members and a valid date is provided.", "danger")
        return redirect(url_for('team_parameters.manage_team_parameters'))
    except Exception as e:
        flash(f"Error saving team parameters: {e}", "danger")
        return redirect(url_for('team_parameters.manage_team_parameters'))
