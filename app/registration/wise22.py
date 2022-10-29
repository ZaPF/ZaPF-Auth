from flask import render_template, jsonify, Response, redirect, url_for, current_app
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, IntegerField
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
  'hamburgfuehrung': ('Hamburg Stadt Führung', -1, 'Stadt'),
  'desy': ('DESY Führung', -1, 'Desy'),
  'sternenwarte': ('Sternwarte', -1, 'sternenwarte'),
  'lufthansa': ('Lufthansa Technik', -1, 'Lufthansa'),
  'kunst': ('Kunsthalle', -1, 'Kunst'),
  'hafenrundfahrt': ('Hafenrundfahrt', -1, 'Hafen'),
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
#   '3xl': '3XL',
  'xxl': 'XXL',
  'xl': 'XL',
  'l': 'L',
  'm': 'M',
  's': 'S',
  'xs': 'XS'
}

T_SHirt_SCHNITT_CHOICES = {
    'mens-fit': 'gerader Schnitt (Männer)',
    'ladies-fit': 'Körperbetonender Schnitt (Frauen)',
    'keins':'keins'
}

Kapuzenjacken_CHOICES = {
  'keins': 'Keiner',
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
  'flohpulver': 'Flohpulver',
  'fahrrad': 'Fahrrad',
  'badeente': 'Badeente',
}

ANREISE_ZEIT_TYPES = {
  'frueher': 'früher',
  'fr014': 'DO vor 14h',
  'do014': 'DO vor 14h',
  'do114': 'DO nach 14h',
  'fr114': 'DO nach 14h',
  'ende': 'Samstag',
}

ABREISE_ZEIT_TYPES = {
  'vorso': 'Vor SO',
  'so016': 'SO vor 16h',
  'so116': 'SO nach 16h',
}

ESSEN_TYPES = {
  'omnivor': 'Omnivor',
  'vegetarisch': 'Vegetarisch',
  'vegan': 'Vegan',
}


IMMA_TYPES = {
    'invalid': '---',
    'ja': 'Immatrikuliert',
    'nein': 'Fehler',
    'n.i.': 'Nicht Immatrikuliert',
}

class ExkursionenOverwriteForm(FlaskForm):
    exkursion_overwrite = SelectField('Exkursionen Festlegung', choices=EXKURSIONEN_TYPES_FORM)
    submit = SubmitField()

def attachment(response, filename):
    response.headers['Content-Disposition'] = 'attachment; filename="{0}"'.format(filename)
    return response

def wise22_calculate_exkursionen(registrations):
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
def registration_wise22_report_clear(target):
    if target == 'all':
        cache.clear()
        return redirect(url_for('registration.registration_wise22_reports'))
    else:
        cache.delete("view/{0}".format(url_for(target)))
        return redirect(url_for(target))

@registration_blueprint.route('/admin/registration/report/wise22')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise22_reports():
    datetime_string = get_datetime_string() 
    registrations = Registration.query.all()
    confirmed = [reg for reg in registrations if reg.confirmed]
    attendees = [reg for reg in registrations if reg.is_zapf_attendee]
    gremika = [reg for reg in attendees if reg.is_guaranteed]
    return render_template('admin/wise22/reports.html',
        registrations=len(registrations),
        attendees=len(attendees),
        confirmed=len(confirmed),
        gremika=len(gremika),
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/wise22/reise')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise22_report_reise():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result = {}
    result['anreise_zeit'] = {}
    result['abreise_zeit'] = {}
    result['anreise_witz'] = {}
    result['nrwticket'] = {
        'nein': [],
        'ja': [],
        'jaund': [],
    }
    for name, label in ANREISE_ZEIT_TYPES.items():
        result['anreise_zeit'][name] = {'label': label, 'registrations': []}
    for reg in registrations:
        anreise_type = reg.data['anreise_zeit']
        if (not result['anreise_zeit'][anreise_type]):
            return None
        result['anreise_zeit'][anreise_type]['registrations'].append(reg)
    for name, label in ABREISE_ZEIT_TYPES.items():
        result['abreise_zeit'][name] = {'label': label, 'registrations': []}
    for reg in registrations:
        abreise_type = reg.data['abreise_zeit']
        if (not result['abreise_zeit'][abreise_type]):
            return None
        result['abreise_zeit'][abreise_type]['registrations'].append(reg)
    for name, label in ANREISE_TYPES.items():
        result['anreise_witz'][name] = {'label': label, 'registrations': []}
    for reg in registrations:
        anreise_witz_type = reg.data['anreise_witz']
        if (not result['anreise_witz'][anreise_witz_type]):
            return None
        result['anreise_witz'][anreise_witz_type]['registrations'].append(reg)
    return render_template('admin/wise22/reise.html',
        result = result,
        ANREISE_ZEIT_TYPES = ANREISE_ZEIT_TYPES,
        ABREISE_ZEIT_TYPES = ABREISE_ZEIT_TYPES,
        ANREISE_TYPES = ANREISE_TYPES,
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/wise22/roles')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise22_report_roles():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result = {}
    result_keys = ['trustee', 'minuteman', 'akchair', 'plenumchair', 'electee','mentee', 'mentor', 'notmentee']
    for key in result_keys: result[key] = []
    for reg in registrations:
        if reg.data['vertrauensperson']: result['trustee'].append(reg) 
        if reg.data['protokoll']: result['minuteman'].append(reg) 
        if reg.data['akleitung']: result['akchair'].append(reg)
        if reg.data['redeleitung']: result['plenumchair'].append(reg)
        if reg.data['gremiumwahl']: result['electee'].append(reg)
        if reg.data['zaepfchen'] == 'ja': result['notmentee'].append(reg) 
        if reg.data['zaepfchen'] == 'jaund': result['mentee'].append(reg) 
        if reg.data['mentor']: result['mentor'].append(reg) 
    return render_template('admin/wise22/roles.html',
        result = result,
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/wise22/t-shirts')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise22_report_tshirts():
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
    return render_template('admin/wise22/t-shirts.html',
        result = result,
        result_unis = result_unis,
        TSHIRTS_TYPES = TSHIRTS_TYPES,
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/wise22/merch')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise22_report_merch():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    unis = Uni.query.order_by(Uni.id)
    result = {
        'nobags': [],
    }
    result_unis = {}
    for uni in unis:
        result_unis[uni.id] = {
            'name': uni.name,
            'registrations': [],
            'nobags': 0,
        }
    for reg in registrations:
        if reg.data['nottasche']:
            result['nobags'].append(reg)
            result_unis[reg.uni.id]['nobags'] += 1
    return render_template('admin/wise22/merch.html',
        result = result,
        result_unis = result_unis,
        datetime_string = datetime_string,
    )

@registration_blueprint.route('/admin/registration/report/wise22/essen')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise22_report_essen():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result = {}
    result['essen'] = {}
    result['allergien'] = []
    result['alkohol'] = []
    result['heissgetraenk'] = {
        'kaffee': [],
        'tee': [],
        'unparteiisch': [],
    }
    for name, label in ESSEN_TYPES.items():
        result['essen'][name] = {'label': label, 'registrations': []}
    for reg in registrations:
        essen_type = reg.data['essen']
        allergien = reg.data['allergien']
        alkohol = reg.data['alkohol']
        heissgetraenk = reg.data['heissgetraenk']
        essensformen = reg.data['essensformen']
        if (not result['essen'][essen_type]):
            return None
        result['essen'][essen_type]['registrations'].append(reg)
        if allergien or essensformen:
            result['allergien'].append(reg)
        if alkohol == 'ja':
            result['alkohol'].append(reg)
        result['heissgetraenk'][heissgetraenk].append(reg)
    return render_template('admin/wise22/essen.html',
        result = result,
        ESSEN_AMOUNT_TYPES = ESSEN_AMOUNT_TYPES,
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/wise22/unterkunft')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise22_report_unterkunft():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result = {}
    result['barriere'] = []
    result['toilette'] = []
    result['couch'] = []
    result['privat'] = []
    result['schlafen'] = {
        'laut': [],
        'elaut': [],
        'egal': [],
        'eleise': [],
        'leise': [],
    }
    
    for reg in registrations:
        if reg.data['barrierefreiheit']: result['barriere'].append(reg)
        if reg.data['notbinarytoiletten']: result['toilette'].append(reg)
        if reg.data['couchsurfing']: result['couch'].append(reg)
        if reg.data['privatunterkunft']: result['privat'].append(reg)
        schlafen = reg.data['schlafen']
        result['schlafen'][schlafen].append(reg)
        
    return render_template('admin/wise22/unterkunft.html',
        result = result,
        datetime_string = datetime_string,
    )

@registration_blueprint.route('/admin/registration/report/wise22/exkursionen')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise22_report_exkursionen():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.all() if reg.is_zapf_attendee]
    result = wise22_calculate_exkursionen(registrations)
    return render_template('admin/wise22/exkursionen.html',
        result = result,
        exkursionen_types = EXKURSIONEN_TYPES,
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/wise22/sonstiges')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise22_report_sonstiges():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result = {}
    result['comment'] = []
        
    for reg in registrations:
        if reg.data['kommentar']: result['comment'].append(reg)
        
        
    return render_template('admin/wise22/sonstiges.html',
        result = result,
        datetime_string = datetime_string,
    )


@registration_blueprint.route('/admin/registration/<int:reg_id>/details_wise22', methods=['GET', 'POST'])
@groups_sufficient('admin', 'orga')
def registration_wise22_details_registration(reg_id):
    reg = Registration.query.filter_by(id=reg_id).first()
    form = ExkursionenOverwriteForm()
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
            cache.delete("view/{0}".format(url_for('registration.registration_wise22_report_exkursionen')))
            return redirect(url_for('registration.registration_wise22_report_exkursionen'))
        else:
            return redirect(url_for('registration.registration_wise22_details_registration', reg_id = reg_id))
    if 'exkursion_overwrite' in reg.data:
        form.exkursion_overwrite.data = reg.data['exkursion_overwrite']
    if reg.is_guaranteed:
        current_app.logger.debug(reg.user.groups)
    return render_template('admin/wise22/details.html',
        reg = reg,
        form = form,
        EXKURSIONEN_TYPES = EXKURSIONEN_TYPES,
        TSHIRTS_TYPES = TSHIRTS_TYPES,
        ANREISE_TYPES = ANREISE_TYPES,
        ANREISE_ZEIT_TYPES = ANREISE_ZEIT_TYPES,
        ABREISE_ZEIT_TYPES = ABREISE_ZEIT_TYPES,
        ESSEN_TYPES = ESSEN_TYPES,
        ESSEN_AMOUNT_TYPES = ESSEN_AMOUNT_TYPES,
        IMMA_TYPES = IMMA_TYPES,
    )

@registration_blueprint.route('/admin/registration/report/wise21/stimmkarten/latex')
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
#    result_exkursionen = sose21_calculate_exkursionen(registrations)
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
