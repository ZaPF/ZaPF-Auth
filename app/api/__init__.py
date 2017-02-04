from flask import Blueprint

api_blueprint = Blueprint('api', __name__, template_folder = 'templates/')

from . import views

def init_app(app):
    # Set up sanity checks.
    from . import sanity
    getattr(app, 'sanity_check_modules', []).append(sanity)

    return app
