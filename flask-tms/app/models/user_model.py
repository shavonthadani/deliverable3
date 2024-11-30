from firebase_admin import auth, firestore

class UserModel:
    @staticmethod
    def get_firestore_client():
        """
        Ensure Firestore client is only created after Firebase is initialized.
        """
        return firestore.client()

    @staticmethod
    def create_user(first_name, last_name, email, password, student_number, role, study_program=None, course_section=None):
        """
        Create a user in Firebase Auth and Firestore.
        """
        try:
            # Create pseudo-email for Firebase Authentication
            pseudo_email = f"{student_number}@example.com"

            # Create the user in Firebase Auth
            auth_user = auth.create_user(
                email=pseudo_email,
                password=password,
                display_name=f"{first_name} {last_name}",
            )

            # Store user details in Firestore
            db = UserModel.get_firestore_client()
            user_data = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'student_number': student_number,
                'role': role,
            }

            if role == 'student':
                user_data.update({
                    'study_program': study_program,
                    'course_section': course_section,
                })

            db.collection('students').document(student_number).set(user_data)
            return auth_user
        except Exception as e:
            raise Exception(f"Error creating user: {e}")

    @staticmethod
    def get_user_info_by_student_number(student_number):
        """
        Retrieve user info from Firestore using the student number.
        """
        db = UserModel.get_firestore_client()
        user_ref = db.collection('students').document(student_number).get()

        if not user_ref.exists:
            raise Exception("User not found in Firestore.")

        return user_ref.to_dict()
