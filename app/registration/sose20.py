from flask import render_template, jsonify, Response, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from . import registration_blueprint
from .models import Registration, Uni
from app.user import groups_sufficient
from app.db import db
import io
import csv

EXKURSIONEN_TYPES = {
  'egal': ('ist mir egal', -1, 'Egal'),
  'keine': ('keine exkursion', -1, 'Keine'),
  'ipg': ('IPG Photonics', 20, 'IPG'),
  'nch': ('Neurochirurgie', 0, 'Neurochirurgie'),
  'km': ('Krueckemeyer Klebstoffe', 20, 'Krueckemeyer'),
  'ejot': ('EJOT Schrauben', 20, 'EJOT'),
  'lennestadt': ('Sauerland-Pyramiden', 30, 'Sauerland'),
  'vbsi': ('Versorgungsbetriebe Siegen', 20, 'Versorgungsbetriebe'),
  'fokos': ('FoKoS', 20, 'FoKoS'),
  'bwf': ('Bergwerksfuehrung', 30, 'Bergwerk'),
  'stf': ('Stadtführung', 20, 'Stadtführung'),
  'wandern': ('Wandern', 30, 'Wandern'),
  'lan': ('LAN Party', 0, 'LAN Party'),
  'nospace': ('Konnte keiner Exkursion zugeordnet werden', -1, 'Noch offen'),
}

EXKURSIONEN_FIELD_NAMES = ['exkursion1', 'exkursion2', 'exkursion3', 'exkursion4']

EXKURSIONEN_TYPES_BIRTHDAY = []

EXKURSIONEN_TYPES_FORM = [('nooverwrite', '')] + [(name, data[0]) for name, data in EXKURSIONEN_TYPES.items()]

TSHIRTS_TYPES = {
  'keins': 'Nein, ich möchte keins',
  'fitted_5xl': 'fitted 5XL',
  'fitted_4xl': 'fitted 4XL',
  'fitted_3xl': 'fitted 3XL',
  'fitted_xxl': 'fitted XXL',
  'fitted_xl': 'fitted XL',
  'fitted_l': 'fitted L',
  'fitted_m': 'fitted M',
  'fitted_s': 'fitted S',
  'fitted_xs': 'fitted XS',
  '5xl': '5XL',
  '4xl': '4XL',
  '3xl': '3XL',
  'xxl': 'XXL',
  'xl': 'XL',
  'l': 'L',
  'm': 'M',
  's': 'S',
  'xs': 'XS'
}

ESSEN_TYPES = {
  'vegetarisch': 'Vegetarisch',
  'vegan': 'Vegan',
  'omnivor': 'Omnivor'
}

HEISSE_GETRAENKE_TYPES = {
  'egal': 'Egal',
  'kaffee': 'Kaffee',
  'tee': 'Tee'
}

SCHLAFEN_TYPES = {
  'nachteule': 'Nachteule',
  'morgenmuffel': 'Morgenmuffel',
  'vogel': 'Früher Vogel'
}

MITTAG1_TYPES = {
  'vegan': 'Gemüseschnitzel mit Kräutersoße',
  'normal': 'Schnitzel mit Rahmsoße'
}

MITTAG2_TYPES = {
  'vegan': 'Sojaschnitzel mit Nudeln',
  'normal': 'Hähnchen mit Nudeln'
}

MITTAG3_TYPES = {
  'vegan': 'veg. Currywurst',
  'normal': 'Currywurst'
}

ANREISE_TYPES = {
  'bus': 'Fernbus',
  'bahn': 'Zug',
  'auto': 'Auto',
  'flug': 'Flugzeug',
  'fahrrad': 'Fahrrad',
  'einhorn': 'Einhorn',
  'uboot': 'U-Boot'
}

class Winter17ExkursionenOverwriteForm(FlaskForm):
    spitzname = StringField('Spitzname')
    exkursion_overwrite = SelectField('Exkursionen Festlegung', choices=EXKURSIONEN_TYPES_FORM)
    submit = SubmitField()

def wise17_calculate_exkursionen(registrations):
    def get_sort_key(reg):
        return reg.id
    result = {}
    regs_later = []
    regs_overwritten = [reg for reg in registrations
                            if 'exkursion_overwrite' in reg.data and reg.data['exkursion_overwrite'] != 'nooverwrite']
    regs_normal = sorted(
                    [reg for reg in registrations
                         if not ('exkursion_overwrite' in reg.data) or reg.data['exkursion_overwrite'] == 'nooverwrite'],
                    key = get_sort_key
                  )
    for type_name, type_data in EXKURSIONEN_TYPES.items():
        result[type_name] = {'space': type_data[1], 'free': type_data[1], 'registrations': []}
    for reg in regs_overwritten:
        exkursion_selected = reg.data['exkursion_overwrite']
        if not result[exkursion_selected]:
            return None
        result[exkursion_selected]['registrations'].append((reg, -1))
        result[exkursion_selected]['free'] -= 1
    for reg in regs_normal:
        if reg.uni.name == 'Universitas Saccos Veteres':
            regs_later.append(reg)
            continue;
        got_slot = False
        for field_index, field in enumerate(EXKURSIONEN_FIELD_NAMES):
            exkursion_selected = reg.data[field]
            if exkursion_selected == 'vbsi':
                result['vbsi']['registrations'].append((reg, field_index))
                result['vbsi']['free'] -= 1
                got_slot = True
                break;
            elif exkursion_selected == 'ejot':
                result['ejot']['registrations'].append((reg, field_index))
                result['ejot']['free'] -= 1
                got_slot = True
                break;
            elif exkursion_selected == 'km':
                result['km']['registrations'].append((reg, field_index))
                result['km']['free'] -= 1
                got_slot = True
                break;
        if not got_slot:
            for field_index, field in enumerate(EXKURSIONEN_FIELD_NAMES):
                exkursion_selected = reg.data[field]
                if not result[exkursion_selected]:
                    return None
                if result[exkursion_selected]['space'] == -1 or result[exkursion_selected]['free'] > 0:
                    result[exkursion_selected]['registrations'].append((reg, field_index))
                    result[exkursion_selected]['free'] -= 1
                    got_slot = True
                    break;
        if not got_slot:
            result['nospace']['registrations'].append((reg, len(EXKURSIONEN_FIELD_NAMES) + 1))
    for reg in regs_later:
        for field_index, field in enumerate(EXKURSIONEN_FIELD_NAMES):
            exkursion_selected = reg.data[field]
            if exkursion_selected == 'vbsi':
                result['vbsi']['registrations'].append((reg, field_index))
                result['vbsi']['free'] -= 1
                got_slot = True
                break;
            elif exkursion_selected == 'ejot':
                result['ejot']['registrations'].append((reg, field_index))
                result['ejot']['free'] -= 1
                got_slot = True
                break;
            elif exkursion_selected == 'km':
                result['km']['registrations'].append((reg, field_index))
                result['km']['free'] -= 1
                got_slot = True
                break;
        if not got_slot:
            for field_index, field in enumerate(EXKURSIONEN_FIELD_NAMES):
                exkursion_selected = reg.data[field]
                if not result[exkursion_selected]:
                    return None
                if result[exkursion_selected]['space'] == -1 or result[exkursion_selected]['free'] > 0:
                    result[exkursion_selected]['registrations'].append((reg, field_index))
                    result[exkursion_selected]['free'] -= 1
                    break;
        if not got_slot:
            result['nospace']['registrations'].append((reg, len(EXKURSIONEN_FIELD_NAMES) + 1))
    return result

@registration_blueprint.route('/admin/registration/report/sose20')
@groups_sufficient('admin', 'orga')
def registration_sose20_reports():
    return render_template('admin/sose20/reports.html')

from app.db import db
from .models import Uni, Registration, Mascot
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.fields.html5 import IntegerField
from app.user import groups_sufficient
from app.views import confirm
from flask_babel import gettext
import io
import csv

from . import api, wise17, sose20

class UniForm(FlaskForm):
    name = StringField(gettext('Uni Name'))
    token = StringField(gettext('Token'))
    slots = IntegerField(gettext('Slots'), default=3)
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
