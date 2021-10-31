from flask import render_template, redirect, url_for, flash, jsonify, Response
from . import registration_blueprint
from app.db import db
from .models import Uni, Registration, Mascot
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.fields.html5 import IntegerField
from app.user import groups_sufficient
from app.views import confirm
from app.cache import cache
from flask_babel import gettext
import io
import csv

from . import api, wise21

class UniForm(FlaskForm):
    name = StringField(gettext('Uni Name'))
    token = StringField(gettext('Token'))
    slots = IntegerField(gettext('Slots'), default=3)
    submit = SubmitField()

def attachment(response, filename):
    response.headers['Content-Disposition'] = 'attachment; filename="{0}"'.format(filename)
    return response

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
                form.name.errors.append(gettext("There is already a uni with that name"))
            elif 'uni.token' in str(e.orig):
                form.token.errors.append(gettext("There is already a uni with that token"))
            else:
                raise
            return render_template('admin/uniform.html', form = form)
        return redirect(url_for('registration.unis'))
    return render_template('admin/uniform.html', form = form)

@registration_blueprint.route('/admin/uni/<int:uni_id>/delete', methods=['GET', 'POST'])
@groups_sufficient('admin', 'orga')
@confirm(title=gettext('Delete university'),
        action=gettext('Delete'),
        back='registration.unis')
def delete_uni(uni_id):
    uni = Uni.query.filter_by(id=uni_id).first()
    db.session.delete(uni)
    db.session.commit()
    flash(gettext('Deleted university "%(name)s"', name=uni.name), 'success')
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
                form.name.errors.append(gettext("There is already a uni with that name"))
            elif 'uni.token' in str(e.orig):
                form.token.errors.append(gettext("There is already a uni with that token"))
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
@confirm(title=gettext('Delete registration'),
        action=gettext('Delete registration'),
        back='registration.registrations')
def delete_registration(reg_id):
    reg = Registration.query.filter_by(id=reg_id).first()
    db.session.delete(reg)
    db.session.commit()
    flash(gettext('Deleted %(username)s\'s registration', username=reg.username))
    return redirect(url_for('registration.registrations'))

@registration_blueprint.route('/admin/registration/export/json')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registrations_export_json():
    registrations = Registration.query.all()
    return attachment(jsonify(registrations = [
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
    ]), 'registrations.json')

@registration_blueprint.route('/admin/registration/export/csv')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registrations_export_csv():
    registrations = Registration.query.order_by(Registration.uni_id).all()
    result = io.StringIO()
    writer = csv.writer(result, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows([[reg.username, reg.user.mail, reg.user.firstName,
                       reg.user.surname, reg.uni.name, reg.is_guaranteed,
                       reg.confirmed, reg.priority, reg.is_zapf_attendee, reg.blob]
                      for reg in registrations])
    return attachment(Response(result.getvalue(), mimetype='text/csv'), 'registrations.csv')

@registration_blueprint.route('/admin/registration/export/openslides/csv')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registrations_export_openslides_csv():
    registrations = Registration.query.all()
    result = io.StringIO()
    writer = csv.writer(result, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows([[None, reg.user.firstName, reg.user.surname, reg.uni.name,
                       reg.id, 'Teilnehmikon', None, None, 1, None, None]
                      for reg in registrations if reg.is_zapf_attendee])
    return attachment(Response(result.getvalue(), mimetype='text/csv'), 'openslides.csv')

@registration_blueprint.route('/admin/registration/export/teilnehmer/csv')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registrations_export_teilnehmer_csv():
    registrations = Registration.query.order_by(Registration.uni_id)
    result = io.StringIO()
    writer = csv.writer(result, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows([[reg.user.full_name, reg.uni.name]
                      for reg in registrations if reg.is_zapf_attendee])
    return attachment(Response(result.getvalue(), mimetype='text/csv'), 'attendees.csv')

@registration_blueprint.route('/admin/registration/export/mails/attendees')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registrations_export_mails_attendees():
    result =  [reg.user.mail for reg in Registration.query.all() if reg.is_zapf_attendee]
    return attachment(Response("\n".join(result), mimetype='text/plain'), 'attendee-mails.txt')

@registration_blueprint.route('/admin/registration/export/mails/registrations')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registrations_export_mails_all():
    result =  [reg.user.mail for reg in Registration.query.all()]
    return attachment(Response("\n".join(result), mimetype='text/plain'), 'registration-mails.txt')

@registration_blueprint.route('/admin/registration/export/attendee/csv')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registrations_export_attendee_csv():
    registrations = [reg for reg in Registration.query.order_by(Registration.uni_id).all() if reg.is_zapf_attendee]
    result = io.StringIO()
    writer = csv.writer(result, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows([[reg.username, reg.user.mail, reg.user.firstName,
                       reg.user.surname, reg.uni.name, reg.is_guaranteed,
                       reg.confirmed, reg.priority, reg.is_zapf_attendee]
                      for reg in registrations])
    return attachment(Response(result.getvalue(), mimetype='text/csv'), 'attendees.csv')

@registration_blueprint.route('/admin/mascots')
@groups_sufficient('admin', 'orga')
def mascots():
    mascots = Mascot.query.all()
    return render_template('admin/mascots.html',
        mascots=mascots,
        uni = None
    )

@registration_blueprint.route('/admin/uni/<int:uni_id>/mascots')
@groups_sufficient('admin', 'orga')
def mascots_by_uni(uni_id):
    mascots = Mascot.query.filter_by(uni_id=uni_id).all()
    return render_template('admin/mascots.html',
        mascots = mascots,
        uni = Uni.query.filter_by(id=uni_id).first()
    )

@registration_blueprint.route('/admin/mascots/<int:masc_id>/delete', methods=['GET', 'POST'])
@groups_sufficient('admin', 'orga')
@confirm(title=gettext('Delete mascot'),
        action=gettext('Delete mascot'),
        back='registration.mascots')
def del_mascot(masc_id):
    masc = Mascot.query.filter_by(id=masc_id).first()
    db.session.delete(masc)
    db.session.commit()
    flash(gettext('Deleted %(name)s', name=masc.name))
    return redirect(url_for('registration.mascots'))

@registration_blueprint.route('/admin/mascots/export/json')
@groups_sufficient('admin', 'orga')
@cache.cached()
def mascot_export_json():
    mascots = Registration.query.all()
    return attachment(jsonify(mascots = [
        {
         'name': masc.username,
         'uni_name': masc.uni.name,
        }
        for masc in mascots
    ]), 'mascots.json')

@registration_blueprint.route('/admin/mascots/export/csv')
@groups_sufficient('admin', 'orga')
@cache.cached()
def mascots_export_csv():
    mascots = Mascot.query.order_by(Registration.uni_id).all()
    result = io.StringIO()
    writer = csv.writer(result, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows([[masc.name,reg.uni.name]
                      for masc in mascots])
    return attachment(Response(result.getvalue(), mimetype='text/csv'), 'mascots.csv')




