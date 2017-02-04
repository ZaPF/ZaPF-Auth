from . import api_blueprint
from flask import request, jsonify
from app.oauth2 import oauth

@api_blueprint.route('/api/me', methods=['GET'])
@oauth.require_oauth('ownUserData')
def apiMe():
    user = request.oauth.user
    return jsonify(email = user.mail, username = user.username, firstName = user.firstName, surname = user.surname)
