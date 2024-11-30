from datetime import datetime
from firebase_admin import firestore
from app.models.user_model import UserModel

class TeamModel:
    @staticmethod
    def remove_member(team_id, member_id):
        """
        Remove a member from the specified team.
        """
        try:
            db = TeamModel.get_firestore_client()
            team_ref = db.collection('teams').document(team_id)
            team_data = team_ref.get()

            if not team_data.exists:
                raise Exception("Team not found.")

            team = team_data.to_dict()
            members = team.get('members', [])

            if member_id not in members:
                raise Exception(f"Member {member_id} is not part of the team.")

            # Remove the member from the list
            members.remove(member_id)

            # Update the team document
            team_ref.update({'members': members})

        except Exception as e:
            raise Exception(f"Error removing member: {e}")

    @staticmethod
    def update_liaison(team_id, new_liaison_id):
        """
        Update the liaison for a given team.
        """
        try:
            db = TeamModel.get_firestore_client()
            team_ref = db.collection('teams').document(team_id)
            team_data = team_ref.get()

            if not team_data.exists:
                raise Exception("Team not found.")

            # Update the liaison field
            team_ref.update({'liaison_id': new_liaison_id})
        except Exception as e:
            raise Exception(f"Error updating liaison: {e}")

    @staticmethod
    def get_team_details(team_id):
        """
        Fetch details of a team, including member details and pending requests.
        """
        db = TeamModel.get_firestore_client()

        # Fetch the team document
        team_ref = db.collection('teams').document(team_id).get()
        if not team_ref.exists:
            raise Exception("Team not found.")

        team_data = team_ref.to_dict()

        # Fetch member details
        members_details = []
        for member_id in team_data.get('members', []):
            member_ref = db.collection('students').document(member_id).get()
            if member_ref.exists:
                member_data = member_ref.to_dict()
                members_details.append({
                    'student_number': member_id,
                    'name': f"{member_data.get('first_name')} {member_data.get('last_name')}"
                })

        # Fetch pending requests
        pending_requests_details = []
        for request_id in team_data.get('pending_requests', []):
            request_ref = db.collection('students').document(request_id).get()
            if request_ref.exists:
                request_data = request_ref.to_dict()
                pending_requests_details.append({
                    'student_number': request_id,
                    'name': f"{request_data.get('first_name')} {request_data.get('last_name')}"
                })

        # Add details to the team data
        team_data['members_details'] = members_details
        team_data['pending_requests_details'] = pending_requests_details

        return {
            'team_id': team_id,
            'team_name': team_data.get('team_name'),
            'creation_date': team_data.get('date_of_creation'),
            'liaison_id': team_data.get('liaison_id'),
            'status': team_data.get('status', 'incomplete'),
            'members': members_details,
            'pending_requests': pending_requests_details
        }

    @staticmethod
    def get_firestore_client():
        """
        Ensure Firestore client is only created after Firebase is initialized.
        """
        return firestore.client()

    @staticmethod
    def is_team_name_unique(team_name):
        """
        Check if a team name is unique.
        """
        db = TeamModel.get_firestore_client()
        existing_teams = db.collection('teams').where('team_name', '==', team_name).get()
        return not existing_teams

    @staticmethod
    def are_members_valid(member_ids):
        """
        Check if all member IDs exist in the system and are not part of another team.
        """
        db = TeamModel.get_firestore_client()
        for member_id in member_ids:
            member_ref = db.collection('students').document(member_id).get()
            if not member_ref.exists:
                return False, f"Student {member_id} does not exist in the system."
            if member_ref.to_dict().get('team_id'):
                return False, f"Student {member_id} is already part of another team."
        return True, ""

    @staticmethod
    def create_team(team_name, members, liaison_id):
        """
        Create a new team and save it to Firestore.
        """
        db = TeamModel.get_firestore_client()
        team_ref = db.collection('teams').document()

        team_ref.set({
            'team_id': team_ref.id,  # Unique team identifier
            'team_name': team_name,
            'members': members,
            'liaison_id': liaison_id,
            'date_of_creation': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'status': 'incomplete' if len(members) < TeamModel.get_min_team_size() else 'complete'
        })
    @staticmethod
    def get_team_parameters(team_id = None):
        """
        Retrieve the team parameters from Firestore.
        """
        db = TeamModel.get_firestore_client()
        if team_id:
            # Check for team-specific parameters
            team_params_ref = db.collection('team_parameters').document(team_id)
            team_params = team_params_ref.get()
            if team_params.exists:
                return team_params.to_dict()
        params_ref = db.collection('team_parameters').document('default')
        params = params_ref.get()
        if params.exists:
            return params.to_dict()
        else:
            raise Exception("Team parameters not set.")
        
    @staticmethod
    def is_user_in_team(user_id):
        """
        Check if a user is already a member of any team.
        """
        try:
            db = TeamModel.get_firestore_client()
            teams_ref = db.collection('teams')
            
            # Query Firestore to check if the user is in any team's members or pending requests
            teams_with_member = teams_ref.where('members', 'array_contains', user_id).get()
            pending_requests = teams_ref.where('pending_requests', 'array_contains', user_id).get()
            
            # If the user exists in any team or pending requests, return True
            return len(teams_with_member) > 0 or len(pending_requests) > 0
        except Exception as e:
            raise Exception(f"Error checking user in team: {e}")


    @staticmethod
    def get_min_team_size():
        """
        Retrieve the minimum team size from team parameters.
        """
        team_params = TeamModel.get_team_parameters()
        return team_params.get('min_members', 0)  # Default to 0 if not set

    @staticmethod
    def get_max_team_size():
        """
        Retrieve the maximum team size from team parameters.
        """
        team_params = TeamModel.get_team_parameters()
        return team_params.get('max_members', 0)  # Default to 0 if not set
    @staticmethod
    def re_evaluate_teams(min_members, max_members):
        """
        Re-evaluate all teams based on the new parameters and update their statuses.
        """
        db = TeamModel.get_firestore_client()
        teams_ref = db.collection('teams')
        teams = teams_ref.stream()

        for team in teams:
            team_data = team.to_dict()
            team_id = team_data.get('team_id')
            member_count = len(team_data.get('members', []))

            # Determine new status
            if member_count < min_members:
                status = 'incomplete'
            else:
                status = 'complete'

            # Update team status
            teams_ref.document(team_id).update({'status': status})
    @staticmethod
    def add_join_request(team_id, student_id):
        """
        Add a student to the pending requests for a team.
        """
        db = TeamModel.get_firestore_client()
        team_ref = db.collection('teams').document(team_id)
        team_data = team_ref.get()

        if not team_data.exists:
            raise Exception("Team not found.")

        pending_requests = team_data.to_dict().get('pending_requests', [])
        if student_id in pending_requests:
            raise Exception("You have already requested to join this team.")

        # Update pending requests
        pending_requests.append(student_id)
        team_ref.update({'pending_requests': pending_requests})

    @staticmethod
    def get_incomplete_teams():
        """
        Retrieve all incomplete teams from Firestore.
        """
        try:
            db = TeamModel.get_firestore_client()
            teams_ref = db.collection('teams')

            # Query teams with status 'incomplete'
            incomplete_teams_query = teams_ref.where('status', '==', 'incomplete').stream()
            incomplete_teams = []

            for team in incomplete_teams_query:
                team_data = team.to_dict()
                incomplete_teams.append({
                    'team_id': team_data.get('team_id'),
                    'team_name': team_data.get('team_name'),
                    'status': team_data.get('status'),
                    'current_size': len(team_data.get('members', [])),
                    'max_members': team_data.get('max_members', TeamModel.get_max_team_size())
                })

            return incomplete_teams

        except Exception as e:
            raise Exception(f"Error fetching incomplete teams: {e}")


    @staticmethod
    def approve_request(team_id, student_id):
        """
        Approve a student's request to join the team.
        """
        db = TeamModel.get_firestore_client()
        team_ref = db.collection('teams').document(team_id)
        team_data = team_ref.get()

        if not team_data.exists:
            raise Exception("Team not found.")

        team = team_data.to_dict()
        pending_requests = team.get('pending_requests', [])
        members = team.get('members', [])

        if student_id not in pending_requests:
            raise Exception("Student has not requested to join this team.")

        # Remove from pending requests and add to members
        pending_requests.remove(student_id)
        members.append(student_id)

        # Update the team document
        team_ref.update({
            'pending_requests': pending_requests,
            'members': members
        })
    @staticmethod
    def reject_request(team_id, student_number):
        """
        Remove a student from the pending requests list of a team.
        """
        try:
            db = TeamModel.get_firestore_client()
            team_ref = db.collection('teams').document(team_id)
            team_data = team_ref.get()

            if not team_data.exists:
                raise Exception("Team not found.")

            team = team_data.to_dict()
            pending_requests = team.get('pending_requests', [])

            if student_number not in pending_requests:
                raise Exception(f"Student {student_number} does not have a pending request.")

            # Remove the student from pending requests
            pending_requests.remove(student_number)

            # Update the team document
            team_ref.update({'pending_requests': pending_requests})
        except Exception as e:
            raise Exception(f"Error rejecting request: {e}")

    @staticmethod
    def get_all_teams():
        """
        Fetch all teams with their details.
        """
        db = TeamModel.get_firestore_client()
        teams_ref = db.collection('teams').stream()

        all_teams = []
        for team_doc in teams_ref:
            team_data = team_doc.to_dict()

            # Fetch members' details
            members_details = []
            for member_id in team_data.get('members', []):
                member_ref = db.collection('students').document(member_id).get()
                if member_ref.exists:
                    member_info = member_ref.to_dict()
                    members_details.append({
                        'student_number': member_id,
                        'name': f"{member_info.get('first_name')} {member_info.get('last_name')}",
                        'study_program': member_info.get('study_program'),
                        'course_section': member_info.get('course_section'),
                        'email': member_info.get('email'),
                    })

            team_data['members_details'] = members_details
            all_teams.append(team_data)

        return all_teams

    @staticmethod
    def add_member(team_id, student_id):
        """
        Add a student to the specified team.
        """
        db = TeamModel.get_firestore_client()
        team_ref = db.collection('teams').document(team_id)
        team_data = team_ref.get()

        if not team_data.exists:
            raise Exception("Team not found.")

        team = team_data.to_dict()
        if len(team.get('members', [])) >= TeamModel.get_max_team_size():
            raise Exception("Team already at maximum capacity.")

        team_ref.update({'members': firestore.ArrayUnion([student_id])})
        team_parameters = TeamModel.get_team_parameters(team_id)
        min_members = team_parameters.get('min_members', 0)
        max_members = team_parameters.get('max_members', 0)
        TeamModel.re_evaluate_teams(min_members, max_members)

    @staticmethod
    def get_students_without_teams():
        """
        Retrieve a list of students who are not currently part of any team.
        """
        db = TeamModel.get_firestore_client()
        students_ref = db.collection('students')
        teams_ref = db.collection('teams')

        # Fetch all students
        all_students = students_ref.stream()

        # Fetch all teams and their members
        teams = teams_ref.stream()
        all_team_members = set()
        for team in teams:
            team_data = team.to_dict()
            all_team_members.update(team_data.get('members', []))

        students_without_teams = []
        for student in all_students:
            student_data = student.to_dict()

            # Include only students with the "student" role who are not in any team
            if student_data.get('role') == 'student' and student.id not in all_team_members:
                students_without_teams.append({
                    'student_number': student.id,
                    'name': f"{student_data.get('first_name')} {student_data.get('last_name')}",
                    'study_program': student_data.get('study_program'),
                    'course_section': student_data.get('course_section'),
                    'email': student_data.get('email')
                })

        return students_without_teams
