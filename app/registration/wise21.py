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

# HOODIE_TYPES = {
#   'keins': 'Keiner',
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
#   'xxl': 'XXL',
#   'xl': 'XL',
#   'l': 'L',
#   'm': 'M',
#   's': 'S',
#   'xs': 'XS'
# }

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

ANREISE_ZEIT_TYPES = {
  'frueher': 'Vor Do 14h',
  'do1416': 'Do 14-16h',
  'do1618': 'Do 16-18h',
  'do1820': 'Do 18-20h',
  'do2022': 'Do 20-22h',
  'ende': 'Nach Do 22h',
}

ABREISE_ZEIT_TYPES = {
  'vorso': 'Vor So',
  'so810': 'So 8-10h',
  'so1012': 'So 10-12h',
  'so1214': 'So 12-14h',
  'so1416': 'So 14-16h',
  'so1618': 'So 16-18h',
  'so1820': 'So 18-20h',
  'ende': 'Nach dem Plenum',
}

ESSEN_TYPES = {
  'omnivor': 'Omnivor',
  'vegetarisch': 'Vegetarisch',
  'vegan': 'Vegan',
}

ESSEN_AMOUNT_TYPES = {
  'weniger': 'Weniger!',
  'eins': 'Eins',
  'zwei': 'Zwei',
  'drei': 'Drei',
  'mehr': 'Mehr!',
}

IMMA_TYPES = {
    'ja': 'Immatrikuliert',
    'nein': 'Fehler',
    'n.i.': 'Nicht Immatrikuliert',
}

def attachment(response, filename):
    response.headers['Content-Disposition'] = 'attachment; filename="{0}"'.format(filename)
    return response

def get_datetime_string():
    return datetime.now(tz=pytz.timezone('Europe/Berlin')).strftime('%d.%m.%Y %H:%M:%S %Z')

@registration_blueprint.route('/admin/registration/report/clear/<target>')
def registration_wise21_report_clear(target):
    if target == 'all':
        cache.clear()
        return redirect(url_for('registration.registration_wise21_reports'))
    else:
        cache.delete("view/{0}".format(url_for(target)))
        return redirect(url_for(target))

@registration_blueprint.route('/admin/registration/report/wise21')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise21_reports():
    datetime_string = get_datetime_string() 
    registrations = Registration.query.all()
    confirmed = [reg for reg in registrations if reg.confirmed]
    attendees = [reg for reg in registrations if reg.is_zapf_attendee]
    gremika = [reg for reg in attendees if reg.is_guaranteed]
    return render_template('admin/wise21/reports.html',
        registrations=len(registrations),
        attendees=len(attendees),
        confirmed=len(confirmed),
        gremika=len(gremika),
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/wise21/merch')
@registration_blueprint.route('/admin/registration/report/wise21/merch/<place>')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise21_report_merch(place = None):
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    unis = Uni.query.order_by(Uni.id)
    result = {
        'shirts': {},
        'nomugs': [],
        'nobags': [],
    }
    result_unis = {}
    for uni in unis:
        result_unis[uni.id] = {
            'name': uni.name,
            'registrations': [],
            'shirts': {name: 0 for name, label in TSHIRTS_TYPES.items()},
            'nomugs': 0,
            'nobags': 0,
        }
    for name, label in TSHIRTS_TYPES.items():
        result['shirts'][name] = {'label': label, 'amount': 0, 'requests': []}
    for reg in registrations:
        if place is not None:
            if place == 'online' and reg.data['modus'] != "online":
                continue
            if place != 'online' and place != reg.data['standort']:
                continue

        tshirt_size = reg.data['tshirt']
        tshirt_amount = reg.data['nrtshirt']
        if tshirt_amount == None:
            tshirt_amount = 0
        if not result['shirts'][tshirt_size]:
            return None
        if reg.data['nottasse']:
            result['nomugs'].append(reg)
            result_unis[reg.uni.id]['nomugs'] += 1
        if reg.data['nottasche']:
            result['nobags'].append(reg)
            result_unis[reg.uni.id]['nobags'] += 1
        result['shirts'][tshirt_size]['amount'] += tshirt_amount
        result['shirts'][tshirt_size]['requests'].append({'registration': reg, 'amount': tshirt_amount})
        result_unis[reg.uni.id]['registrations'].append(reg)
        result_unis[reg.uni.id]['shirts'][tshirt_size] += tshirt_amount
    return render_template('admin/wise21/merch.html',
        result = result,
        result_unis = result_unis,
        TSHIRTS_TYPES = TSHIRTS_TYPES,
        datetime_string = datetime_string,
        place = place,
    )

@registration_blueprint.route('/admin/registration/report/wise21/standort')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise21_report_standort():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id)]
    result = {
        'goe': [],
        'koe': [],
        'mue': [],
        'egal': [],
    }
    for reg in registrations:
        if reg.data['modus'] == "online":
            continue

        result[reg.data['standort']].append(reg)
        
    return render_template('admin/wise21/standort.html',
        result = result,
        datetime_string = datetime_string,
    )

@registration_blueprint.route('/admin/registration/report/wise21/praesentonline')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise21_report_praesentonline():
    datetime_string = get_datetime_string()
    registrations = [reg for reg in Registration.query.order_by(Registration.id)]
    result = {
        'online': [],
        'present': [],
    }
    for reg in registrations:

        result[reg.data['modus']].append(reg)
    return render_template('admin/wise21/praesentonline.html',
        result = result,
        datetime_string = datetime_string,
    )

@registration_blueprint.route('/admin/registration/report/wise21/essen')
@registration_blueprint.route('/admin/registration/report/wise21/essen/<place>')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise21_report_essen(place = None):
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
        if reg.data['modus'] == "online":
                continue
        if place is not None and place != reg.data['standort']:
                continue
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
    return render_template('admin/wise21/essen.html',
        result = result,
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/wise21/anreise')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise21_report_anreise():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result = {}
    result_places = ['goe', 'koe', 'mue', 'egal']
    result_keys = ['inbound', 'inbound_time', 'outbound_time']
    for place in result_places: 
        result[place] = {}
        for key in result_keys: result[place][key] = {}
        
        for key in ANREISE_TYPES: result[place]['inbound'][key] = []
        for key in ANREISE_ZEIT_TYPES: result[place]['inbound_time'][key] = []
        for key in ABREISE_ZEIT_TYPES: result[place]['outbound_time'][key] = []

    for reg in registrations:
        if reg.data['modus'] == "online":
            continue
        else:
            place = reg.data['standort']
        anreise = reg.data['anreise_witz']
        anreise_zeit = reg.data['anreise_zeit']
        abreise_zeit = reg.data['abreise_zeit']
        if anreise in ANREISE_TYPES.keys():
            result[place]['inbound'][anreise].append(reg)
        if anreise_zeit in ANREISE_ZEIT_TYPES.keys():
            result[place]['inbound_time'][anreise_zeit].append(reg)
        if abreise_zeit in ABREISE_ZEIT_TYPES.keys():
            result[place]['outbound_time'][abreise_zeit].append(reg)
    return render_template('admin/wise21/anreise.html',
        result = result,
        datetime_string = datetime_string,
        places = result_places,
        ANREISE_TYPES = ANREISE_TYPES,
        ANREISE_ZEIT_TYPES = ANREISE_ZEIT_TYPES,
        ABREISE_ZEIT_TYPES = ABREISE_ZEIT_TYPES,
    )

@registration_blueprint.route('/admin/registration/report/wise21/roles')
@registration_blueprint.route('/admin/registration/report/wise21/roles/<place>')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise21_report_roles(place = None):
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result = {}
    result_keys = ['trustee', 'minuteman', 'mentee', 'mentor', 'notmentee']
    for key in result_keys: result[key] = []
    for reg in registrations:
        if place is not None:
            if place == 'online' and reg.data['modus'] != "online":
                continue
            if place != 'online' and place != reg.data['standort']:
                continue

        if reg.data['vertrauensperson'] == 'ja': result['trustee'].append(reg) 
        if reg.data['protokoll'] == 'ja': result['minuteman'].append(reg) 
        if reg.data['zaepfchen'] == 'ja': result['notmentee'].append(reg) 
        if reg.data['zaepfchen'] == 'jaund': result['mentee'].append(reg) 
        if reg.data['mentor']: result['mentor'].append(reg) 
    return render_template('admin/wise21/roles.html',
        result = result,
        datetime_string = datetime_string
    )

@registration_blueprint.route('/admin/registration/report/wise21/sonstiges')
@groups_sufficient('admin', 'orga')
@cache.cached()
def registration_wise21_report_sonstiges():
    datetime_string = get_datetime_string() 
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result = {}
    result['comment'] = []
    result['music'] = []
        
    for reg in registrations:
        if reg.data['kommentar']: result['comment'].append(reg)
        if reg.data['musikwunsch']: result['music'].append(reg)
        
        
    return render_template('admin/wise21/sonstiges.html',
        result = result,
        datetime_string = datetime_string,
    )

class DetailsOverwriteForm(FlaskForm):
    spitzname = StringField('Spitzname')
    modus = SelectField('Modus', choices=[
            ("online", "Online-Teilnahme"),
            ("present", "Präsenzteilnahme"),
        ],
    )
    standort = SelectField('Standort festlegen', choices=[
            ("goe", "Göttingen"), 
            ("koe", "Köln"), 
            ("mue", "München (Garchingen)"), 
            ("egal", "Egal"),
        ]
    )
    priority = IntegerField("Priorität (-1 für manuelle Platzvergabe)")
    submit = SubmitField()

@registration_blueprint.route('/admin/registration/<int:reg_id>/details_wise21', methods=['GET', 'POST'])
@groups_sufficient('admin', 'orga')
def registration_wise21_details_registration(reg_id):
    reg = Registration.query.filter_by(id=reg_id).first()
    form = DetailsOverwriteForm()

    if form.validate_on_submit():
        data = reg.data
        if 'orig_standort' not in data:
            data['orig_standort'] = data['standort']
        if 'orig_modus' not in data:
            data['orig_modus'] = data['modus']
        if 'orig_spitzname' not in data:
            data['orig_spitzname'] = data['spitzname']
        data['standort'] = form.standort.data
        data['modus'] = form.modus.data
        data['spitzname'] = form.spitzname.data
        reg.data = data

        if reg.priority != form.priority.data:
            reg.priority = form.priority.data

        db.session.add(reg)
        db.session.commit()
        return redirect(url_for('registration.registration_wise21_details_registration', reg_id = reg_id))
        
    form.spitzname.data = reg.data['spitzname']
    form.standort.data = reg.data['standort']
    form.modus.data = reg.data['modus']
    form.priority.data = reg.priority
    return render_template('admin/wise21/details.html',
        reg = reg,
        form = form,
        TSHIRTS_TYPES = TSHIRTS_TYPES,
        ANREISE_TYPES = ANREISE_TYPES,
        ANREISE_ZEIT_TYPES = ANREISE_ZEIT_TYPES,
        ABREISE_ZEIT_TYPES = ABREISE_ZEIT_TYPES,
        ESSEN_TYPES = ESSEN_TYPES,
        ESSEN_AMOUNT_TYPES = ESSEN_AMOUNT_TYPES,
        IMMA_TYPES = IMMA_TYPES,
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
