from flask import jsonify, request, Response
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import User, VerticalJumpRecord
from datetime import datetime, timedelta, timezone
from sqlalchemy import desc, func
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import bcrypt
import io

matplotlib.use('Agg')

def create_routes(app, db):

    def validate_register(username, password, tip_toe_height):
        if not isinstance(username, str) or not 1 <= len(username) <= 20:
            return {'msg': 'username must be a string from 1 to 20 characters long'}
        elif not isinstance(password, str) or not 10 <= len(password) <= 80:
            return {'msg': 'password must be a string from 10 to 80 characters long'}
        elif not isinstance(tip_toe_height, float) or not tip_toe_height > 0:
            return {'msg': 'tip-toe must be a positive floating point value'}
        else:
            return None


    @app.post('/api/register')
    def register():
        username = request.json.get('username', None)
        password = request.json.get('password', None)
        tip_toe_height = request.json.get('tip-toe', None)

        validation_error = validate_register(username, password, tip_toe_height)

        if validation_error:
            return jsonify(validation_error), 400
        else:
            db.session.add(User(
                username=username,
                password=bcrypt.hashpw(password.encode(), bcrypt.gensalt()),
                tip_toe_height=tip_toe_height
            ))
            db.session.commit()
            return jsonify({'msg': 'registration success'}), 200


    @app.post('/api/login')
    def login():
        username = request.json.get('username')
        password = request.json.get('password')

        user = User.query.filter_by(username=username).one_or_none()

        if user is None or not bcrypt.checkpw(password.encode(), user.password):
            return jsonify({'msg': 'incorrect username or password'}), 401
        else:
            return jsonify({'access_token': create_access_token(identity=user.id)}), 200


    def validate_record_jump(variant, time, body_weight, note):
        if variant not in {'MAX', 'CMJ'}:
            return {'msg': "variant must be either 'MAX' (maximum approach jump) or 'CMJ' (counter movement jump)"}
        elif not isinstance(time, float) or not time > 0:
            return {'msg': 'hang-time must be a positive floating point value'}
        elif not isinstance(body_weight, float) or not body_weight > 0:
            return {'msg': 'body-weight must be a positive floating point value'}
        elif note is not None and not isinstance(note, str):
            return {'msg': 'note must be a string'}
        else:
            return None


    @app.post('/api/record-jump')
    @jwt_required()
    def record_jump():
        user = User.query.filter_by(id=get_jwt_identity()).one_or_404()

        variant = request.json.get('variant')
        time = request.json.get('hang-time')
        body_weight = request.json.get('body-weight')
        note = request.json.get('note')

        validation_error = validate_record_jump(variant, time, body_weight, note)
        if validation_error:
            return jsonify(validation_error), 400

        height = 9.80665 / 8 * time ** 2 + user.tip_toe_height

        db.session.add(VerticalJumpRecord(variant=variant, height=height, weight=body_weight, note=note, user_id=user.id))
        db.session.commit()

        return jsonify({'msg': 'jump recorded successfully'}), 200


    @app.route('/api/jumps')
    @jwt_required()
    def get_jumps():
        user_id = get_jwt_identity()

        variant = request.json.get('variant', None)  # CMJ or STD
        aggregation = request.json.get('aggregation', None)  # avg or max
        height_unit = request.json.get('height-unit', 'm')  # cm or in or m
        weight_unit = request.json.get('weight-unit', 'kg')
        utc_offset = request.json.get('utc-offset', 0)
        order = request.json.get('order-by', 'date') # date or weight or jump

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
            return jsonify({'msg': "aggregation must be either 'max' (maximum) or 'avg' (average)"}), 400
        
        jumps = jumps.filter(User.id == user_id)
        jumps = jumps.filter(VerticalJumpRecord.variant == variant) if variant is not None else jumps

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

        return jsonify({'data': result}), 200


    @app.get('/api/plot')
    @jwt_required()
    def get_plot():
        user_id = get_jwt_identity()

        timespan = request.json.get('years', 1)
        utc_offset = request.json.get('utc-offset', 0)
        aggregation = request.json.get('aggregation', 'max')

        if not isinstance(timespan, int) or not timespan > 0:
            return jsonify({'msg': 'years must be a positive integer'}), 400
        
        if not isinstance(utc_offset, int) or not -12 <= utc_offset <= 14:
            return jsonify({'msg': 'utt-offset must be an integer from -12 to 14'}), 400

        if aggregation == 'max':
            aggregation_func = func.max
        elif aggregation == 'avg':
            aggregation_func = func.avg
        else:
            return jsonify({'msg': "aggregation must be either 'max' (maximum) or 'avg' (average)"}), 400

        jumps = db.session.query(
            aggregation_func(VerticalJumpRecord.height).label('height'),
            VerticalJumpRecord.timestamp.label('time')
        ).group_by(func.date(VerticalJumpRecord.timestamp)).order_by(VerticalJumpRecord.timestamp).filter(VerticalJumpRecord.user_id == user_id)

        if len(jumps.all()) < 3:
            return jsonify({'msg': 'not enough data points to generate a plot'}), 422

        buf = io.BytesIO()

        fig, ax = plt.subplots()
        ax.plot([jump.time + timedelta(hours=utc_offset) for jump in jumps], [jump.height for jump in jumps])
        ax.set_xlabel('date')
        ax.set_ylabel('jump height (m)')
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=timespan * 3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.set_xlim(datetime.now(timezone.utc) - timedelta(years=timespan))

        fig.savefig(buf, format='png')
        buf.seek(0)

        return Response(buf, mimetype='image/png')


    def get_improvement(user_id, timespan):
        """
        Preconditions:
            - user_id must be a valid user id
            - timespan is a positive integer
        """

        jumps = db.session.query(
            func.max(VerticalJumpRecord.height),
            VerticalJumpRecord.timestamp
        ).group_by(func.date(VerticalJumpRecord)).filter(VerticalJumpRecord.user_id == user_id).all()

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
        return now - prev


    @app.get('/summary')
    @jwt_required()
    def get_summary():
        user_id = get_jwt_identity()

        num_jumps = len(VerticalJumpRecord.query.filter_by(user_id=user_id).all())
        num_days = len({date for  date in db.session.query(func.date(VerticalJumpRecord)).filter(VerticalJumpRecord.user_id == user_id).all()})

        if num_jumps > 0:
            highest_jump = db.session.query(func.max(VerticalJumpRecord.height)).filter(VerticalJumpRecord.user_id == user_id).one()
        
            highest_jump_date = db.session.query(func.date(VerticalJumpRecord.timestamp)).filter(
                VerticalJumpRecord.user_id == user_id,
                VerticalJumpRecord.height == highest_jump
            ).order_by(desc(VerticalJumpRecord.timestamp)).first()

            last_jump, last_jump_date = db.session.query(
                func.max(VerticalJumpRecord.height),
                func.date(VerticalJumpRecord.timestamp)
            ).filter(VerticalJumpRecord.user_id == user_id).group_by(func.date(VerticalJumpRecord.timestamp)).order_by(desc(VerticalJumpRecord.timestamp)).first()

        else:
            highest_jump = None
            highest_jump_date = None
            last_jump = None
            last_jump_date = None
        
        return jsonify(
            {
                'num-records': num_jumps,
                'num-days': num_days,
                'highest-jump': {'height': highest_jump, 'date': highest_jump_date},
                'last-jump': {'height': last_jump, 'date': last_jump_date},
                'improvement': {
                    '6-months': get_improvement(user_id, 6),
                    '12-months': get_improvement(user_id, 12),
                    '24-months': get_improvement(user_id, 24)
                }
            }
        ), 200