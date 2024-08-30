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
- GET /api/summary: Provides a summary of the user's vertical jump progress.
    Requires JWT authentication.

Dependencies:
- Flask: For creating the web application and handling HTTP requests.
- Flask-JWT-Extended: For handling JSON Web Tokens (JWT) for authentication.
- SQLAlchemy: For database interactions.
- Bcrypt: For password hashing.

Authors:
- John Zhang
"""

import io
from datetime import timedelta
from flask import jsonify, request, Response
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from sqlalchemy import desc, func
import bcrypt
from models import User, VerticalJumpRecord
import utils


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

        variant = request.args.get('variant', None)
        aggregation = request.args.get('aggregation', None)
        height_unit = request.args.get('height-unit', 'm')
        weight_unit = request.args.get('weight-unit', 'kg')
        utc_offset = request.args.get('utc-offset', '0')
        order = request.args.get('order-by', 'date')

        validation_error = utils.validate_query_params(
            variant,
            aggregation,
            height_unit,
            weight_unit,
            utc_offset,
            order,
            None
        )
        if validation_error:
            return jsonify(validation_error), 400
        
        jumps = utils.build_and_filter_query(db, user_id, order, variant, aggregation)

        height_conversion = {'m': 1,  'cm': 100, 'in': 39.3701}
        weight_conversion = {'kg': 1, 'lbs': 2.20462}
        height_conversion_factor = height_conversion[height_unit]
        weight_conversion_factor = weight_conversion[weight_unit]
        utc_offset = int(utc_offset)
            
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
        Returns a plot showing the user's jump progress over time.

        See README.md for a detailed documentation.
        """
        user_id = get_jwt_identity()

        timespan = request.args.get('years', '1')
        utc_offset = request.args.get('utc-offset', '0')
        variant = request.args.get('variant', 'MAX')
        aggregation = request.args.get('aggregation', 'max')
        height_unit = request.args.get('height-unit', 'm')
        
        validation_error = utils.validate_query_params(variant, aggregation, height_unit, 'kg', utc_offset, 'date', timespan)
        if validation_error:
            return jsonify(validation_error), 400

        timespan = int(timespan)
        utc_offset = int(utc_offset)

        jumps = utils.build_and_filter_query(db, user_id, 'date', variant, aggregation)

        height_conversion = {'m': 1,  'cm': 100, 'in': 39.3701}

        buf = io.BytesIO()
        utils.generate_plot(
            buf,
            [(jump.date + timedelta(hours=utc_offset)).date() for jump in jumps],
            [jump.height * height_conversion[height_unit] for jump in jumps],
            height_unit,
            timespan
        )

        return Response(buf, mimetype='image/png')

    @app.get('/api/summary')
    @jwt_required()
    def get_summary():
        """
        Provides a summary of the user's vertical jump progress.

        See README.md for a detailed documentation.
        """
        user_id = get_jwt_identity()
        height_unit = request.args.get('height-unit', 'm')

        jumps = utils.build_and_filter_query(db, user_id, 'date', None, None)
        num_jumps = len(jumps.all())
        num_days = len({jump.date.date() for jump in jumps})

        highest_jump = utils.build_and_filter_query(db, user_id, 'height', None, None).all()[-1]
        last_jump = utils.build_and_filter_query(db, user_id, 'date', None, 'max').all()[-1]

        height_conversion = {'m': 1,  'cm': 100, 'in': 39.3701}
        if height_unit not in height_conversion:
            return jsonify({"msg": "height-unit must be either 'm', 'cm', or 'in'"}), 400
        else:
            conversion_factor = height_conversion[height_unit]

        return jsonify(
            {
                'num-records': num_jumps,
                'num-days': num_days,
                'highest-jump': {
                    'height': highest_jump[1] * conversion_factor,
                    'date': highest_jump[0].date()
                },
                'last-jump': {
                    'height': last_jump[1] * conversion_factor,'date': last_jump[0].date()
                },
                'improvement': {
                    '6-months': utils.get_improvement(db, user_id, 6, conversion_factor),
                    '12-months': utils.get_improvement(db, user_id, 12, conversion_factor),
                    '24-months': utils.get_improvement(db, user_id, 24, conversion_factor)
                }
            }
        ), 200
