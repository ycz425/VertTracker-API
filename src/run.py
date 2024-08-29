from flask import Flask
from flask_jwt_extended import JWTManager
from models import db
from routes import create_routes

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['JWT_SECRET_KEY'] = '6BoMuJ42TFDNAHNARSRtYjuTePr0DEwF'

db.init_app(app)

jwt = JWTManager(app)

create_routes(app, db)

if __name__ == '__main__':
    app.run(debug=True)