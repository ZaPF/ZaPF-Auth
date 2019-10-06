from .models import Client, Grant, Token
from flask import current_app, render_template
from . import oauth2_blueprint, oauth, admin
from flask_login import current_user, login_user
from flask_ldap3_login.forms import LDAPLoginForm
from app.user import login_required


@oauth2_blueprint.route("/oauth/authorize", methods=["GET", "POST"])
@oauth.authorize_handler
def authorize(*args, **kwargs):
    if current_user.is_authenticated:
        current_app.logger.info("Authorizing {user.username}".format(user=current_user))
        return True

    # Otherwise instantiate a login form to log the user in.
    form = LDAPLoginForm()

    if form.validate_on_submit():
        # Successfully logged in, We can now access the saved user object
        # via form.user.
        current_app.logger.debug(
            "Logged in user: {user.username} ({user.full_name})".format(user=form.user)
        )
        login_user(form.user)  # Tell flask-login to log them in.
        return True

    return render_template("login.html", form=form)


@oauth2_blueprint.route("/oauth/token", methods=["POST"])
@oauth.token_handler
def access_token():
    return None


@oauth2_blueprint.route("/oauth/revoke", methods=["POST"])
@oauth.revoke_handler
def revoke_token():
    pass
