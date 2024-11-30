import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from firebase_admin import firestore
import os
class NotificationModel:

    def get_email_by_student_number(student_number):
        try:
            # Initialize Firestore client
            db = firestore.client()

            # Reference the students collection
            student_ref = db.collection('students').document(student_number)

            # Fetch the student document
            student_doc = student_ref.get()

            # Check if the document exists
            if student_doc.exists:
                # Extract the email field
                student_data = student_doc.to_dict()
                email = student_data.get('email', None)
                if email:
                    return email
                else:
                    raise Exception(f"No email found for student number: {student_number}")
            else:
                raise Exception(f"Student with number {student_number} not found.")

        except Exception as e:
            print(f"Error retrieving email: {e}")
            return None
    def send_email(subject, message, recipient):
        try:
            sender_email = os.getenv("SENDER_EMAIL")
            sender_password = os.getenv("SENDER_PASSWORD")

            # Create the email
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient
            msg['Subject'] = subject

            # Email body
            msg.attach(MIMEText(message, 'plain'))

            # Connect to the SMTP server
            smtp = smtplib.SMTP('smtp.gmail.com', 587)
            smtp.starttls()  # Enable security

            # Enable debugging for SMTP
            smtp.set_debuglevel(1)

            smtp.login(sender_email, sender_password)
            smtp.sendmail(sender_email, recipient, msg.as_string())
            smtp.quit()

            print(f"Email sent successfully to {recipient}")
        except Exception as e:
            print(f"Error sending email: {e}")
