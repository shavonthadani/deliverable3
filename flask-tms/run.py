from app import create_app
from flask import redirect, url_for
app = create_app()
@app.route('/')
def home():
    # Redirect to the /auth/dashboard route
    return redirect(url_for('auth.dashboard_page'))
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
