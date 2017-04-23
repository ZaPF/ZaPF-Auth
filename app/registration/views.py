from flask import render_template, redirect, url_for, flash, jsonify, Response
from . import registration_blueprint
from app.db import db
from .models import Uni, Registration
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.fields.html5 import IntegerField
from app.user import groups_sufficient
from app.views import confirm
import io
import csv

from . import api, sose17

class UniForm(FlaskForm):
    name = StringField('Uni Name')
    token = StringField('Token')
    slots = IntegerField('Token', default=3)
    submit = SubmitField()

@registration_blueprint.route('/admin/uni')
@groups_sufficient('admin', 'orga')
def unis():
    unis = Uni.query.all()
    unis_registrations = {}
    for uni in unis:
        registrations = Registration.query.filter_by(uni_id=uni.id).all()
        unis_registrations[uni.id] = {
            'total': len(registrations),
            'confirmed': sum(reg.confirmed for reg in registrations),
            'gremien': sum(reg.priority == -1 for reg in registrations)
        }
    return render_template('admin/unis.html',
        unis = unis,
        unis_registrations = unis_registrations
    )

@registration_blueprint.route('/admin/uni/new', methods=['GET', 'POST'])
@groups_sufficient('admin', 'orga')
def add_uni():
    form = UniForm()
    if form.validate_on_submit():
        uni = Uni(form.name.data, form.token.data, form.slots.data or 3)
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

@registration_blueprint.route('/admin/uni/<int:uni_id>/delete', methods=['GET', 'POST'])
@groups_sufficient('admin', 'orga')
@confirm(title='Delete university',
        action='Delete',
        back='registration.unis')
def delete_uni(uni_id):
    uni = Uni.query.filter_by(id=uni_id).first()
    db.session.delete(uni)
    db.session.commit()
    flash('Deleted university "{}"'.format(uni.name), 'success')
    return redirect(url_for('registration.unis'))

@registration_blueprint.route('/admin/uni/<int:uni_id>/edit', methods=['GET', 'POST'])
@groups_sufficient('admin', 'orga')
def edit_uni(uni_id):
    uni = Uni.query.filter_by(id=uni_id).first()
    form = UniForm(name = uni.name, token = uni.token, slots = uni.slots)
    if form.validate_on_submit():
        from sqlalchemy.exc import IntegrityError
        uni.name = form.name.data
        uni.token = form.token.data
        uni.slots = form.slots.data
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

@registration_blueprint.route('/admin/uni/<int:uni_id>/slots/increase')
@groups_sufficient('admin', 'orga')
def uni_slots_increase(uni_id):
    uni = Uni.query.filter_by(id=uni_id).first()
    uni.slots = uni.slots + 1
    db.session.add(uni)
    db.session.commit()
    return redirect(url_for('registration.unis'))

@registration_blueprint.route('/admin/uni/<int:uni_id>/slots/decrease')
@groups_sufficient('admin', 'orga')
def uni_slots_decrease(uni_id):
    uni = Uni.query.filter_by(id=uni_id).first()
    uni.slots = uni.slots - 1
    db.session.add(uni)
    db.session.commit()
    return redirect(url_for('registration.unis'))

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

@registration_blueprint.route('/admin/registration/<int:reg_id>/delete', methods=['GET', 'POST'])
@groups_sufficient('admin', 'orga')
@confirm(title='Delete registration',
        action='Delete registration',
        back='registration.registrations')
def delete_registration(reg_id):
    reg = Registration.query.filter_by(id=reg_id).first()
    db.session.delete(reg)
    db.session.commit()
    flash('Deleted {}\'s registration'.format(reg.username))
    return redirect(url_for('registration.registrations'))

@registration_blueprint.route('/admin/registration/export/json')
@groups_sufficient('admin', 'orga')
def registrations_export_json():
    registrations = Registration.query.all()
    return jsonify(registrations = [
        {
         'username': reg.username,
         'mail': reg.user.mail,
         'firstName': reg.user.firstName,
         'surname': reg.user.surname,
         'uni_name': reg.uni.name,
         'is_guaranteed': reg.is_guaranteed,
         'confirmed': reg.confirmed,
         'priority': reg.priority,
         'is_zapf_attendee': reg.is_zapf_attendee,
         'blob': reg.blob
        }
        for reg in registrations
    ])

@registration_blueprint.route('/admin/registration/export/csv')
@groups_sufficient('admin', 'orga')
def registrations_export_csv():
    registrations = Registration.query.order_by(Registration.uni_id).all()
    result = io.StringIO()
    writer = csv.writer(result, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows([[reg.username, reg.user.mail, reg.user.firstName,
                       reg.user.surname, reg.uni.name, reg.is_guaranteed,
                       reg.confirmed, reg.priority, reg.is_zapf_attendee, reg.blob]
                      for reg in registrations])
    return Response(result.getvalue(), mimetype='text/csv')

@registration_blueprint.route('/admin/registration/export/openslides/csv')
@groups_sufficient('admin', 'orga')
def registrations_export_openslides_csv():
    registrations = Registration.query.all()
    result = io.StringIO()
    writer = csv.writer(result, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows([[None, reg.user.firstName, reg.user.surname, reg.uni.name,
                       reg.id, 'Teilnehmikon', None, None, 1, None, None]
                      for reg in registrations if reg.is_zapf_attendee])
    return Response(result.getvalue(), mimetype='text/csv')

@registration_blueprint.route('/admin/registration/export/teilnehmer/csv')
@groups_sufficient('admin', 'orga')
def registrations_export_teilnehmer_csv():
    registrations = Registration.query.order_by(Registration.uni_id)
    result = io.StringIO()
    writer = csv.writer(result, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows([[reg.user.full_name, reg.uni.name]
                      for reg in registrations if reg.is_zapf_attendee])
    return Response(result.getvalue(), mimetype='text/csv')

@registration_blueprint.route('/admin/registration/export/mails/txt')
@groups_sufficient('admin', 'orga')
def registrations_export_mails_txt():
    result =  [reg.user.mail for reg in Registration.query.all() if reg.is_zapf_attendee]
    return Response("\n".join(result), mimetype='text/plain')

@registration_blueprint.route('/admin/registration/export/attendee/csv')
@groups_sufficient('admin', 'orga')
def registrations_export_attendee_csv():
    registrations = [reg for reg in Registration.query.order_by(Registration.uni_id).all() if reg.is_zapf_attendee]
    result = io.StringIO()
    writer = csv.writer(result, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows([[reg.username, reg.user.mail, reg.user.firstName,
                       reg.user.surname, reg.uni.name, reg.is_guaranteed,
                       reg.confirmed, reg.priority, reg.is_zapf_attendee]
                      for reg in registrations])
    return Response(result.getvalue(), mimetype='text/csv')
