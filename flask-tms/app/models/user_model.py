from firebase_admin import auth, firestore

class UserModel:
    @staticmethod
    def get_firestore_client():
        """
        Ensure Firestore client is only created after Firebase is initialized.
        """
        return firestore.client()

    @staticmethod
    def create_user(first_name, last_name, email, password, student_number, role):
        try:
            # Check if the user already exists using the pseudo-email
            pseudo_email = f"{student_number}@example.com"
            auth.get_user_by_email(pseudo_email)
            raise Exception("User already exists.")  # Raise a controlled exception if the user exists

        except auth.UserNotFoundError:
            try:
                # If the user does not exist, create them
                user = auth.create_user(
                    email=pseudo_email,
                    password=password,
                    display_name=f"{first_name} {last_name}"
                )
                # Store user details in Firestore
                db = UserModel.get_firestore_client()
                db.collection('users').document(user.uid).set({
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'student_number': student_number,
                    'role': role
                })
                return user
            except Exception as e:
                raise Exception(f"Error: {e}")

        except Exception as e:
            raise Exception(f"Error creating user: {e}")

    @staticmethod
    def get_user_by_student_number(student_number):
        pseudo_email = f"{student_number}@example.com"
        try:
            return auth.get_user_by_email(pseudo_email)
        except Exception as e:
            raise Exception(f"User not found: {e}")
