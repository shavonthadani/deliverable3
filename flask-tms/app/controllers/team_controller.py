from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models.user_model import UserModel
from datetime import datetime
from app.models.team_model import TeamModel
from app.models.notification_model import NotificationModel
from app.models.team_parameters_model import TeamParametersModel
team_bp = Blueprint('team', __name__)

@team_bp.route('/details', methods=['GET', 'POST'])
def team_details():
    """
    Display details about the team the user belongs to and handle team actions.
    """
    # Ensure the user is logged in
    if 'student_number' not in session:
        flash("Please log in to view team details.", "warning")
        return redirect(url_for('auth.login_page'))

    student_number = session.get('student_number')
    team_id = session.get('team_id')

    if not team_id:
        flash("You are not currently part of a team.", "danger")
        return redirect(url_for('auth.dashboard_page'))

    try:
        # Fetch team details
        team_details = TeamModel.get_team_details(team_id)

        # Check if the user is the liaison
        is_liaison = team_details['liaison_id'] == student_number
        team_parameters = TeamModel.get_team_parameters(team_id)
        return render_template('team_details.html', team_details=team_details, is_liaison=is_liaison, team_parameters=team_parameters)
    except Exception as e:
        flash(f"Error fetching team details: {e}", "danger")
        return redirect(url_for('auth.dashboard_page'))


@team_bp.route('/quit', methods=['POST'])
def quit_team():
    """
    Handle a user quitting a team.
    """
    if 'student_number' not in session:
        flash("Please log in to quit the team.", "warning")
        return redirect(url_for('auth.login_page'))

    student_number = session.get('student_number')
    team_id = session.get('team_id')

    if not team_id:
        flash("You are not currently part of a team.", "danger")
        return redirect(url_for('auth.dashboard_page'))

    try:
        # Get the team parameters
        team_parameters = TeamModel.get_team_parameters(team_id)
        deadline = datetime.strptime(team_parameters['formation_deadline'], "%Y-%m-%d")

        # Check if the deadline has passed
        if datetime.now() > deadline:
            flash("You cannot quit the team after the deadline.", "danger")
            return redirect(url_for('auth.dashboard_page'))
        # Check if the user is the liaison
        team_details = TeamModel.get_team_details(team_id)
        if team_details['liaison_id'] == student_number:
            flash("You must transfer liaison ownership before quitting the team.", "danger")
            return redirect(url_for('auth.dashboard_page'))

        # Remove user from the team
        TeamModel.remove_member(team_id, student_number)
        email = NotificationModel.get_email_by_student_number(student_number)
        NotificationModel.send_email(
            subject="You left your team",
            message=f"This is confirmation that you left {team_details['team_name']}",
            recipient=email
        )
        # Clear user's team_id in the session and Firestore
        team_parameters = TeamModel.get_team_parameters(team_id)
        min_members = team_parameters.get('min_members', 0)
        max_members = team_parameters.get('max_members', 0)
        session.pop('team_id', None)
        TeamModel.re_evaluate_teams(min_members, max_members)

        flash("You have successfully quit the team.", "success")
        return redirect(url_for('auth.dashboard_page'))
    except Exception as e:
        flash(f"Error quitting the team: {e}", "danger")
        return redirect(url_for('team.team_details'))


@team_bp.route('/transfer_liaison', methods=['POST'])
def transfer_liaison():
    """
    Handle transferring liaison ownership to another team member.
    """
    # Ensure the user is logged in and is the current liaison
    if 'student_number' not in session:
        flash("Please log in to perform this action.", "warning")
        return redirect(url_for('auth.login_page'))

    team_id = session.get('team_id')
    current_liaison_id = session.get('student_number')
    new_liaison_id = request.form.get('new_liaison_id')

    if not team_id or not current_liaison_id:
        flash("You must be part of a team to perform this action.", "danger")
        return redirect(url_for('auth.dashboard_page'))

    try:
        # Verify that the current user is the liaison
        team_details = TeamModel.get_team_details(team_id)
        if team_details['liaison_id'] != current_liaison_id:
            flash("Only the current liaison can transfer ownership.", "danger")
            return redirect(url_for('auth.dashboard_page'))

        # Update the liaison
        TeamModel.update_liaison(team_id, new_liaison_id)
        flash("Liaison ownership transferred successfully!", "success")
        return redirect(url_for('auth.dashboard_page'))

    except Exception as e:
        flash(f"Error transferring liaison ownership: {e}", "danger")
        return redirect(url_for('auth.dashboard_page'))


@team_bp.route('/create', methods=['GET'])
def create_team_page():
    """
    Render the page to create a team.
    """
    return render_template('create_team.html')

@team_bp.route('/create', methods=['POST'])
def create_team():
    """
    Handle team creation by validating input and saving team details.
    """
    team_name = request.form.get('team_name')
    members = request.form.get('members', '').split(',')  # Split IDs by commas

    # Remove whitespace from member IDs
    members = [member.strip() for member in members if member.strip()]

    # Validation: Ensure team name is provided
    if not team_name:
        flash("Team name is required.", "danger")
        return redirect(url_for('team.create_team_page'))

    # Validation: Check for duplicate member IDs
    if len(set(members)) != len(members):
        flash("Duplicate member IDs found. Each member must have a unique ID.", "danger")
        return redirect(url_for('team.create_team_page'))

    try:
        # Check if all members are students
        db = UserModel.get_firestore_client()
        invalid_members = []
        valid_members = []
        for member_id in members:
            user_ref = db.collection('students').document(member_id).get()
            if not user_ref.exists or user_ref.to_dict().get('role') != 'student':
                invalid_members.append(member_id)
            else:
                valid_members.append(member_id)

        # If there are invalid member IDs, show an error
        if invalid_members:
            flash(f"The following member IDs are invalid or not students: {', '.join(invalid_members)}", "danger")
            return redirect(url_for('team.create_team_page'))

        # Include the current user (team creator) in the team
        current_user_id = session.get('student_number')
        if current_user_id not in valid_members:
            valid_members.append(current_user_id)
        
        # Prevent creating a team if any member is already part of another team
        already_in_team = [
            member for member in valid_members if TeamModel.is_user_in_team(member)
        ]
        if already_in_team:
            flash(f"The following members are already in a team: {', '.join(already_in_team)}", "danger")
            return redirect(url_for('team.create_team_page'))

        # Automatically assign the current user as the team liaison
        liaison_id = current_user_id

        # Save the team details
        TeamModel.create_team(
            team_name=team_name,
            members=valid_members,
            liaison_id=liaison_id
        )

        flash("Team created successfully!", "success")
        return redirect(url_for('auth.dashboard_page'))

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('team.create_team_page'))

@team_bp.route('/browse-teams', methods=['GET'])
def browse_teams():
    """
    Allow students to browse incomplete teams and request to join them.
    """
    # Ensure the user is logged in and not already part of a team
    if 'student_number' not in session:
        flash("Please log in to view available teams.", "warning")
        return redirect(url_for('auth.login_page'))

    if session.get('team_id'):
        flash("You are already part of a team.", "danger")
        return redirect(url_for('auth.dashboard_page'))

    try:
        # Fetch incomplete teams
        incomplete_teams = TeamModel.get_incomplete_teams()

        return render_template('browse_teams.html', teams=incomplete_teams)
    except Exception as e:
        flash(f"Error fetching teams: {e}", "danger")
        return redirect(url_for('auth.dashboard_page'))
    
@team_bp.route('/request-join/<team_id>', methods=['POST'])
def request_join(team_id):
    """
    Handle a student's request to join a team.
    """
    if 'student_number' not in session:
        flash("Please log in to request joining a team.", "warning")
        return redirect(url_for('auth.login_page'))

    student_id = session.get('student_number')

    try:
        # Add the student to the team's pending requests
        TeamModel.add_join_request(team_id, student_id)
        flash("Your request to join the team has been sent.", "success")
        return redirect(url_for('auth.dashboard_page'))
    except Exception as e:
        flash(f"Error requesting to join the team: {e}", "danger")
        return redirect(url_for('auth.dashboard_page'))

@team_bp.route('/approve-request/<team_id>', methods=['POST'])
def approve_request(team_id):
    """
    Approve a join request for a team.
    """
    if 'team_id' not in session:
        flash("You must be part of a team to approve requests.", "danger")
        return redirect(url_for('auth.dashboard_page'))

    student_number = request.form.get('student_number')

    try:
        # Fetch team details
        team = TeamModel.get_team_details(team_id)

        # Ensure the liaison is approving the request
        if session['student_number'] != team['liaison_id']:
            flash("Only the team liaison can approve requests.", "danger")
            return redirect(url_for('auth.dashboard_page'))

        # Add the student to the team if not already full
        if len(team['members']) >= TeamModel.get_max_team_size():
            flash("The team is already at maximum capacity.", "danger")
            return redirect(url_for('auth.dashboard_page'))

        TeamModel.approve_request(team_id, student_number)
        email = NotificationModel.get_email_by_student_number(student_number)
        NotificationModel.send_email(
            subject="You were added to a team",
            message=f"This is confirmation that you were added to {team['team_name']}",
            recipient=email
        )
        team_parameters = TeamModel.get_team_parameters(team_id)
        min_members = team_parameters.get('min_members', 0)
        max_members = team_parameters.get('max_members', 0)
        TeamModel.re_evaluate_teams(min_members, max_members)
        flash(f"{student_number} has been added to the team.", "success")
    except Exception as e:
        flash(f"Error approving request: {e}", "danger")

    return redirect(url_for('auth.dashboard_page'))

@team_bp.route('/reject-request/<team_id>', methods=['POST'])
def reject_request(team_id):
    """
    Reject a join request for a team.
    """
    if 'team_id' not in session:
        flash("You must be part of a team to reject requests.", "danger")
        return redirect(url_for('auth.dashboard_page'))

    student_number = request.form.get('student_number')

    try:
        # Ensure the liaison is rejecting the request
        team = TeamModel.get_team_details(team_id)
        if session['student_number'] != team['liaison_id']:
            flash("Only the team liaison can reject requests.", "danger")
            return redirect(url_for('auth.dashboard_page'))

        TeamModel.reject_request(team_id, student_number)
        flash(f"Request from {student_number} has been rejected.", "success")
    except Exception as e:
        flash(f"Error rejecting request: {e}", "danger")

    return redirect(url_for('auth.dashboard_page'))

@team_bp.route('/instructor/teams', methods=['GET'])
def view_all_teams():
    """
    Display a list of all teams for the instructor's courses.
    """
    if 'role' not in session or session['role'] != 'instructor':
        flash("Access denied. Only instructors can view teams.", "danger")
        return redirect(url_for('auth.dashboard_page'))

    try:
        teams = TeamModel.get_all_teams()
        students_without_teams = TeamModel.get_students_without_teams()  # Fetch students not in teams
        return render_template('view_all_teams.html', teams=teams,students_without_teams=students_without_teams)
    except Exception as e:
        flash(f"Error fetching teams: {e}", "danger")
        return redirect(url_for('auth.dashboard_page'))

@team_bp.route('/instructor/add_member/<team_id>', methods=['POST'])
def add_member_to_team(team_id):
    """
    Add a student to a team.
    """
    if 'role' not in session or session['role'] != 'instructor':
        flash("Access denied. Only instructors can add members to teams.", "danger")
        return redirect(url_for('auth.dashboard_page'))

    student_id = request.form.get('student_id')
    team_parameters = TeamModel.get_team_parameters(team_id)
    deadline = datetime.strptime(team_parameters['formation_deadline'], "%Y-%m-%d")

    # Check if the deadline has passed
    if datetime.now() > deadline:
        flash("You cannot add member after deadline.", "danger")
        return redirect(url_for('auth.dashboard_page'))
    try:
        # Check if student is already in a team
        if TeamModel.is_user_in_team(student_id):
            flash(f"Student {student_id} is already in a team.", "danger")
        else:
            TeamModel.add_member(team_id, student_id)
            team_parameters = TeamModel.get_team_parameters(team_id)
            min_members = team_parameters.get('min_members', 0)
            max_members = team_parameters.get('max_members', 0)
            TeamModel.re_evaluate_teams(min_members, max_members)
            email = NotificationModel.get_email_by_student_number(student_id)
            team = TeamModel.get_team_details(team_id)
            NotificationModel.send_email(
                subject="You were added to a team",
                message=f"This is confirmation that you were added to {team['team_name']}",
                recipient=email
            )
            flash("Student added to the team successfully!", "success")
    except Exception as e:
        flash(f"Error adding student to the team: {e}", "danger")

    return redirect(url_for('auth.dashboard_page'))

@team_bp.route('/instructor/remove_member/<team_id>', methods=['POST'])
def remove_member_from_team(team_id):
    """
    Remove a student from a team.
    """
    if 'role' not in session or session['role'] != 'instructor':
        flash("Access denied. Only instructors can remove members from teams.", "danger")
        return redirect(url_for('auth.dashboard_page'))
    team_parameters = TeamModel.get_team_parameters(team_id)
    deadline = datetime.strptime(team_parameters['formation_deadline'], "%Y-%m-%d")

    # Check if the deadline has passed
    if datetime.now() > deadline:
        flash("You cannot remove member after deadline.", "danger")
        return redirect(url_for('auth.dashboard_page'))

    student_id = request.form.get('student_id')
    team_details = TeamModel.get_team_details(team_id)
    if team_details['liaison_id'] == student_id:
        flash("You cannot remove a liason.", "danger")
        return redirect(url_for('auth.dashboard_page'))

    try:
        TeamModel.remove_member(team_id, student_id)
        team_parameters = TeamModel.get_team_parameters(team_id)
        min_members = team_parameters.get('min_members', 0)
        max_members = team_parameters.get('max_members', 0)
        TeamModel.re_evaluate_teams(min_members, max_members)
        email = NotificationModel.get_email_by_student_number(student_id)
        team = TeamModel.get_team_details(team_id)
        NotificationModel.send_email(
            subject="You were removed from a team",
            message=f"This is confirmation that you were removed from {team['team_name']}",
            recipient=email
        )
        flash("Student removed from the team successfully!", "success")
    except Exception as e:
        flash(f"Error removing student from the team: {e}", "danger")

    return redirect(url_for('auth.dashboard_page'))

@team_bp.route('/customize_parameters/<team_id>', methods=['POST'])
def customize_team_parameters(team_id):
    """
    Save custom team parameters for a specific team.
    """
    min_members = request.form.get('min_members')
    max_members = request.form.get('max_members')
    deadline = request.form.get('deadline')

    # Validation
    if not all([min_members, max_members, deadline]):
        flash("All fields are required.", "danger")
        return redirect(url_for('auth.dashboard_page'))

    try:
        min_members = int(min_members)
        max_members = int(max_members)
        deadline_date = datetime.strptime(deadline, "%Y-%m-%d")

        if min_members <= 0 or max_members <= 1 or min_members >= max_members:
            flash("Invalid member constraints.", "danger")
            return redirect(url_for('auth.dashboard_page'))

        if deadline_date <= datetime.now():
            flash("Deadline must be a future date.", "danger")
            return redirect(url_for('auth.dashboard_page'))

        # Save custom parameters
        db = TeamParametersModel.get_firestore_client()
        db.collection('team_parameters').document(team_id).set({
            'min_members': min_members,
            'max_members': max_members,
            'formation_deadline': deadline
        })
        team_parameters = TeamModel.get_team_parameters(team_id)
        min_members = team_parameters.get('min_members', 0)
        max_members = team_parameters.get('max_members', 0)
        TeamModel.re_evaluate_teams(min_members, max_members)

        flash("Custom parameters set successfully!", "success")
        return redirect(url_for('auth.dashboard_page'))

    except ValueError:
        flash("Invalid input. Ensure numbers are entered for members and a valid date is provided.", "danger")
        return redirect(url_for('auth.dashboard_page'))
    except Exception as e:
        flash(f"Error saving custom parameters: {e}", "danger")
        return redirect(url_for('auth.dashboard_page'))

@team_bp.route('/list_teams', methods=['GET'])
def list_teams():
    """
    Display a list of all teams with actions for instructors.
    """
    try:
        teams = TeamModel.get_all_teams()  # Fetch all teams
        students_without_teams = TeamModel.get_students_without_teams()  # Fetch students not in teams

        return render_template('list_teams.html', teams=teams, students_without_teams=students_without_teams)
    except Exception as e:
        flash(f"Error fetching teams: {e}", "danger")
        return redirect(url_for('auth.dashboard_page'))
