from flask import render_template, redirect, url_for, flash
from . import registration_blueprint
from app.db import db
from .models import Uni, Registration
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from app.user import groups_sufficient

from . import api

class UniForm(FlaskForm):
    name = StringField('Uni Name')
    token = StringField('Token')
    submit = SubmitField()

@registration_blueprint.route('/admin/uni')
@groups_sufficient('admin', 'orga')
def unis():
    unis = Uni.query.all()
    return render_template('admin/unis.html', unis = unis)

@registration_blueprint.route('/admin/uni/new', methods=['GET', 'POST'])
@groups_sufficient('admin', 'orga')
def add_uni():
    form = UniForm()
    if form.validate_on_submit():
        uni = Uni(form.name.data, form.token.data)
        db.session.add(uni)
        try:
            db.session.commit()
        except IntegrityError as e:
            if 'uni.name' in str(e.orig):
                form.name.errors.append("There is already a uni with that name")
            elif 'uni.token' in str(e.orig):
                form.token.errors.append("There is already a uni with that token")
            else:
                raise
            return render_template('admin/uniform.html', form = form)
        return redirect(url_for('registration.unis'))
    return render_template('admin/uniform.html', form = form)

@registration_blueprint.route('/admin/uni/<int:uni_id>/delete')
@groups_sufficient('admin', 'orga')
def delete_uni(uni_id):
    uni = Uni.query.filter_by(id=uni_id).first()
    flash('Deleted {uni.name}'.format(uni=uni))
    db.session.delete(uni)
    db.session.commit()
    return redirect(url_for('registration.unis'))

@registration_blueprint.route('/admin/uni/<int:uni_id>/edit', methods=['GET', 'POST'])
@groups_sufficient('admin', 'orga')
def edit_uni(uni_id):
    uni = Uni.query.filter_by(id=uni_id).first()
    form = UniForm(name = uni.name, token = uni.token)
    if form.validate_on_submit():
        from sqlalchemy.exc import IntegrityError
        uni = Uni(form.name.data, form.token.data)
        db.session.add(uni)
        try:
            db.session.commit()
        except IntegrityError as e:
            if 'uni.name' in str(e.orig):
                form.name.errors.append("There is already a uni with that name")
            elif 'uni.token' in str(e.orig):
                form.token.errors.append("There is already a uni with that token")
            else:
                raise
            return render_template('admin/uniform.html', form = form)
        return redirect(url_for('registration.unis'))
    return render_template('admin/uniform.html', form = form)

@registration_blueprint.route('/admin/registration')
@groups_sufficient('admin', 'orga')
def registrations():
    registrations = Registration.query.all()
    return render_template('admin/registrations.html',
        registrations = registrations,
        uni = None
    )

@registration_blueprint.route('/admin/uni/<int:uni_id>/registrations')
@groups_sufficient('admin', 'orga')
def registrations_by_uni(uni_id):
    registrations = Registration.query.filter_by(uni_id=uni_id).all()
    return render_template('admin/registrations.html',
        registrations = registrations,
        uni = Uni.query.filter_by(id=uni_id).first()
    )

@registration_blueprint.route('/admin/registration/<int:reg_id>/delete')
@groups_sufficient('admin', 'orga')
def delete_registration(reg_id):
    reg = Registration.query.filter_by(id=reg_id).first()
    flash('Deleted {registration.username}\'s registration'.format(registration=reg))
    db.session.delete(reg)
    db.session.commit()
    return redirect(url_for('registration.registrations'))
