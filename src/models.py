"""
This module defines the database models for the vertical jump tracking application using SQLAlchemy.

Models:
- User: Represents a user in the system.
- VerticalJumpRecord: Represents a record of a vertical jump performed by a user.

Dependencies:
- SQLAlchemy: For database interactions.

Author:
- John Zhang
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


class User(db.Model):
    """
    Represents a user in the database.

    Attributes:
    - id (int): The unique identifier for the user.
    - username (str): The username of the user. It must be unique and is limited to 20 characters.
    - password (str): The hashed password of the user. It is stored as a string up to 80 characters long.
    - tip_toe_height (float): The user's tip-toe height, used to adjust jump height calculations.

    Relationships:
    - vertical_jump_records (list of VerticalJumpRecord): The vertical jump records associated with this user. This relationship
      supports cascading delete operations, so all associated records are deleted when the user is removed.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    tip_toe_height = db.Column(db.Float, nullable=False)

    vertical_jump_records = db.relationship(
        'VerticalJumpRecord',
        uselist=True,
        cascade='all, delete'
    )


class VerticalJumpRecord(db.Model):
    """
    Represents a vertical jump record associated with a user.

    Attributes:
    - id (int): The unique identifier for the jump record.
    - height (float): The height of the jump, calculated based on the hang-time and user data.
    - timestamp (datetime): The date and time when the jump was recorded. Defaults to the current time in UTC.
    - variant (str): The type of jump performed. Must be either 'MAX' (maximum approach jump) or 'CMJ' (counter movement jump).
    - weight (float, optional): The body weight of the user at the time of the jump. This value is optional.
    - note (str, optional): Any additional notes provided by the user about the jump.
    - user_id (int): The ID of the user who performed the jump. This is a foreign key that links to the `User` model. 
      The record is deleted if the associated user is removed.

    Relationships:
    - user (User): The user who owns this jump record. This is a foreign key relationship with the `User` model.
    """
    id = db.Column(db.Integer, primary_key=True)
    height = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    variant = db.Column(db.String(3), nullable=False)
    weight = db.Column(db.Float, nullable=True)
    note = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
