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
    def get_team_parameters():
        """
        Retrieve the current team creation parameters.
        """
        db = TeamParametersModel.get_firestore_client()
        params_ref = db.collection('team_parameters').document('default')
        params = params_ref.get()
        if params.exists:
            return params.to_dict()
        else:
            return None
