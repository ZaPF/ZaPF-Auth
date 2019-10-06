from flask import Blueprint, abort, redirect, url_for, flash
import flask_login
from flask_login import LoginManager, current_user, logout_user
from flask_ldap3_login import LDAP3LoginManager
from functools import wraps

user_blueprint = Blueprint("user", __name__, template_folder="templates/")

from . import models


def init_app(app):

    login_manager = LoginManager(app)
    login_manager.anonymous_user = models.AnonymousUser
    ldap_manager = LDAP3LoginManager(app)

    @ldap_manager.save_user
    def save_user(dn, username, data, memberships):
        user = models.User.get(username)
        return user

    @login_manager.user_loader
    def load_user(id):
        return models.User.get(id)

    # Set up sanity checks.
    from . import sanity

    getattr(app, "sanity_check_modules", []).append(sanity)


def redirect_to_login_page(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user or current_user.is_anonymous:
            return redirect(url_for("user.login"))
        return f(*args, **kwargs)

    return wrapped


def login_required(f):
    @wraps(f)
    @redirect_to_login_page
    @flask_login.login_required
    def wrapped(*args, **kwargs):
        if not current_user or current_user.is_anonymous:
            return redirect(url_for("user.login"))
        if not current_user.confirm_mail or not current_user.confirm_mail["confirmed"]:
            if current_user.confirm_mail and current_user.confirm_mail["token"]:
                flash("Your mail is not confirmed yet.", "warning")
                return redirect(url_for("user.confirm_mail_resend"))
            else:
                current_user.confirm_mail_start()
                flash(
                    "Your mail is not confirmed yet. A confirmation mail has been sent now",
                    "warning",
                )
            logout_user()
            return redirect(url_for("user.login"))
        return f(*args, **kwargs)

    return wrapped


def groups_sufficient(*groups):
    return groups_required(*groups, require_all=False)


def groups_required(*groups, require_all=True):
    def wrapper(f):
        @wraps(f)
        @login_required
        def wrapped(*args, **kwargs):
            if not current_user or current_user.is_anonymous:
                return redirect("/")
            current_groups = set([group.group_name for group in current_user.groups])
            required_groups = set(groups)
            has_all_required_groups = bool(required_groups.issubset(current_groups))
            has_some_required_groups = bool(
                required_groups.intersection(current_groups)
            )
            if (
                require_all
                and has_all_required_groups
                or (not require_all)
                and has_some_required_groups
            ):
                return f(*args, **kwargs)
            abort(403)

        return wrapped

    return wrapper


from . import views
