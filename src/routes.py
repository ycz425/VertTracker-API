"""
This module provides endpoints for the VertTracker API.

Endpoints:
- POST /api/register: Registers user into the database.
- POST /api/login: Authenticates a user and returns a JWT access token.
- POST /api/record-jump: Records a user's vertical jump measurement in the database.
    Requires JWT authentication.
- GET /api/jumps: Queries the database for the user's jump records
    based on the query parameters. Requires JWT authentication.
- GET /api/plot: Generates a plot showing the user's jump progress over time.
    Requires JWT authentication.
- GET /summary: Provides a summary of the user's vertical jump progress.
    Requires JWT authentication.

Dependencies:
- Flask: For creating the web application and handling HTTP requests.
- Flask-JWT-Extended: For handling JSON Web Tokens (JWT) for authentication.
- SQLAlchemy: For database interactions.
- Bcrypt: For password hashing.
- Matplotlib: For generating plots.

Authors:
- John Zhang
"""

import io
from datetime import datetime, timedelta, timezone
from flask import jsonify, request, Response
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from sqlalchemy import desc, func
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import bcrypt
from models import User, VerticalJumpRecord
import utils

matplotlib.use('Agg')


def create_routes(app, db):
    """
    Sets up the API routes for the application.

    Parameters:
    - app (Flask): The Flask application.
    - db (SQLAlchemy): An instance of the SQLAlchemy class.
    """

    @app.post('/api/register')
    def register():
        """
        Registers user into the database.

        See README.md for a detailed documentation.
        """
        username = request.json.get('username', None)
        password = request.json.get('password', None)
        tip_toe_height = request.json.get('tip-toe', None)

        validation_error = utils.validate_register(username, password, tip_toe_height)

        if validation_error:
            return jsonify(validation_error), 400

        db.session.add(User(
            username=username,
            password=bcrypt.hashpw(password.encode(), bcrypt.gensalt()),
            tip_toe_height=tip_toe_height
        ))
        db.session.commit()
        return jsonify({'msg': 'registration success'}), 200

    @app.post('/api/login')
    def login():
        """
        Authenticates a user and returns a JWT access token.
        
        See README.md for a detailed documentation.
        """
        username = request.json.get('username')
        password = request.json.get('password')

        user = User.query.filter_by(username=username).one_or_none()

        if user is None or not bcrypt.checkpw(password.encode(), user.password):
            return jsonify({'msg': 'incorrect username or password'}), 401
        else:
            return jsonify({'access_token': create_access_token(identity=user.id)}), 200

    @app.post('/api/record-jump')
    @jwt_required()
    def record_jump():
        """
        Records a user's vertical jump measurement in the database.
        
        See README.md for a detailed documentation.
        """
        user = User.query.filter_by(id=get_jwt_identity()).one_or_404()

        variant = request.json.get('variant')
        time = request.json.get('hang-time')
        body_weight = request.json.get('body-weight')
        note = request.json.get('note')

        validation_error = utils.validate_record_jump(variant, time, body_weight, note)
        if validation_error:
            return jsonify(validation_error), 400

        height = 9.80665 / 8 * time ** 2 + user.tip_toe_height

        db.session.add(VerticalJumpRecord(
            variant=variant,
            height=height,
            weight=body_weight,
            note=note,
            user_id=user.id
        ))
        db.session.commit()

        return jsonify({'msg': 'jump recorded successfully'}), 200

    @app.get('/api/jumps')
    @jwt_required()
    def get_jumps():
        """
        Queries the database for the user's jump records based on the query parameters.

        See README.md for a detailed documentation.
        """
        user_id = get_jwt_identity()

        variant = request.args.get('variant', None)  # CMJ or MAX
        aggregation = request.args.get('aggregation', None)  # avg or max
        height_unit = request.args.get('height-unit', 'm')  # cm or in or m
        weight_unit = request.args.get('weight-unit', 'kg')
        utc_offset = int(request.args.get('utc-offset', 0))
        order = request.args.get('order-by', 'date')  # date or weight or jump

        if aggregation == 'avg' and variant is None:
            return jsonify({'msg': "variant must be specified when using the 'avg' aggregation"})
        elif aggregation == 'avg' or aggregation == 'max':
            aggregation_func = func.avg if aggregation == 'avg' else func.max
            jumps = db.session.query(
                VerticalJumpRecord.timestamp.label('date'),
                VerticalJumpRecord.height.label('height'),
                VerticalJumpRecord.variant.label('variant'),
                VerticalJumpRecord.weight.label('weight'),
                VerticalJumpRecord.note.label('note'),
                aggregation_func(VerticalJumpRecord.height).label('height')
            ).group_by(func.date(VerticalJumpRecord.timestamp))
        elif aggregation is None:
            jumps = db.session.query(
                VerticalJumpRecord.timestamp.label('date'),
                VerticalJumpRecord.height.label('height'),
                VerticalJumpRecord.variant.label('variant'),
                VerticalJumpRecord.weight.label('weight'),
                VerticalJumpRecord.note.label('note'),
            )
        else:
            return jsonify({
                'msg': "aggregation must be either 'max' (maximum) or 'avg' (average)"
            }), 400

        jumps = jumps.filter(User.id == user_id)

        if variant is not None:
            jumps = jumps.filter(VerticalJumpRecord.variant == variant)

        if order == 'date':
            jumps = jumps.order_by(VerticalJumpRecord.timestamp)
        elif order == 'weight':
            jumps = jumps.order_by(VerticalJumpRecord.weight)
        elif order == 'height':
            jumps = jumps.order_by(VerticalJumpRecord.height)
        else:
            return jsonify({'msg': "order-by must be either 'date', 'weight', or 'height'"}), 400

        height_conversion = {'m': 1,  'cm': 100, 'in': 39.3701}
        weight_conversion = {'kg': 1, 'lbs': 2.20462}

        if height_unit not in height_conversion:
            return jsonify({"msg': height-unit must be either 'm', 'cm', or 'in'"}), 400
        else:
            height_conversion_factor = height_conversion[height_unit]

        if weight_unit not in weight_conversion:
            return jsonify({"msg': 'weight-unit must be either 'kg' or 'lbs'"}), 400
        else:
            weight_conversion_factor = weight_conversion[weight_unit]

        if not isinstance(utc_offset, int) or not -12 <= utc_offset <= 14:
            return jsonify({'msg': 'utt-offset must be an integer from -12 to 14'}), 400

        result = []
        for jump in jumps:
            item = {
                'date': (jump.date + timedelta(hours=utc_offset)).strftime('%a %d %b %Y'),
                'height': jump.height * height_conversion_factor,
                'variant': jump.variant,
                'weight': jump.weight * weight_conversion_factor,
                'note': jump.note
            }
            result.append(item)

        return jsonify(result), 200

    @app.get('/api/plot')
    @jwt_required()
    def get_plot():
        """
        Generates a plot showing the user's jump progress over time.

        See README.md for a detailed documentation.
        """
        user_id = get_jwt_identity()

        timespan = int(request.args.get('years', 1))
        utc_offset = int(request.args.get('utc-offset', 0))
        aggregation = request.args.get('aggregation', 'max')

        if not isinstance(timespan, int) or not timespan > 0:
            return jsonify({'msg': 'years must be a positive integer'}), 400

        if not isinstance(utc_offset, int) or not -12 <= utc_offset <= 14:
            return jsonify({'msg': 'utt-offset must be an integer from -12 to 14'}), 400

        if aggregation == 'max':
            aggregation_func = func.max
        elif aggregation == 'avg':
            aggregation_func = func.avg
        else:
            return jsonify({
                'msg': "aggregation must be either 'max' (maximum) or 'avg' (average)"
            }), 400

        jumps = (
            db.session.query(
                aggregation_func(VerticalJumpRecord.height).label('height'),
                VerticalJumpRecord.timestamp.label('time')
            )
            .group_by(func.date(VerticalJumpRecord.timestamp))
            .order_by(VerticalJumpRecord.timestamp)
            .filter(VerticalJumpRecord.user_id == user_id)
        )

        if len(jumps.all()) < 3:
            return jsonify({'msg': 'not enough data points to generate a plot'}), 422

        buf = io.BytesIO()

        fig, ax = plt.subplots()
        ax.plot(
            [jump.time + timedelta(hours=utc_offset) for jump in jumps],
            [jump.height for jump in jumps]
        )
        ax.set_xlabel('date')
        ax.set_ylabel('jump height (m)')
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=timespan * 3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.set_xlim(datetime.now(timezone.utc) - timedelta(years=timespan))

        fig.savefig(buf, format='png')
        buf.seek(0)

        return Response(buf, mimetype='image/png')

    @app.get('/summary')
    @jwt_required()
    def get_summary():
        """
        Provides a summary of the user's vertical jump progress.

        See README.md for a detailed documentation.
        """
        user_id = get_jwt_identity()
        height_unit = request.args.get('height-unit', 'm')

        num_jumps = len(VerticalJumpRecord.query.filter_by(user_id=user_id).all())
        num_days = len({date for date in (
            db.session.query(func.date(VerticalJumpRecord))
            .filter(VerticalJumpRecord.user_id == user_id)
            .all()
        )})

        if num_jumps > 0:
            highest_jump = (
                db.session.query(func.max(VerticalJumpRecord.height))
                .filter(VerticalJumpRecord.user_id == user_id)
                .one()
            )

            highest_jump_date = db.session.query(func.date(VerticalJumpRecord.timestamp)).filter(
                VerticalJumpRecord.user_id == user_id,
                VerticalJumpRecord.height == highest_jump
            ).order_by(desc(VerticalJumpRecord.timestamp)).first()

            last_jump, last_jump_date = (
                db.session.query(
                    func.max(VerticalJumpRecord.height),
                    func.date(VerticalJumpRecord.timestamp)
                )
                .filter(VerticalJumpRecord.user_id == user_id)
                .group_by(func.date(VerticalJumpRecord.timestamp))
                .order_by(desc(VerticalJumpRecord.timestamp))
                .first()
            )

        else:
            highest_jump = None
            highest_jump_date = None
            last_jump = None
            last_jump_date = None

        height_conversion = {'m': 1,  'cm': 100, 'in': 39.3701}
        if height_unit not in height_conversion:
            return jsonify({"msg': height-unit must be either 'm', 'cm', or 'in'"}), 400
        else:
            conversion_factor = height_conversion[height_unit]

        return jsonify(
            {
                'num-records': num_jumps,
                'num-days': num_days,
                'highest-jump': {
                    'height': highest_jump * conversion_factor,
                    'date': highest_jump_date
                },
                'last-jump': {'height': last_jump * conversion_factor, 'date': last_jump_date},
                'improvement': {
                    '6-months': utils.get_improvement(db, user_id, 6, conversion_factor),
                    '12-months': utils.get_improvement(db, user_id, 12, conversion_factor),
                    '24-months': utils.get_improvement(db, user_id, 24, conversion_factor)
                }
            }
        ), 200
