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

EXKURSIONEN_TYPES = {
  'egal': ('ist mir egal', -1, 'Egal'),
  'keine': ('keine exkursion', -1, 'Keine'),
  'eso': ('ESO - Europäische Südsternwarte', 20, 'ESO'),
  'ipp': ('IPP - Max-Plank-Institut für Plasmaphysik', 20, 'IPP'),
  'mpq': ('MPQ - Max-Plank-Institut für Quantenoptik', 20, 'MPQ'),
  'mpe': ('MPE - Max-Plank-Institut für Extraterrestrische Physik', 20, 'MPE'),
  'mpa': ('MPA - Max-Plank-Institut für Astrophysik', 20, 'MPA'),
  'lrz': ('LRZ - Leibniz-Rechenzentrum', 20, 'LRZ'),
  'frm2': ('FRM II', 20, 'FRM II'),
  'campusfuehrung': ('Ausgiebigerere Campusführung', 20, 'Campusführung'),
  'stadtfuehrung': ('Stadtführung Garching', 20, 'Stadtführung'),
  'isarwanderung': ('Isarwanderung', 20, 'Isarwanderung'),
  'lss': ('Führung durch das LSS', 20, 'LSS'),
  'aisec': ('Fraunhofer AISEC', 20, 'AISEC'),
  'nospace': ('Konnte keiner Exkursion zugeordnet werden', -1, 'Noch offen'),
}

EXKURSIONEN_FIELD_NAMES = ['exkursion1', 'exkursion2', 'exkursion3', 'exkursion4']

EXKURSIONEN_TYPES_FORM = [('nooverwrite', '')] + [(name, data[0]) for name, data in EXKURSIONEN_TYPES.items()]

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

ESSEN_TYPES = {
  'vegetarisch': 'Vegetarisch',
  'vegan': 'Vegan',
  'omnivor': 'Omnivor'
}

ANREISE_TYPES = {
  'bus': 'Fernbus',
  'bahn': 'Zug',
  'auto': 'Auto',
  'flug': 'Flugzeug',
  'floss': 'Floß',
  'fahrrad': 'Fahrrad',
  'sonstige': 'Sonstige'
}

ABREISE_TIMES = {
    'fr': 'Freitag',
    'sa': 'Samstag',
    'sovormittag': 'Sonntag Vormittag',
    'soabend': 'Sonntag Abend',
    'monacht': 'Nacht auf Montag',
    'movormittag': 'Montag Vormittag'
}

ANREDEN = {
    'ka': 'Keine Angabe',
    'er': 'Er/Ihm',
    'sie': 'Sie/Ihr',
    'es': 'Es/Ihm',
    'siemehrzahl': 'Sie (Mehrzahl)/Ihnen',
    'vorname': 'Mit meinem Vornamen/Spitznamen',
    'anderes': 'Sprich mich darauf an'
}

class Winter20ExkursionenOverwriteForm(FlaskForm):
    exkursion_overwrite = SelectField('Exkursionen Festlegung', choices=EXKURSIONEN_TYPES_FORM)
    submit = SubmitField()

def attachment(response, filename):
    response.headers['Content-Disposition'] = 'attachment; filename="{0}"'.format(filename)
    return response

def wise20_calculate_exkursionen(registrations):
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
        if reg.uni.name == 'Universidad de los Saccos Veteres (Alumni)':
            regs_later.append(reg)
            continue;
        got_slot = False
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
        got_slot = False
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
    return result

def get_datetime_string():
    return datetime.now(tz=pytz.timezone('Europe/Berlin')).strftime('%d.%m.%Y %H:%M:%S %Z')

@registration_blueprint.route('/admin/registration/report/clear/<target>')
def registration_wise20_report_clear(target):
    if target == 'all':
        cache.clear()
        return redirect(url_for('registration.registration_wise20_reports'))
    else:
        cache.delete("view/{0}".format(url_for(target)))
        return redirect(url_for(target))

@registration_blueprint.route('/admin/registration/report/wise20')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_reports():
    datetime_string = get_datetime_string() 
    registrations = Registration.query.all()
    confirmed = [reg for reg in registrations if reg.confirmed]
    attendees = [reg for reg in registrations if reg.is_zapf_attendee]
    students = [reg for reg in attendees if reg.data['immatrikuliert'] == 'ja']
    gremika = [reg for reg in attendees if reg.is_guaranteed]
    return render_template('admin/wise20/reports.html',
        registrations=len(registrations),
        attendees=len(attendees),
        students=len(students),
        confirmed=len(confirmed),
        gremika=len(gremika),
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/wise20/exkursionen')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_report_exkursionen():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.all() if reg.is_zapf_attendee]
    result = wise20_calculate_exkursionen(registrations)
    return render_template('admin/wise20/exkursionen.html',
        result = result,
        exkursionen_types = EXKURSIONEN_TYPES,
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/wise20/t-shirts')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_report_tshirts():
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
    return render_template('admin/wise20/t-shirts.html',
        result = result,
        result_unis = result_unis,
        TSHIRTS_TYPES = TSHIRTS_TYPES,
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/wise20/hoodie')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_report_hoodie():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    unis = Uni.query.order_by(Uni.id)
    result = {}
    result_unis = {}
    result_muetze = []
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
        if reg.data['muetze']:
            result_muetze.append(reg)
        result[hoodie_size]['registrations'].append(reg)
        result_unis[reg.uni.id]['registrations'].append(reg)
        result_unis[reg.uni.id]['types'][hoodie_size] += 1
    return render_template('admin/wise20/hoodie.html',
        result = result,
        result_unis = result_unis,
        result_muetze = result_muetze,
        HOODIE_TYPES = HOODIE_TYPES,
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/wise20/merch')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_report_merch():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    unis = Uni.query.order_by(Uni.id)
    result = {
        'shirts': {},
        'hoodies': {},
        'hats': [],
        'beermugs': []
    }
    result_unis = {}
    for uni in unis:
        result_unis[uni.id] = {
            'name': uni.name,
            'registrations': [],
            'shirts': {name: 0 for name, label in TSHIRTS_TYPES.items()},
            'hoodies': {name: 0 for name, label in HOODIE_TYPES.items()},
            'hats': 0,
            'beermugs': 0
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
        if reg.data['muetze']:
            result['hats'].append(reg)
            result_unis[reg.uni.id]['hats'] += 1
        if reg.data['krug']:
            result['beermugs'].append(reg)
            result_unis[reg.uni.id]['beermugs'] += 1
        result['shirts'][tshirt_size]['amount'] += tshirt_amount
        result['shirts'][tshirt_size]['requests'].append({'registration': reg, 'amount': tshirt_amount})
        result['hoodies'][hoodie_size]['amount'] += 1
        result['hoodies'][hoodie_size]['requests'].append({'registration': reg, 'amount': 1})
        result_unis[reg.uni.id]['registrations'].append(reg)
        result_unis[reg.uni.id]['shirts'][tshirt_size] += 1
        result_unis[reg.uni.id]['hoodies'][hoodie_size] += 1
    return render_template('admin/wise20/merch.html',
        result = result,
        result_unis = result_unis,
        TSHIRTS_TYPES = TSHIRTS_TYPES,
        HOODIE_TYPES = HOODIE_TYPES,
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/wise20/essen')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_report_essen():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result_essen = {}
    result_allergien = []
    result_alkohol = []
    for name, label in ESSEN_TYPES.items():
        result_essen[name] = {'label': label, 'registrations': []}
    for reg in registrations:
        essen_type = reg.data['essen']
        allergien = reg.data['allergien']
        alkohol = reg.data['alkohol']
        if (not result_essen[essen_type]):
            return None
        result_essen[essen_type]['registrations'].append(reg)
        if allergien:
            result_allergien.append(reg)
        if alkohol:
            result_alkohol.append(reg)
    return render_template('admin/wise20/essen.html',
        result_essen = result_essen,
        result_allergien = result_allergien,
        result_alkohol = result_alkohol,
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/wise20/rahmenprogramm')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_report_rahmenprogramm():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result_musikwunsch = []
    result_inbound = {}
    result_outbound = {}
    for key in ANREISE_TYPES: result_inbound[key] = []
    for key in ABREISE_TIMES: result_outbound[key] = []
    for reg in registrations:
        musikwunsch = reg.data['musikwunsch']
        abreise = reg.data['abreise_zeit']
        anreise = reg.data['anreise_verkehr']
        if musikwunsch:
            result_musikwunsch.append(reg)
        if anreise in ANREISE_TYPES.keys():
            result_inbound[anreise].append(reg)
        if abreise in ABREISE_TIMES.keys():
            result_outbound[abreise].append(reg)
    return render_template('admin/wise20/rahmenprogramm.html',
        result_musikwunsch = result_musikwunsch,
        result_inbound = result_inbound,
        result_outbound = result_outbound,
        datetime_string = datetime_string,
        ANREISE_TYPES = ANREISE_TYPES,
        ABREISE_TIMES = ABREISE_TIMES
    )

@registration_blueprint.route('/admin/registration/report/wise20/roles')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_report_roles():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result = {}
    result_keys = ['trustee', 'minuteman', 'helper', 'mentee', 'mentor', 'notmentee']
    for key in result_keys: result[key] = []
    for reg in registrations:
        if reg.data['vertrauensperson']: result['trustee'].append(reg) 
        if reg.data['protokoll']: result['minuteman'].append(reg)
        if reg.data['langzeithelfikon']: result['helper'].append(reg) 
        if reg.data['zaepfchen'] == 'ja': result['notmentee'].append(reg) 
        if reg.data['zaepfchen'] == 'jamentor': result['mentee'].append(reg) 
        if reg.data['mentor']: result['mentor'].append(reg) 
    return render_template('admin/wise20/roles.html',
        result = result,
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/wise20/sonstiges')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_report_sonstiges():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result = {}
    result['unterkunft'] = {}
    result['unterkunft']['options'] = ['ja', 'nein']
    result['unterkunft']['ja'] = []
    result['unterkunft']['nein'] = []
    result['student'] = {}
    result['student']['options'] = ['ja', 'nein']
    result['student']['ja'] = []
    result['student']['nein'] = []
    result['minderjaehrig'] = []
    result['stream'] = {}
    result['stream']['options'] = {'ja': "Ja", 'nein': "Nein", 'japasswort': "Ja, aber nur Passwortgeschützt"}
    result['comment'] = []
    for option in result['stream']['options'].keys():
        result['stream'][option] = 0
    for reg in registrations:
        result['unterkunft']['ja'].append(reg) if reg.data['eigene_unterkunft'] else result['unterkunft']['nein'].append(reg)
        result['student']['ja'].append(reg) if reg.data['immatrikuliert'] == 'ja' else result['student']['nein'].append(reg)
        result['stream'][reg.data['stream']] += 1
        if reg.data['minderjaehrig']: result['minderjaehrig'].append(reg)
        if reg.data['kommentar']: result['comment'].append(reg)
    return render_template('admin/wise20/sonstiges.html',
        result = result,
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/<int:reg_id>/details_wise20', methods=['GET', 'POST'])
@groups_sufficient('admin', 'orga')
def registration_wise20_details_registration(reg_id):
    reg = Registration.query.filter_by(id=reg_id).first()
    form = Winter20ExkursionenOverwriteForm()
    if form.validate_on_submit():
        data = reg.data
        if 'exkursion_overwrite' in reg.data:
            old_overwrite = data['exkursion_overwrite']
        else:
            old_overwrite = 'nooverwrite'
        data['exkursion_overwrite'] = form.exkursion_overwrite.data
        reg.data = data
        db.session.add(reg)
        db.session.commit()
        if old_overwrite != form.exkursion_overwrite.data:
            cache.delete("view/{0}".format(url_for('registration.registration_wise20_report_exkursionen')))
            return redirect(url_for('registration.registration_wise20_report_exkursionen'))
        else:
            return redirect(url_for('registration.registration_wise20_details_registration', reg_id = reg_id))
    if 'exkursion_overwrite' in reg.data:
        form.exkursion_overwrite.data = reg.data['exkursion_overwrite']
    if reg.is_guaranteed:
        current_app.logger.debug(reg.user.groups)
    return render_template('admin/wise20/details.html',
        reg = reg,
        form = form,
        EXKURSIONEN_TYPES = EXKURSIONEN_TYPES,
        ESSEN_TYPES = ESSEN_TYPES,
        TSHIRTS_TYPES = TSHIRTS_TYPES,
        HOODIE_TYPES = HOODIE_TYPES,
        ANREISE_TYPES = ANREISE_TYPES,
        ABREISE_TIMES = ABREISE_TIMES,
        ANREDEN = ANREDEN
    )

@registration_blueprint.route('/admin/registration/report/wise20/stimmkarten/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_export_stimmkarten_latex():
    unis = Uni.query.all()
    result = []
    for uni in unis:
        uni_regs = [reg for reg in Registration.query.filter_by(uni_id = uni.id) if reg.is_zapf_attendee]
        if len(uni_regs) > 0:
            result.append("\\stimmkarte{{{0}}}".format(uni.name))
    return attachment(Response("\n".join(result), mimetype="application/x-latex"), 'stimmkarten.tex')

@registration_blueprint.route('/admin/registration/report/wise20/idkarten/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_export_idkarten_latex():
    result = ["\\idcard{{{}}}{{{}}}{{{}}}".format(reg.id, reg.user.full_name, reg.uni.name)
                for reg in Registration.query.order_by(Registration.uni_id) if reg.is_zapf_attendee]
    return attachment(Response("\n".join(result), mimetype="application/x-latex"), 'idkarten.tex')

@registration_blueprint.route('/admin/registration/report/wise20/tagungsausweise/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_export_tagungsausweise_latex():
    def get_sort_key(entry):
        return entry[0]
    registrations = [reg for reg in Registration.query.all() if reg.is_zapf_attendee]
    result_exkursionen = wise20_calculate_exkursionen(registrations)
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

@registration_blueprint.route('/admin/registration/report/wise20/strichlisten/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_export_strichlisten_latex():
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

@registration_blueprint.route('/admin/registration/report/wise20/bmbflisten/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_export_bmbflisten_latex():
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

@registration_blueprint.route('/admin/registration/report/wise20/taschentassenlisten/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_export_taschentassenlisten_latex():
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

@registration_blueprint.route('/admin/registration/report/wise20/ausweisidbeitraglisten/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_export_ausweisidbeitraglisten_latex():
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

@registration_blueprint.route('/admin/registration/report/wise20/t-shirt/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_export_t_shirt_latex():
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

@registration_blueprint.route('/admin/registration/report/wise20/wichteln/csv')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registrations_wise20_export_wichteln_csv():
    registrations = Registration.query.all()
    result = io.StringIO()
    writer = csv.writer(result, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows([[reg.user.full_name, reg.uni.name, reg.data['spitzname']]
                      for reg in registrations if reg.is_zapf_attendee])
    return attachment(Response(result.getvalue(), mimetype='text/csv'), 'wichteln.csv')

@registration_blueprint.route('/admin/registration/report/wise20/exkursionen/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_export_exkursionen_latex():
    registrations = [reg for reg in Registration.query.all() if reg.is_zapf_attendee]
    result_exkursionen = wise20_calculate_exkursionen(registrations)
    result = []
    for name, data in result_exkursionen.items():
        buffer = ["\\exkursionspage{{{type}}}{{".format(type=EXKURSIONEN_TYPES[name][2])]
        for reg in data['registrations']:
            buffer.append("{} & {} \\\\ \\hline".format(reg[0].user.full_name, reg[0].uni.name))
        buffer.append("}")
        result.append("\n".join(buffer))
    return attachment(Response("\n".join(result), mimetype="application/x-latex"), 'exkursionen.tex')

@registration_blueprint.route('/admin/registration/report/wise20/unis/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_export_unis_latex():
    unis = Uni.query.all()
    result = []
    for uni in unis:
        uni_regs = [reg for reg in Registration.query.filter_by(uni_id = uni.id) if reg.is_zapf_attendee]
        if len(uni_regs) > 0:
            result.append("\\item{{{0}}}".format(uni.name))
    return attachment(Response("\n".join(result), mimetype="application/x-latex"), 'unis.tex')

@registration_blueprint.route('/admin/registration/report/wise20/unis-teilnehmer/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_export_unis_teilnehmer_latex():
    unis = Uni.query.all()
    result = []
    for uni in unis:
        uni_regs = [reg for reg in Registration.query.filter_by(uni_id = uni.id) if reg.is_zapf_attendee]
        if len(uni_regs) > 0:
            result.append("\\item{{{0} - {1}}}".format(uni.name, len(uni_regs)))
    return attachment(Response("\n".join(result), mimetype="application/x-latex"), 'unis-tn.tex')

@registration_blueprint.route('/admin/registration/report/wise20/bestaetigungen/latex')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise20_export_bestaetigungen_latex():
    registrations = [reg for reg in Registration.query.order_by(Registration.uni_id) if reg.is_zapf_attendee]
    result = []
    for reg in registrations:
        result.append("\\bestaetigung{{{}}}{{{}}}".format(reg.user.full_name, reg.uni.name))
    return attachment(Response("\n".join(result), mimetype="application/x-latex"), 'bestaetigungen.tex')

@registration_blueprint.route('/admin/registration/report/wise20/id_name/csv')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registrations_wise20_export_id_name_csv():
    registrations = Registration.query.all()
    result = io.StringIO()
    writer = csv.writer(result, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows([[reg.id, "{} ({})".format(reg.user.full_name, reg.uni.name)]
                      for reg in registrations if reg.is_zapf_attendee])
    return attachment(Response(result.getvalue(), mimetype='text/csv'), 'id_name.csv')
