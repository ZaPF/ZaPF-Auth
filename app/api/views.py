from . import api_blueprint
from flask import request, jsonify
from app.oauth2 import oauth

@api_blueprint.route('/api/me', methods=['GET'])
@oauth.require_oauth('ownUserData')
def apiMe():
    user = request.oauth.user
    return jsonify(
            email = user.mail,
            username = user.username,
            firstName = user.firstName,
            surname = user.surname,
            full_name = user.full_name
            )

@api_blueprint.route('/api/me/nextcloud', methods=['GET'])
@oauth.require_oauth('nextcloud')
def api_nextcloud():
    user = request.oauth.user
    return jsonify(
            email = user.mail,
            user_id = user.username,
            firstName = user.firstName,
            lastName = user.surname,
            displayName = user.full_name
            )