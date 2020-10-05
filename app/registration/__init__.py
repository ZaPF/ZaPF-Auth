from flask import Blueprint, g
from flask_httpauth import HTTPTokenAuth

token_auth = HTTPTokenAuth(scheme='ZaPF-Token')
registration_blueprint = Blueprint('registration', __name__, template_folder='templates/')

from . import models, views

@token_auth.verify_token
def verify_token(token):
    uni = models.Uni.query.filter_by(token=token).first()
    g.uni = uni
    return uni is not None

def init_app(app):
    return app
