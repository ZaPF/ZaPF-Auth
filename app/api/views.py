from . import api_blueprint
from flask import request, jsonify


@api_blueprint.route("/api/me", methods=["GET"])
def apiMe():
    user = request.oauth.user
    return jsonify(
        email=user.mail,
        username=user.username,
        firstName=user.firstName,
        surname=user.surname,
        full_name=user.full_name,
    )
