from flask import render_template, jsonify, Response, redirect, url_for, current_app
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from . import registration_blueprint
from .models import Registration, Uni
from app.user import groups_sufficient
from app.db import db
from app.cache import cache
from datetime import datetime
import pytz
import io
import csv

TSHIRTS_TYPES = {
  'keins': 'Keines',
#  'fitted_5xl': 'fitted 5XL',
#  'fitted_4xl': 'fitted 4XL',
#  'fitted_3xl': 'fitted 3XL',
#  'fitted_xxl': 'fitted XXL',
#  'fitted_xl': 'fitted XL',
#  'fitted_l': 'fitted L',
#  'fitted_m': 'fitted M',
#  'fitted_s': 'fitted S',
#  'fitted_xs': 'fitted XS',
#  '5xl': '5XL',
#  '4xl': '4XL',
  '3xl': '3XL',
  'xxl': 'XXL',
  'xl': 'XL',
  'l': 'L',
  'm': 'M',
  's': 'S',
  'xs': 'XS'
}

HOODIE_TYPES = {
  'keins': 'Keiner',
#  'fitted_5xl': 'fitted 5XL',
#  'fitted_4xl': 'fitted 4XL',
#  'fitted_3xl': 'fitted 3XL',
#  'fitted_xxl': 'fitted XXL',
#  'fitted_xl': 'fitted XL',
#  'fitted_l': 'fitted L',
#  'fitted_m': 'fitted M',
#  'fitted_s': 'fitted S',
#  'fitted_xs': 'fitted XS',
#  '5xl': '5XL',
#  '4xl': '4XL',
  '3xl': '3XL',
  'xxl': 'XXL',
  'xl': 'XL',
  'l': 'L',
  'm': 'M',
  's': 'S',
  'xs': 'XS'
}

ANREISE_TYPES = {
  'bus': 'Fernbus',
  'bahn': 'Zug',
  'auto': 'Auto',
#  'flug': 'Flugzeug',
  'zeitmaschine': 'Zeitmaschine',
  'boot': 'Boot',
  'fahrrad': 'Fahrrad',
  'badeente': 'Badeente',
}

SCHWIMMEN_TYPES = {
    'keins': 'keins',
    'bleiente': 'Bleiente',
    'seepferd': 'Seepferdchen',
    'bronze': 'Bronze',
    'silber': 'Silber',
    'gold': 'Gold',
    'rett': 'Rettungsschwimmer*in',
}

def attachment(response, filename):
    response.headers['Content-Disposition'] = 'attachment; filename="{0}"'.format(filename)
    return response

def get_datetime_string():
    return datetime.now(tz=pytz.timezone('Europe/Berlin')).strftime('%d.%m.%Y %H:%M:%S %Z')

@registration_blueprint.route('/admin/registration/report/clear/<target>')
def registration_sose21_report_clear(target):
    if target == 'all':
        cache.clear()
        return redirect(url_for('registration.registration_sose21_reports'))
    else:
        cache.delete("view/{0}".format(url_for(target)))
        return redirect(url_for(target))

@registration_blueprint.route('/admin/registration/report/sose21')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_sose21_reports():
    datetime_string = get_datetime_string() 
    registrations = Registration.query.all()
    confirmed = [reg for reg in registrations if reg.confirmed]
    attendees = [reg for reg in registrations if reg.is_zapf_attendee]
    gremika = [reg for reg in attendees if reg.is_guaranteed]
    return render_template('admin/sose21/reports.html',
        registrations=len(registrations),
        attendees=len(attendees),
        confirmed=len(confirmed),
        gremika=len(gremika),
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/sose21/t-shirts')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_sose21_report_tshirts():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    unis = Uni.query.order_by(Uni.id)
    result = {}
    result_unis = {}
    for uni in unis:
        result_unis[uni.id] = {
            'name': uni.name,
            'registrations': [],
            'types': {name: 0 for name, label in TSHIRTS_TYPES.items()}
        }
    for name, label in TSHIRTS_TYPES.items():
        result[name] = {'label': label, 'registrations': []}
    for reg in registrations:
        tshirt_size = reg.data['tshirt']
        if not result[tshirt_size]:
            return None
        result[tshirt_size]['registrations'].append(reg)
        result_unis[reg.uni.id]['registrations'].append(reg)
        result_unis[reg.uni.id]['types'][tshirt_size] += 1
    return render_template('admin/sose21/t-shirts.html',
        result = result,
        result_unis = result_unis,
        TSHIRTS_TYPES = TSHIRTS_TYPES,
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/sose21/hoodie')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_sose21_report_hoodie():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    unis = Uni.query.order_by(Uni.id)
    result = {}
    result_unis = {}
    for uni in unis:
        result_unis[uni.id] = {
            'name': uni.name,
            'registrations': [],
            'types': {name: 0 for name, label in HOODIE_TYPES.items()}
        }
    for name, label in HOODIE_TYPES.items():
        result[name] = {'label': label, 'registrations': []}
    for reg in registrations:
        hoodie_size = reg.data['hoodie']
        if not result[hoodie_size]:
            return None
        result[hoodie_size]['registrations'].append(reg)
        result_unis[reg.uni.id]['registrations'].append(reg)
        result_unis[reg.uni.id]['types'][hoodie_size] += 1
    return render_template('admin/sose21/hoodie.html',
        result = result,
        result_unis = result_unis,
        HOODIE_TYPES = HOODIE_TYPES,
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/sose21/merch')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_sose21_report_merch():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    unis = Uni.query.order_by(Uni.id)
    result = {
        'shirts': {},
        'hoodies': {},
        'towels': [],
        'mugs': [],
        'usbs': [],
        'frisbees': [],
        'patches': [],
        'scarves': [],
    }
    result_unis = {}
    for uni in unis:
        result_unis[uni.id] = {
            'name': uni.name,
            'registrations': [],
            'shirts': {name: 0 for name, label in TSHIRTS_TYPES.items()},
            'hoodies': {name: 0 for name, label in HOODIE_TYPES.items()},
            'towels': 0,
            'mugs': 0,
            'usbs': 0,
            'frisbees': 0,
            'patches': 0,
            'scarves': 0,
        }
    for name, label in TSHIRTS_TYPES.items():
        result['shirts'][name] = {'label': label, 'amount': 0, 'requests': []}
    for name, label in HOODIE_TYPES.items():
        result['hoodies'][name] = {'label': label, 'amount': 0, 'requests': []}
    for reg in registrations:
        tshirt_size = reg.data['tshirt']
        tshirt_amount = reg.data['addtshirt'] + 1 if reg.data['addtshirt'] else 1
        hoodie_size = reg.data['hoodie']
        if not result['shirts'][tshirt_size] or not result['hoodies'][hoodie_size]:
            return None
        if reg.data['handtuch']:
            result['towels'].append(reg)
            result_unis[reg.uni.id]['towels'] += 1
        if reg.data['tasse']:
            result['mugs'].append(reg)
            result_unis[reg.uni.id]['mugs'] += 1
        if reg.data['usb']:
            result['usbs'].append(reg)
            result_unis[reg.uni.id]['usbs'] += 1
        if reg.data['frisbee']:
            result['frisbees'].append(reg)
            result_unis[reg.uni.id]['frisbees'] += 1
        if reg.data['aufnaeher']:
            result['patches'].append(reg)
            result_unis[reg.uni.id]['patches'] += 1
        if reg.data['schal']:
            result['scarves'].append(reg)
            result_unis[reg.uni.id]['scarves'] += 1
        result['shirts'][tshirt_size]['amount'] += tshirt_amount
        result['shirts'][tshirt_size]['requests'].append({'registration': reg, 'amount': tshirt_amount})
        result['hoodies'][hoodie_size]['amount'] += 1
        result['hoodies'][hoodie_size]['requests'].append({'registration': reg, 'amount': 1})
        result_unis[reg.uni.id]['registrations'].append(reg)
        result_unis[reg.uni.id]['shirts'][tshirt_size] += tshirt_amount
        result_unis[reg.uni.id]['hoodies'][hoodie_size] += 1
    return render_template('admin/sose21/merch.html',
        result = result,
        result_unis = result_unis,
        TSHIRTS_TYPES = TSHIRTS_TYPES,
        HOODIE_TYPES = HOODIE_TYPES,
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/sose21/rahmenprogramm')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_sose21_report_rahmenprogramm():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result_musikwunsch = []
    result_inbound = {}
    for key in ANREISE_TYPES: result_inbound[key] = []
    for reg in registrations:
        musikwunsch = reg.data['musikwunsch']
        anreise = reg.data['anreise_verkehr']
        if musikwunsch:
            result_musikwunsch.append(reg)
        if anreise in ANREISE_TYPES.keys():
            result_inbound[anreise].append(reg)
    return render_template('admin/sose21/rahmenprogramm.html',
        result_musikwunsch = result_musikwunsch,
        result_inbound = result_inbound,
        datetime_string = datetime_string,
        ANREISE_TYPES = ANREISE_TYPES,
    )

@registration_blueprint.route('/admin/registration/report/sose21/roles')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_sose21_report_roles():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result = {}
    result_keys = ['trustee', 'minuteman', 'mentee', 'mentor', 'notmentee']
    for key in result_keys: result[key] = []
    for reg in registrations:
        if reg.data['vertrauensperson'] == 'ja': result['trustee'].append(reg) 
        if reg.data['protokoll'] == 'ja': result['minuteman'].append(reg) 
        if reg.data['zaepfchen'] == 'ja': result['notmentee'].append(reg) 
        if reg.data['zaepfchen'] == 'jamentor': result['mentee'].append(reg) 
        if reg.data['mentor']: result['mentor'].append(reg) 
    return render_template('admin/sose21/roles.html',
        result = result,
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/sose21/sonstiges')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_sose21_report_sonstiges():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result = {}
    result['comment'] = []
    
    for reg in registrations:
        if reg.data['kommentar']: result['comment'].append(reg)
    return render_template('admin/sose21/sonstiges.html',
        result = result,
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/<int:reg_id>/details_sose21', methods=['GET', 'POST'])
@groups_sufficient('admin', 'orga')
def registration_sose21_details_registration(reg_id):
    reg = Registration.query.filter_by(id=reg_id).first()
    if reg.is_guaranteed:
        current_app.logger.debug(reg.user.groups)
    return render_template('admin/sose21/details.html',
        reg = reg,
        TSHIRTS_TYPES = TSHIRTS_TYPES,
        HOODIE_TYPES = HOODIE_TYPES,
        ANREISE_TYPES = ANREISE_TYPES,
        SCHWIMMEN_TYPES = SCHWIMMEN_TYPES,
    )

@registration_blueprint.route('/admin/registration/report/sose21/stimmkarten/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_sose21_export_stimmkarten_latex():
    unis = Uni.query.all()
    result = []
    for uni in unis:
        uni_regs = [reg for reg in Registration.query.filter_by(uni_id = uni.id) if reg.is_zapf_attendee]
        if len(uni_regs) > 0:
            result.append("\\stimmkarte{{{0}}}".format(uni.name))
    return attachment(Response("\n".join(result), mimetype="application/x-latex"), 'stimmkarten.tex')

@registration_blueprint.route('/admin/registration/report/sose21/idkarten/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_sose21_export_idkarten_latex():
    result = ["\\idcard{{{}}}{{{}}}{{{}}}".format(reg.id, reg.user.full_name, reg.uni.name)
                for reg in Registration.query.order_by(Registration.uni_id) if reg.is_zapf_attendee]
    return attachment(Response("\n".join(result), mimetype="application/x-latex"), 'idkarten.tex')

@registration_blueprint.route('/admin/registration/report/sose21/tagungsausweise/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_sose21_export_tagungsausweise_latex():
    def get_sort_key(entry):
        return entry[0]
    registrations = [reg for reg in Registration.query.all() if reg.is_zapf_attendee]
    result_exkursionen = sose21_calculate_exkursionen(registrations)
    result = []
    result_alumni = []
    for name, data in result_exkursionen.items():
        for reg in data['registrations']:
            if reg[0].uni.name == "Alumni":
                ausweis_type = "\\ausweisalumni"
            else:
                ausweis_type = "\\ausweis"
            result.append((reg[0].uni_id, "{type}{{{spitzname}}}{{{name}}}{{{uni}}}{{{id}}}{{{exkursion}}}".format(
              type = ausweis_type,
              spitzname = reg[0].data['spitzname'] or reg[0].user.firstName,
              name = reg[0].user.full_name,
              uni = reg[0].uni.name,
              id = reg[0].id,
              exkursion = EXKURSIONEN_TYPES[name][2]
            )))
    result = sorted(result, key = get_sort_key)
    result = [data[1] for data in result]
    return attachment(Response("\n".join(result), mimetype="application/x-latex"), 'tagungsausweise.tex')

@registration_blueprint.route('/admin/registration/report/sose21/strichlisten/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_sose21_export_strichlisten_latex():
    registrations = [reg for reg in Registration.query.order_by(Registration.uni_id) if reg.is_zapf_attendee]
    i = 0
    result = []
    for reg in registrations:
        if i == 0:
            result.append("\\strichliste{")
        result.append("{} & {} & \\\\[0.25cm] \\hline".format(reg.user.full_name, reg.uni.name))
        i += 1
        if i == 34:
            result.append("}")
            i = 0
    result.append("}")
    return attachment(Response("\n".join(result), mimetype="application/x-latex"), 'strichlisten.tex')

@registration_blueprint.route('/admin/registration/report/sose21/bmbflisten/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_sose21_export_bmbflisten_latex():
    registrations = [reg for reg in Registration.query.order_by(Registration.uni_id) if reg.is_zapf_attendee]
    i = 0
    lfd_nr = 1
    result = []
    for reg in registrations:
        if reg.uni.name == "Alumni":
            continue;
        if i == 0:
            result.append("\\bmbfpage{")
        result.append("{} & {} & {} &&& \\\\[0.255cm] \\hline".format(lfd_nr, reg.user.full_name, reg.uni.name))
        i += 1
        lfd_nr += 1
        if i == 20:
            result.append("}")
            i = 0
    result.append("}")
    return attachment(Response("\n".join(result), mimetype="application/x-latex"), 'bmbflisten.tex')

@registration_blueprint.route('/admin/registration/report/sose21/taschentassenlisten/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_sose21_export_taschentassenlisten_latex():
    registrations = [reg for reg in Registration.query.order_by(Registration.uni_id) if reg.is_zapf_attendee]
    i = 0
    result = []
    for reg in registrations:
        if i == 0:
            result.append("\\tassentaschen{")
        result.append("{} & {} && \\\\[0.25cm] \\hline".format(reg.user.full_name, reg.uni.name))
        i += 1
        if i == 34:
            result.append("}")
            i = 0
    if i != 0:
        result.append("}")
    return attachment(Response("\n".join(result), mimetype="application/x-latex"), 'taschentassenlisten.tex')

@registration_blueprint.route('/admin/registration/report/sose21/ausweisidbeitraglisten/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_sose21_export_ausweisidbeitraglisten_latex():
    registrations = [reg for reg in Registration.query.order_by(Registration.uni_id) if reg.is_zapf_attendee]
    i = 0
    result = []
    for reg in registrations:
        if i == 0:
            result.append("\\ausweisidbeitrag{")
        result.append("{} & {} &&& \\\\[0.25cm] \\hline".format(reg.user.full_name, reg.uni.name))
        i += 1
        if i == 34:
            result.append("}")
            i = 0
    if i != 0:
        result.append("}")
    return attachment(Response("\n".join(result), mimetype="application/x-latex"), 'ausweisidbeitraglisten.tex')

@registration_blueprint.route('/admin/registration/report/sose21/t-shirt/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_sose21_export_t_shirt_latex():
    registrations = [reg for reg in Registration.query.order_by(Registration.uni_id) if reg.is_zapf_attendee]
    i = 0
    result = []
    for reg in registrations:
        if i == 0:
            result.append("\\tshirt{")
        result.append("{} & {} & {} \\\\[0.25cm] \\hline".format(reg.user.full_name, reg.uni.name, reg.data["tshirt"]))
        i += 1
        if i == 34:
            result.append("}")
            i = 0
    if i != 0:
        result.append("}")
    return attachment(Response("\n".join(result), mimetype="application/x-latex"), 'shirts.tex')

@registration_blueprint.route('/admin/registration/report/sose21/wichteln/csv')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registrations_sose21_export_wichteln_csv():
    registrations = Registration.query.all()
    result = io.StringIO()
    writer = csv.writer(result, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows([[reg.user.full_name, reg.uni.name, reg.data['spitzname']]
                      for reg in registrations if reg.is_zapf_attendee])
    return attachment(Response(result.getvalue(), mimetype='text/csv'), 'wichteln.csv')

@registration_blueprint.route('/admin/registration/report/sose21/exkursionen/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_sose21_export_exkursionen_latex():
    registrations = [reg for reg in Registration.query.all() if reg.is_zapf_attendee]
    result_exkursionen = sose21_calculate_exkursionen(registrations)
    result = []
    for name, data in result_exkursionen.items():
        buffer = ["\\exkursionspage{{{type}}}{{".format(type=EXKURSIONEN_TYPES[name][2])]
        for reg in data['registrations']:
            buffer.append("{} & {} \\\\ \\hline".format(reg[0].user.full_name, reg[0].uni.name))
        buffer.append("}")
        result.append("\n".join(buffer))
    return attachment(Response("\n".join(result), mimetype="application/x-latex"), 'exkursionen.tex')

@registration_blueprint.route('/admin/registration/report/sose21/unis/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_sose21_export_unis_latex():
    unis = Uni.query.all()
    result = []
    for uni in unis:
        uni_regs = [reg for reg in Registration.query.filter_by(uni_id = uni.id) if reg.is_zapf_attendee]
        if len(uni_regs) > 0:
            result.append("\\item{{{0}}}".format(uni.name))
    return attachment(Response("\n".join(result), mimetype="application/x-latex"), 'unis.tex')

@registration_blueprint.route('/admin/registration/report/sose21/unis-teilnehmer/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_sose21_export_unis_teilnehmer_latex():
    unis = Uni.query.all()
    result = []
    for uni in unis:
        uni_regs = [reg for reg in Registration.query.filter_by(uni_id = uni.id) if reg.is_zapf_attendee]
        if len(uni_regs) > 0:
            result.append("\\item{{{0} - {1}}}".format(uni.name, len(uni_regs)))
    return attachment(Response("\n".join(result), mimetype="application/x-latex"), 'unis-tn.tex')

@registration_blueprint.route('/admin/registration/report/sose21/bestaetigungen/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_sose21_export_bestaetigungen_latex():
    registrations = [reg for reg in Registration.query.order_by(Registration.uni_id) if reg.is_zapf_attendee]
    result = []
    for reg in registrations:
        result.append("\\bestaetigung{{{}}}{{{}}}".format(reg.user.full_name, reg.uni.name))
    return attachment(Response("\n".join(result), mimetype="application/x-latex"), 'bestaetigungen.tex')

@registration_blueprint.route('/admin/registration/report/sose21/id_name/csv')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registrations_sose21_export_id_name_csv():
    registrations = Registration.query.all()
    result = io.StringIO()
    writer = csv.writer(result, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows([[reg.id, "{} ({})".format(reg.user.full_name, reg.uni.name)]
                      for reg in registrations if reg.is_zapf_attendee])
    return attachment(Response(result.getvalue(), mimetype='text/csv'), 'id_name.csv')
