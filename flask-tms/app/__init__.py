from flask import Flask
import firebase_admin
from firebase_admin import credentials

from app.controllers.auth_controller import auth_bp

def create_app():
    # Create Flask app
    app = Flask(__name__)

    # Set a secret key for flash messages
    app.secret_key = "your_secret_key"

    # Initialize Firebase Admin SDK
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebase-adminsdk.json")
        firebase_admin.initialize_app(cred)

    # Register Blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')

    return app
