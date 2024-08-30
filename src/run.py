"""
This module sets up and configures the Flask application for the vertical jump tracking API.

Usage:
- Run this module directly to start the Flask application.
    The app will listen for incoming requests and handle them according to the defined routes.
    A sample database is provided for testing and exploration.
    A single user a preregistered with the following account information:
        - username: sample_user
        - password: 1234567890

Dependencies:
- Flask: For creating the web application and handling HTTP requests.
- Flask-JWT-Extended: For handling JSON Web Tokens (JWT) for authentication.
- SQLAlchemy: For database interactions.
"""

from flask import Flask
from flask_jwt_extended import JWTManager
from models import db
from routes import create_routes

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sample.db'
app.config['JWT_SECRET_KEY'] = '6BoMuJ42TFDNAHNARSRtYjuTePr0DEwF'

db.init_app(app)

jwt = JWTManager(app)

create_routes(app, db)

if __name__ == '__main__':
    app.run()
