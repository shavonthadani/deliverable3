from firebase_admin import firestore
from datetime import datetime

class TeamParametersModel:
    @staticmethod
    def get_firestore_client():
        return firestore.client()

    @staticmethod
    def set_team_parameters(min_members, max_members, formation_deadline, course_code):
        """
        Set or update team creation parameters.
        """
        db = TeamParametersModel.get_firestore_client()
        params_ref = db.collection('team_parameters').document('default')
        params_ref.set({
            'min_members': int(min_members),
            'max_members': int(max_members),
            'formation_deadline': formation_deadline.strftime("%Y-%m-%d"),  # Ensure date is in string format
            'course_code': course_code  # Include the course code
        })


    @staticmethod
    def get_team_parameters(team_id=None):
        """
        Retrieve the team creation parameters.
        Priority: Custom team parameters > Default parameters.
        """
        db = TeamParametersModel.get_firestore_client()

        if team_id:
            # Check for team-specific parameters
            team_params_ref = db.collection('team_parameters').document(team_id)
            team_params = team_params_ref.get()
            if team_params.exists:
                return team_params.to_dict()

        # Fallback to default parameters
        default_params_ref = db.collection('team_parameters').document('default')
        default_params = default_params_ref.get()
        if default_params.exists:
            return default_params.to_dict()

        # If neither custom nor default parameters are found
        return None

