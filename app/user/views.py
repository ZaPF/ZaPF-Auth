from flask import render_template, url_for, \
            redirect, flash, request, current_app
from flask_ldap3_login.forms import LDAPLoginForm
from .models import User
import flask_login
from flask_login import login_user, current_user, logout_user
from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, TextField, SubmitField, PasswordField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from wtforms.fields.html5 import EmailField
import time
from app.views import is_safe_url, get_redirect_target
from . import login_required

class UsernameInUseValidator(object):
    def __call__(self, form, field):
        if User.get(field.data):
            raise ValidationError('User already exists')

class MailInUseValidator(object):
    def __call__(self, form, field):
        if len(User.query('mail: {}'.format(field.data))) != 0:
            raise ValidationError('E-Mail address already in use')

from . import user_blueprint, admin

class SignUpForm(FlaskForm):
    username = StringField('user', validators=[DataRequired('Please enter a username'), UsernameInUseValidator()])
    givenName = StringField('givenName', validators=[DataRequired('Please enter your given name')])
    surname = StringField('surname', validators=[DataRequired('Please enter your surname')])
    mail = EmailField('email', validators=[
            DataRequired('Please enter your E-Mail address'),
            Email('Please enter a valid E-Mail address'),
            MailInUseValidator()])
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

class PasswordResetStartForm(FlaskForm):
    user_or_mail = StringField('user_or_mail', validators=[DataRequired('Please enter a username or mail')])
    recaptcha = RecaptchaField()
    submit = SubmitField('Reset password')

class PasswordResetFinishForm(FlaskForm):
    password = PasswordField('password', validators=[
            DataRequired('Please enter a password'),
            EqualTo('confirm', 'Passwords must match')])
    confirm = PasswordField('repeat')
    submit = SubmitField('Set new password')

class ResendConfirmMailForm(FlaskForm):
    submit = SubmitField('Resend confirmation mail')

@user_blueprint.route('/')
@login_required
def home():
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
        user.confirm_mail_start()
        current_app.logger.info("creating user: {}".format(user))
        flash("Your user account has been created.", 'info')
        flash("Your E-Mail has to be confirmed before you can login!", 'warning')
        return form.redirect()

    return render_template('/signup.html', form=form)

@user_blueprint.route("/logout")
@login_required
def logout():
        logout_user()
        next = request.args.get("next")
        if next and (next in current_app.config["LOGOUT_ALLOWED_NEXT"] or
           is_safe_url(next)):
            return redirect(next)
        else:
            return redirect(url_for("user.home"))

@user_blueprint.route('/user/edit', methods=['GET', 'POST'])
@login_required
def edit_me():
    return admin.edit_user(current_user.username, url_for('user.edit_me'))

@user_blueprint.route('/user/reset_password', methods=['GET', 'POST'])
def reset_password_start():
    form = PasswordResetStartForm()
    if form.validate_on_submit():
        user = User.get(form.user_or_mail.data)
        if not user:
            users = User.query('mail: {}'.format(form.user_or_mail.data))
            if len(users) > 0:
                user = users[0]
        if user:
            user.reset_password_start()
        flash('If your username or mail is valid, you should recive a mail with instructions soon!', 'info')
        return redirect(url_for('user.home'))
    return render_template('reset_password_start.html', form=form)

@user_blueprint.route('/user/reset_password/<string:username>/<string:token>', methods=['GET', 'POST'])
def reset_password_finish(username, token):
    user = User.get(username)

    if not user:
        return redirect(url_for('user.login'))
    if not user.reset_password or user.reset_password[0] != token or user.reset_password[1] < int(time.time()):
        flash('Your password reset token is invalid or expired.', 'error')
        return redirect(url_for('user.home'))

    form = PasswordResetFinishForm()

    if form.validate_on_submit():
        user.password = form.password.data
        user.reset_password = None
        user.save()
        flash('New password has been set.', 'info')
        return redirect(url_for('user.login'))

    return render_template('reset_password_finish.html', form=form)

@user_blueprint.route('/user/confirm_mail', methods=['GET', 'POST'])
@flask_login.login_required
def confirm_mail_resend():
    form = ResendConfirmMailForm()
    if form.validate_on_submit():
        current_user.confirm_mail_start()
        logout_user()
        return redirect(url_for('user.login'))
    return render_template('resend_confirm_mail.html', form=form)

@user_blueprint.route('/user/confirm_mail/<string:username>/<string:token>', methods=['GET', 'POST'])
def confirm_mail_finish(username, token):
    user = User.get(username)

    if not user:
        return redirect(url_for('user.login'))
    if not user.confirm_mail or user.confirm_mail['token'] != token or user.confirm_mail['valid_till'] < int(time.time()):
        flash('Your mail confirmation token is invalid or expired.', 'error')
        return redirect(url_for('user.login'))

    user.confirm_mail['confirmed'] = True
    user.confirm_mail['token'] = None
    user.confirm_mail['valid_till'] = None
    user.save()

    flash('E-Mail confirmed', 'success')

    return redirect('/')
