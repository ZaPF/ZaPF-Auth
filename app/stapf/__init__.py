from flask import Blueprint

stapf_blueprint = Blueprint('stapf', __name__, template_folder='templates/')

from . import models, views

def init_app(app):
    return app
