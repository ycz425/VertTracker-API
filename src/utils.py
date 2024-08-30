"""
This module provides utility functions for the routes module.

Utilities:
- validate_register(username, password, tip_toe_height):
    Validates user registration input.
- validate_record_jump(variant, time, body_weight, note):
    Validates jump record input.
- get_improvement(user_id, timespan): Calculates improvement in jump height
    over a specified timespan.

Dependencies:
- SQLAlchemy: For database interactions.

Authors:
- John Zhang
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy import func

from models import VerticalJumpRecord


def validate_register(username, password, tip_toe_height):
    """
    Validates user registration input.

    Parameters:
    - username (Any): The user input for username.
    - password (Any): The user input for password.
    - tip_toe_height (Any): The user input for tip-toe-height.

    Returns:
    - Optional[dict[str, str]]: 
        - A dictionary with a single key 'msg' and the error description.
        - None if there are no errors with user input.
    """
    if not isinstance(username, str) or not 1 <= len(username) <= 20:
        return {'msg': 'username must be a string from 1 to 20 characters long'}
    if not isinstance(password, str) or not 10 <= len(password) <= 80:
        return {'msg': 'password must be a string from 10 to 80 characters long'}
    if not isinstance(tip_toe_height, float) or not tip_toe_height > 0:
        return {'msg': 'tip-toe must be a positive floating point value'}
    return None


def validate_record_jump(variant, time, body_weight, note):
    """
    Validates jump record input.

    Parameters:
    - variant (Any): The user input for variant.
    - time (Any): The user input for hang-time.
    - body_weight (Any): The user input for body-weight.
    - note (Any): The user input for note.

    Returns:
    - Optional[dict[str, str]]: 
        - A dictionary with a single key 'msg' and the error description.
        - None if there are no errors with user input.
    """
    if variant not in {'MAX', 'CMJ'}:
        return {
            'msg': (
                "variant must be either 'MAX' (maximum approach jump) "
                "or 'CMJ' (counter movement jump)"
            )
        }
    elif not isinstance(time, float) or not time > 0:
        return {'msg': 'hang-time must be a positive floating point value'}
    elif not isinstance(body_weight, float) or not body_weight > 0:
        return {'msg': 'body-weight must be a positive floating point value'}
    elif note is not None and not isinstance(note, str):
        return {'msg': 'note must be a string'}
    else:
        return None
    
def get_improvement(db, user_id, timespan, conversion_factor):
    """
    Calculates improvement in jump height over a specified timespan.

    Parameters:
    - db (SQLAlchemy): An instance of the SQLAlchemy class.
    - user_id (int): The id of the user to generate the summary for.
        Must be an existing user id.
    - timespan (int): The timespan (in months) over which the summary is generated.
        Must be a positive integer.
    - conversion_factor (float): The conversion factor from meters
        to the desired unit of measurement.

    Returns:
    - float: the difference between the most recent jump
        and the earliest jump in the specified timespan.
    """
    jumps = (
        db.session.query(
            func.max(VerticalJumpRecord.height),
            VerticalJumpRecord.timestamp
        )
        .group_by(func.date(VerticalJumpRecord))
        .filter(VerticalJumpRecord.user_id == user_id)
        .all()
    )

    if len(jumps) <= 1:
        return None

    prev_index = 0

    for i in range(len(jumps)):
        if jumps[i][1] > datetime.now(timezone.utc) - timedelta(months=timespan) and i > 0:
            prev_index = i - 1
            break
        elif jumps[i][1] > datetime.now(timezone.utc) - timedelta(months=timespan) and i == 0:
            break
        elif i == len(jumps) - 1:
            return None

    prev = jumps[prev_index][0]
    now = jumps[len(jumps) - 1][0]

    return (now - prev) * conversion_factor
