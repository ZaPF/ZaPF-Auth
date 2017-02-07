from flask import render_template, url_for, \
            redirect, flash, request, current_app
from flask_ldap3_login.forms import LDAPLoginForm
from .models import User
from flask_login import login_user, current_user, login_required, logout_user
from flask_wtf import FlaskForm, RecaptchaField
try:
        from urllib.parse import urlparse, urljoin
except ImportError:
        from urlparse import urlparse, urljoin
from wtforms import StringField, TextField, SubmitField, PasswordField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from wtforms.fields.html5 import EmailField

from . import user_blueprint

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


def get_redirect_target():
    for target in request.args.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return target

class SignUpForm(FlaskForm):
    username = StringField('user', validators=[DataRequired('Please enter a username')])
    givenName = StringField('givenName', validators=[DataRequired('Please enter your given name')])
    surname = StringField('surname', validators=[DataRequired('Please enter your surname')])
    mail = EmailField('email', validators=[
            DataRequired('Please enter your E-Mail address'),
            Email('Please enter a valid E-Mail address')])
    password = PasswordField('password', validators=[
            DataRequired('Please enter a password'),
            EqualTo('confirm', 'Passwords must match')])
    confirm = PasswordField('repeat')
    recaptcha = RecaptchaField()
    submit = SubmitField('Submit')
    next = HiddenField()

    def __init__(self, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        if not self.next.data:
            self.next.data = get_redirect_target() or ''

    def redirect(self, endpoint='login', **values):
        if is_safe_url(self.next.data):
            return redirect(self.next.data)
        target = get_redirect_target()
        return redirect(target or url_for(endpoint, **values))

    def validate_username(form, field):
        """
        Check if the user exists already
        """
        if User.get(field.data):
            raise ValidationError('User already exists')

@user_blueprint.route('/')
def home():
    # Redirect users who are not logged in.
    if not current_user or current_user.is_anonymous:
        return redirect(url_for('user.login'))

    # User is logged in, so show them a page with their cn and dn.

    return render_template("index.html")

@user_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    # Instantiate a LDAPLoginForm which has a validator to check if the user
    # exists in LDAP.
    form = LDAPLoginForm()

    if form.validate_on_submit():
        # Successfully logged in, We can now access the saved user object
        # via form.user.
        current_app.logger.debug(
                "Logged in user: {user.username} ({user.full_name})".format(
                    user = form.user))
        login_user(form.user)  # Tell flask-login to log them in.
        return redirect('/')  # Send them home

    return render_template('login.html', form=form)

@user_blueprint.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm()
    if form.validate_on_submit():
        user = User.create(
            username = form.username.data,
            password = form.password.data,
            givenName = form.givenName.data,
            surname = form.surname.data,
            mail = form.mail.data,
            )
        current_app.logger.info("creating user: {}".format(user))
        flash("Your user account has been created.", 'info')
        return form.redirect()
    print(form.errors)

    return render_template('/signup.html', form=form)

@user_blueprint.route("/logout")
@login_required
def logout():
        logout_user()
        return redirect(url_for("user.home"))
