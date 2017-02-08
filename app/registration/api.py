from flask import request
from flask.json import jsonify
from . import registration_blueprint
from .models import Uni, Registration
from .helpers import send_registration_success_mail
from app.user import groups_required
from app.oauth2 import oauth
from app.db import db
import json

@registration_blueprint.route('/api/unis')
@oauth.require_oauth('uni_list')
def api_unis():
    unis = {uni.id: uni.name for uni in Uni.query.all()}
    return jsonify(unis)

@registration_blueprint.route('/api/registration', methods=['GET', 'POST'])
@oauth.require_oauth('registration')
def api_register():
    user = request.oauth.user
    registration = Registration.query.filter_by(username=user.username).first()
    if request.method == 'POST' \
        and request.headers.get('Content-Type') == 'application/json':
        req = request.get_json()
        if not registration:
            registration = Registration()

        registration.username = user.username
        registration.uni_id = req['uni_id']
        registration.blob = json.dumps(req['data'])
        # set registration to False on the first write
        registration.confirmed = registration.confirmed or False
        db.session.add(registration)
        db.session.commit()
        send_registration_success_mail(user)
        return "OK"

    return jsonify(
            uni_id = registration.uni_id,
            confirmed = registration.confirmed,
            data = registration.blob,
        )
