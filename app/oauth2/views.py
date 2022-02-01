from .models import Client, Token
from flask import current_app, render_template
from . import oauth2_blueprint, admin
from flask_login import current_user, login_user
from flask_ldap3_login.forms import LDAPLoginForm
from app.user import login_required


@oauth2_blueprint.route("/oauth/authorize", methods=["GET", "POST"])
@login_required
def authorize():
    if current_user.is_authenticated:
        current_app.logger.info("Authorizing {user.username}".format(user=current_user))
        return current_app.auth_server.create_authorization_response(
            grant_user=current_user
        )

    return current_app.auth_server.create_authorization_response(grant_user=None)


@oauth2_blueprint.route("/oauth/token", methods=["POST"])
def access_token():
    return current_app.auth_server.create_token_response()
