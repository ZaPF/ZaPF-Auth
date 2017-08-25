from flask import render_template, redirect, url_for, flash, abort
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email, EqualTo, Optional
from wtforms.fields.html5 import EmailField
from app.views import confirm, is_safe_url
from . import groups_required, user_blueprint, login_required
from .models import User
from .views import MailInUseValidator

class UserEditForm(FlaskForm):
    username = StringField('Username')
    givenName = StringField('Given Name', validators=[DataRequired('Please enter a given name')])
    surname = StringField('Surname', validators=[DataRequired('Please enter a surname')])
    mail = EmailField('E-Mail', validators=[
            DataRequired('Please enter an E-Mail address'),
            Email('Please enter a valid E-Mail address'),
            MailInUseValidator()])
    password = PasswordField('Password', validators=[
            Optional(False),
            EqualTo('confirm_password', 'Passwords must match')])
    confirm_password = PasswordField('Repeat password')
    submit = SubmitField('Submit')

@user_blueprint.route('/admin/users')
@login_required
@groups_required('admin')
def list_users():
    users = User.query()
    return render_template('admin/listUsers.html',
        users = users
    )

@user_blueprint.route('/admin/user/<string:username>/delete', methods=['GET', 'POST'])
@login_required
@confirm(title='Delete User?',
        prompt='Are you sure you want to delete this user?',
        action='Delete',
        back='user.list_users')
@groups_required('admin')
def delete_user(username):
    user = User.get(username)
    if not user:
        flash('Invalid user name!', 'error')
        return redirect(url_for('user.list_users'))
    user.delete()
    flash('User has been deleted', 'success')
    return redirect(url_for('user.list_users'))

@user_blueprint.route('/admin/user/<string:username>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(username, back_url = None):
    if not is_safe_url(back_url):
        back_url = url_for('user.list_users')

    user = User.get(username)
    if not user:
        flash('Invalid user name!', 'error')
        return redirect(back_url)
    if not current_user.is_admin and user.username != current_user.username:
        abort(403)
        return ''

    form = UserEditForm()
    if form.validate_on_submit():
        old_mail = user.mail

        if form.password.data:
            user.update(
              givenName = form.givenName.data,
              surname = form.surname.data,
              mail = form.mail.data,
              password = form.password.data
            )
        else:
            user.update(
              givenName = form.givenName.data,
              surname = form.surname.data,
              mail = form.mail.data
            )

        if not current_user.is_admin and old_mail != form.mail.data:
            user.confirm_mail_start()
            flash('E-Mail changed, new confirmation required. Check your mails', 'warning')

        flash('User information changed', 'success')
        return redirect(back_url)

    if not form.username.data:
        form.username.data = user.username
        form.givenName.data = user.firstName
        form.surname.data = user.surname
        form.mail.data = user.mail

    return render_template('admin/editUser.html',
        form = form,
        user = user
    )
