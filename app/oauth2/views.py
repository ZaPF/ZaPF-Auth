from .models import Client, Grant, Token
from flask import current_app, render_template
from . import oauth2_blueprint, oauth, admin
from flask_login import current_user, login_user
from flask_ldap3_login.forms import LDAPLoginForm
from flask_babel import Babel, gettext
from app.user import login_required

def handle_oauth_request(*args, **kwargs):
    requested_scopes = set(kwargs['scopes'])
    return requested_scopes.issubset(current_user.scopes)

@oauth2_blueprint.route('/oauth/authorize', methods=['GET', 'POST'])
@oauth.authorize_handler
def authorize(*args, **kwargs):
    if current_user.is_authenticated:
        current_app.logger.info("Authorizing {user.username}".format(
            user = current_user))
        return handle_oauth_request(*args, **kwargs)

    # Otherwise instantiate a login form to log the user in.
    form = LDAPLoginForm()

    if form.validate_on_submit():
        # Successfully logged in, We can now access the saved user object
        # via form.user.
        current_app.logger.debug(
                gettext("Logged in user: %(username)s (%(full_name)s)",
                    username=form.user.username, full_name=form.user.full_name))
        login_user(form.user)  # Tell flask-login to log them in.
        return handle_oauth_request(*args, **kwargs)

    return render_template('login.html', form=form)

@oauth2_blueprint.route('/oauth/token', methods=['POST'])
@oauth.token_handler
def access_token():
    return None

@oauth2_blueprint.route('/oauth/revoke', methods=['POST'])
@oauth.revoke_handler
def revoke_token():
    pass
