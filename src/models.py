from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    tip_toe_height = db.Column(db.Float, nullable=False)

    vertical_jump_records = db.relationship('VerticalJumpRecord', uselist=True, cascade='all, delete')


class VerticalJumpRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    height = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    variant = db.Column(db.String(3), nullable=False)  # MAX or CMJ
    weight = db.Column(db.Float, nullable=True)
    note = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)