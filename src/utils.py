"""
This module provides utility functions for the routes.py module.

Utilities:
- validate_register(username, password, tip_toe_height):
    Validates user registration input.
- validate_record_jump(variant, time, body_weight, note):
    Validates jump record input.
- get_improvement(user_id, timespan): Calculates improvement in jump height
    over a specified timespan.
- validate_query_params(variant, aggregation, height_unit, weight_unit, utc_offset, order, timespan):
    Validates query parameters.
- build_and_filter_query(db, user_id, order, variant, aggregation):
    Builds and filters query based on given parameters.
- generate_plot(buf, x, y, height_unit, timespan):
    Generates a plot based on the given parameters and saves a png image to buffer.

Dependencies:
- SQLAlchemy: For database interactions.
- Matplotlib: For generating plots.

Authors:
- John Zhang
"""

from datetime import datetime, timezone, timedelta
import matplotlib.dates as mdates
import matplotlib
from matplotlib import pyplot as plt
from sqlalchemy import func

from models import VerticalJumpRecord

matplotlib.use('Agg')


def validate_register(username, password, tip_toe_height):
    """
    Validates user input to the register() function.

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
    Validates user input to the record_jump() function.

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
    if not isinstance(time, float) or not time > 0:
        return {'msg': 'hang-time must be a positive floating point value'}
    if not isinstance(body_weight, float) or not body_weight > 0:
        return {'msg': 'body-weight must be a positive floating point value'}
    if note is not None and not isinstance(note, str):
        return {'msg': 'note must be a string'}
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
    jumps = build_and_filter_query(db, user_id, 'date', None, 'max').all()

    if len(jumps) <= 1:
        return None

    prev_index = 0

    for i in range(len(jumps)):
        if jumps[i][0] > datetime.now() - timedelta(days = timespan * 31) and i > 0:
            prev_index = i - 1
            break
        elif jumps[i][0] > datetime.now() - timedelta(days = timespan * 31) and i == 0:
            break
        elif i == len(jumps) - 1:
            return None

    prev = jumps[prev_index][1]
    now = jumps[len(jumps) - 1][1]

    print(prev)
    print(now)

    return (now - prev) * conversion_factor


def validate_query_params(variant, aggregation, height_unit, weight_unit, utc_offset, order, timespan):
    """
    Validates query parameters.

    Parameters:
    - variant (Any): The user input for variant.
    - aggregation (Any): The user input for aggregation.
    - height_unit (Any): The user input for height-unit.
    - weight_unit (Any): The user input for weight-unit.
    - utc_offset (Any): The user input for utc-offset.
    - order (Any): The user input for order-by.
    - timespan (Any): The user input for years.

    Returns:
    - Optional[dict[str, str]]: 
        - A dictionary with a single key 'msg' and the error description.
        - None if there are no errors with user input.
    """
    if aggregation == 'avg' and variant is None:
        return {'msg': "variant must be specified when using the 'avg' aggregation"}
    if aggregation not in {'max', 'avg', None}:
        return {
            'msg': "aggregation must be either 'max' (maximum) or 'avg' (average)"
        }
    if order not in {'date', 'weight', 'height'}:
        return {'msg': "order-by must be either 'date', 'weight', or 'height'"}
    if height_unit not in {'m', 'cm', 'in'}:
        return {"msg": "height-unit must be either 'm', 'cm', or 'in'"}
    if weight_unit not in {'kg', 'lbs'}:
        return {"msg": "weight-unit must be either 'kg' or 'lbs'"}
    if utc_offset not in {str(n) for n in range(-12, 15)}:
        return {'msg': 'utc-offset must be an integer from -12 to 14'}
    if timespan is not None and (not timespan.isdigit() or timespan == '0'):
        return {'msg': 'years must be a positive integer'}
    return None


def build_and_filter_query(db, user_id, order, variant, aggregation):
    """
    Builds and filters query based on given parameters.

    Parameters:
    - db (SQLAlchemy): An instance of the SQLAlchemy class.
    - user_id (int): The id of the user for which the jump records are queried.
    - order (str): The order of jump records. Must be 'date', 'weight', or 'height'.
    - variant (Optional[str]): The jump variant. Must be either 'MAX', 'CMJ', or None.
    - aggregation (Optional[str]): The aggregation method. Must be 'max' or 'avg'.
    

    Returns:
    - sqlalchemy.orm.query.Query: An SQL query.
    """
    if aggregation == 'max':
        aggregation_func = func.max
    elif aggregation == 'avg':
        aggregation_func = func.avg
    else:
        aggregation_func = None

    if aggregation_func:
        jumps = db.session.query(
            VerticalJumpRecord.timestamp.label('date'),
            VerticalJumpRecord.height.label('height'),
            VerticalJumpRecord.variant.label('variant'),
            VerticalJumpRecord.weight.label('weight'),
            VerticalJumpRecord.note.label('note'),
            aggregation_func(VerticalJumpRecord.height).label('height')
        ).group_by(func.date(VerticalJumpRecord.timestamp))
    else:
        jumps = db.session.query(
            VerticalJumpRecord.timestamp.label('date'),
            VerticalJumpRecord.height.label('height'),
            VerticalJumpRecord.variant.label('variant'),
            VerticalJumpRecord.weight.label('weight'),
            VerticalJumpRecord.note.label('note'),
        )

    jumps = jumps.filter(VerticalJumpRecord.user_id == user_id)

    if variant is not None:
        jumps = jumps.filter(VerticalJumpRecord.variant == variant)

    if order == 'date':
        jumps = jumps.order_by(VerticalJumpRecord.timestamp)
    elif order == 'weight':
        jumps = jumps.order_by(VerticalJumpRecord.weight)
    else:
        jumps = jumps.order_by(VerticalJumpRecord.height)

    return jumps


def generate_plot(buf, x, y, height_unit, timespan):
    """
    Generates a plot based on the given parameters and saves a png image to buffer.

    Parameters:
    - buf (io.BytesIO): A binary buffer which will contain the png image of the plot.
    - x (list): x-coordinates of datapoints. Must be the same length as y.
    - y (list): y-coordinates of datapoints. Must be the same length as x.
    - height_unit (str): The unit of measurement for jump height.
    - timespan (int): The timespan in years over which the jump records are plotted. Must be positive.

    Returns:
    - None
    """
    fig, ax = plt.subplots()
    ax.plot(x,y)
    ax.set_xlabel('date')
    ax.set_ylabel(f'jump height ({height_unit})')
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=timespan * 2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.set_xlim(datetime.now(timezone.utc) - timedelta(days=timespan * 365), datetime.now(timezone.utc))

    fig.savefig(buf, format='png')
    buf.seek(0)
