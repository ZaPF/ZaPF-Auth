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
  'schwab': ('Weingut Schwab mit Wienprobe und Brotzeit (10€ Selbstbeteiligung)', 25, 'Schwab'),
  'vaqtec': ('va-Q-tec', 15, 'Vaqtec'),
  'zae': ('Zentrum für angewandte Energieforschung Bayern & Fraunhofer EZRT', 15, 'ZAE & Fraunhofer'),
  'noell': ('Bilfinger Noell', 20, 'Noell'),
  'isc': ('Fraunhofer ISC', 20, 'Fraunhofer'),
  'mind': ('M!ND-Center', 30, 'Mind-Center'),
  'stfr': ('Stadtführung mit Residenz', 25, 'StadResidenz'),
  'stff': ('Stadtführung mit Festung Marienberg', 25, 'StadFestung'),
  'mft': ('Mainfranken-Theater', 20, 'Theater'),
  'xray': ('Röntgen-Gedächtnisstätte', 20, 'Röntgen'),
  'egal': ('ist mir egal', -1, 'Egal'),
  'keine': ('keine exkursion', -1, 'Keine'),
  'nospace': ('Konnte keiner Exkursion zugeordnet werden', -1, 'Noch offen'),
}

EXKURSIONEN_FIELD_NAMES = ['exkursion1', 'exkursion2', 'exkursion3', 'exkursion4']

EXKURSIONEN_TYPES_BIRTHDAY = []

EXKURSIONEN_TYPES_FORM = [('nooverwrite', '')] + [(name, data[0]) for name, data in EXKURSIONEN_TYPES.items()]

TSHIRTS_TYPES = {
  'keins': 'Nein, ich möchte keins',
  'fitted_xl': 'fitted XL',
  'fitted_l': 'fitted L',
  'fitted_m': 'fitted M',
  'fitted_s': 'fitted S',
  'fitted_xs': 'fitted XS',
  '3xl': '3XL',
  'xxl': 'XXL',
  'xl': 'XL',
  'l': 'L',
  'm': 'M',
  's': 'S',
}

HOODIE_TYPES = {
        'keins': 'Nein, ich möchte keins',
        '3xl': '3XL',
        'xxl': 'XXL',
        'xl': 'XL',
        'l': 'L',
        'm': 'M',
        's': 'S',
        'xs': 'XS',
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
  'MZH': 'Mehrzweckhalle',
  'FW': 'Feuerwehr',
  'egal': 'Egal'
}

ANREISE_TYPES = {
  'bus': 'Fernbus',
  'bahn': 'Zug',
  'auto': 'Auto',
  'flug': 'Flugzeug',
  'fahrrad': 'Fahrrad',
  'boot': 'Boot',
  'zeitmaschine': 'Zeitmaschine',
  'einhorn': 'Einhorn'
}

ABREISE_TYPES = {
        'ende': 'Nach dem Plenum',
        'so810': 'Sonntag 8-10',
        'so1012': 'Sonntag 10-12',
        'so1214': 'Sonntag 12-14',
        'so1416': 'Sonntag 14-16',
        'so1618': 'Sonntag 16-18',
        'so1820': 'Sonntag 18-20',
        'vorso': 'Vor Sonntag'
}

class Winter18ExkursionenOverwriteForm(FlaskForm):
    spitzname = StringField('Spitzname')
    exkursion_overwrite = SelectField('Exkursionen Festlegung', choices=EXKURSIONEN_TYPES_FORM)
    submit = SubmitField()

def wise18_calculate_exkursionen(registrations):
    def get_sort_key(reg):
        return reg.id
    result = {}
    regs_later = []
    regs_notfirst = []
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
        if reg.uni.name == 'Alumni':
            regs_later.append(reg)
            continue;
        got_slot = False
        for field_index, field in enumerate(EXKURSIONEN_FIELD_NAMES):
            exkursion_selected = reg.data[field]
            if exkursion_selected == 'schwab':
                result['schwab']['registrations'].append((reg, field_index))
                result['schwab']['free'] -= 1
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
            if not result[exkursion_selected]:
                return None
            if result[exkursion_selected]['space'] == -1 or result[exkursion_selected]['free'] > 0:
                result[exkursion_selected]['registrations'].append((reg, field_index))
                result[exkursion_selected]['free'] -= 1
                break;
    return result

@registration_blueprint.route('/admin/registration/report/wise18')
@groups_sufficient('admin', 'orga')
def registration_wise18_reports():
    return render_template('admin/wise18/reports.html')

@registration_blueprint.route('/admin/registration/report/wise18/exkursionen')
@groups_sufficient('admin', 'orga')
def registration_wise18_report_exkursionen():
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result = wise18_calculate_exkursionen(registrations)
    return render_template('admin/wise18/exkursionen.html',
        result = result,
        exkursionen_types = EXKURSIONEN_TYPES,
        exkursionen_types_birthday = EXKURSIONEN_TYPES_BIRTHDAY
    )

@registration_blueprint.route('/admin/registration/report/wise18/t-shirts')
@groups_sufficient('admin', 'orga')
def registration_wise18_report_tshirts():
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    unis = Uni.query.order_by(Uni.id)
    result = {}
    result_unis = {}
    for uni in unis:
        result_unis[uni.id] = {
            'name': uni.name,
            'registrations': [],
            'types': {name: 0 for name, label in TSHIRTS_TYPES.items()},
            'total': 0
        }
    for name, label in TSHIRTS_TYPES.items():
        result[name] = {'label': label, 'registrations': [], 'total': 0}
    for reg in registrations:
        tshirt_size = reg.data['tshirt']
        additional_shirts = reg.data['addtshirt']
        if not result[tshirt_size]:
            return None     
        result[tshirt_size]['registrations'].append(reg)
        result[tshirt_size]['total'] +=1
        result_unis[reg.uni.id]['registrations'].append(reg)
        result_unis[reg.uni.id]['types'][tshirt_size] += 1
        result_unis[reg.uni.id]['total'] += 1
        if additional_shirts:
            result[tshirt_size]['total'] += additional_shirts
            result_unis[reg.uni.id]['types'][tshirt_size] += additional_shirts
            result_unis[reg.uni.id]['total'] += additional_shirts
    return render_template('admin/wise18/t-shirts.html',
        result = result,
        result_unis = result_unis,
        TSHIRTS_TYPES = TSHIRTS_TYPES
    )

@registration_blueprint.route('/admin/registration/report/wise18/anabreise')
@groups_sufficient('admin', 'orga')
def registration_wise18_report_anabreise():
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    unis = Uni.query.order_by(Uni.id)
    result_anreise = {}
    result_abreise = {}

    for name, label in ANREISE_TYPES.items():
        result_anreise[name] = {'label': label, 'registrations': []}
    for name, label in ABREISE_TYPES.items():
        result_abreise[name] = {'label': label, 'registrations': []}
    for reg in registrations:
        anreise = reg.data['anreise']
        abreise = reg.data['abreise']
        if not result_abreise[abreise] or not result_anreise[anreise]:
            return None     
        result_anreise[anreise]['registrations'].append(reg)
        result_abreise[abreise]['registrations'].append(reg)
    return render_template('admin/wise18/anabreise.html',
        result_anreise = result_anreise,
        result_abreise = result_abreise,
        ANREISE_TYPES = ANREISE_TYPES,
        ABREISE_TYPES = ABREISE_TYPES
    )

@registration_blueprint.route('/admin/registration/report/wise18/hoodie')
@groups_sufficient('admin', 'orga')
def registration_wise18_report_hoodie():
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    unis = Uni.query.order_by(Uni.id)
    result = {}
    result_unis = {}
    result_handtuch = []
    result_roemer = []
    for uni in unis:
        result_unis[uni.id] = {
            'name': uni.name,
            'registrations': [],
            'types': {name: 0 for name, label in HOODIE_TYPES.items()},
        }
    for name, label in HOODIE_TYPES.items():
        result[name] = {'label': label, 'registrations': []}
    for reg in registrations:
        hoodie_size = reg.data['hoodie']
        if not result[hoodie_size]:
            return None
        if reg.data['handtuch']:
            result_handtuch.append(reg)
        if reg.data['roemer']:
            result_roemer.append(reg)
        result[hoodie_size]['registrations'].append(reg)
        result_unis[reg.uni.id]['registrations'].append(reg)
        result_unis[reg.uni.id]['types'][hoodie_size] += 1
    return render_template('admin/wise18/hoodie.html',
        result = result,
        result_unis = result_unis,
        result_handtuch = result_handtuch,
        result_roemer = result_roemer,
        HOODIE_TYPES = HOODIE_TYPES
    )

@registration_blueprint.route('/admin/registration/report/wise18/essen')
@groups_sufficient('admin', 'orga')
def registration_wise18_report_essen():
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result_essen = {}
    result_heisse_getraenke = {}
    result_essenswunsch = []
    result_allergien = []
    for name, label in ESSEN_TYPES.items():
        result_essen[name] = {'label': label, 'registrations': []}
    for name, label in HEISSE_GETRAENKE_TYPES.items():
        result_heisse_getraenke[name] = {'label': label, 'registrations': []}
    for reg in registrations:
        essen_type = reg.data['essen']
        heisse_getraenke = reg.data['heissgetraenk']
        essenswunsch = reg.data['essenswunsch']
        allergien = reg.data['allergien']
        if not result_essen[essen_type] or not result_heisse_getraenke[heisse_getraenke]:
            return None
        result_essen[essen_type]['registrations'].append(reg)
        result_heisse_getraenke[heisse_getraenke]['registrations'].append(reg)
        if essenswunsch:
            result_essenswunsch.append(reg)
        if allergien:
            result_allergien.append(reg)
    return render_template('admin/wise18/essen.html',
        result_essen = result_essen,
        result_heisse_getraenke = result_heisse_getraenke,
        result_essenswunsch = result_essenswunsch,
        result_allergien = result_allergien
    )

@registration_blueprint.route('/admin/registration/report/wise18/rahmenprogramm')
@groups_sufficient('admin', 'orga')
def registration_wise18_report_rahmenprogramm():
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result_alternativprogramm = []
    result_musikwunsch = []
    for reg in registrations:
        alternativprogramm = reg.data['alternativprogramm']
        musikwunsch = reg.data['musikwunsch']
        if alternativprogramm:
            result_alternativprogramm.append(reg)
        if musikwunsch:
            result_musikwunsch.append(reg)
    return render_template('admin/wise18/rahmenprogramm.html',
        result_alternativprogramm = result_alternativprogramm,
        result_musikwunsch = result_musikwunsch
    )

@registration_blueprint.route('/admin/registration/report/wise18/sonstiges')
@groups_sufficient('admin', 'orga')
def registration_wise18_report_sonstiges():
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result_schlafen = {}
    result_kommentar = []
    result_minderjaehrig = []
    for name, label in SCHLAFEN_TYPES.items():
        result_schlafen[name] = {'label': label, 'registrations': []}
    for reg in registrations:
        schlafen_type = reg.data['schlafen']
        kommentar = reg.data['kommentar']
        minderjaehrig = reg.data['minderjaehrig']
        result_schlafen[schlafen_type]['registrations'].append(reg)
        if kommentar:
            result_kommentar.append(reg)
        if minderjaehrig:
            result_minderjaehrig.append(reg)
    return render_template('admin/wise18/sonstiges.html',
        result_schlafen = result_schlafen,
        result_kommentar = result_kommentar,
        result_minderjaehrig = result_minderjaehrig
    )

@registration_blueprint.route('/admin/registration/report/wise18/spitznamen')
@groups_sufficient('admin', 'orga')
def registration_wise18_report_spitznamen():
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result = {'with': [], 'without': []}
    for reg in registrations:
        spitzname = reg.data['spitzname']
        if spitzname and spitzname != "-":
            result['with'].append(reg)
        else:
            result['without'].append(reg)
    return render_template('admin/wise18/spitznamen.html',
        result = result
    )

@registration_blueprint.route('/admin/registration/<int:reg_id>/details_wise18', methods=['GET', 'POST'])
@groups_sufficient('admin', 'orga')
def registration_wise18_details_registration(reg_id):
    reg = Registration.query.filter_by(id=reg_id).first()
    form = Winter18ExkursionenOverwriteForm()
    if form.validate_on_submit():
        data = reg.data
        old_spitzname = data['spitzname']
        if 'exkursion_overwrite' in reg.data:
            old_overwrite = data['exkursion_overwrite']
        else:
            old_overwrite = 'nooverwrite'
        data['spitzname'] = form.spitzname.data
        data['exkursion_overwrite'] = form.exkursion_overwrite.data
        reg.data = data
        db.session.add(reg)
        db.session.commit()
        if old_spitzname != form.spitzname.data:
            return redirect(url_for('registration.registration_wise18_report_spitznamen'))
        elif old_overwrite != form.exkursion_overwrite.data:
            return redirect(url_for('registration.registration_wise18_report_exkursionen'))
        else:
            return redirect(url_for('registration.registration_wise18_details_registration', reg_id = reg_id))
    if 'exkursion_overwrite' in reg.data:
        form.exkursion_overwrite.data = reg.data['exkursion_overwrite']
    form.spitzname.data = reg.data['spitzname']
    return render_template('admin/wise18/details.html',
        reg = reg,
        form = form,
        EXKURSIONEN_TYPES = EXKURSIONEN_TYPES,
        ESSEN_TYPES = ESSEN_TYPES,
        TSHIRTS_TYPES = TSHIRTS_TYPES,
        SCHLAFEN_TYPES = SCHLAFEN_TYPES,
        HEISSE_GETRAENKE_TYPES = HEISSE_GETRAENKE_TYPES,
        ANREISE_TYPES = ANREISE_TYPES,
        ABREISE_TYPES = ABREISE_TYPES,
        HOODIE_TYPES = HOODIE_TYPES
    )

@registration_blueprint.route('/admin/registration/report/wise18/stimmkarten/latex')
@groups_sufficient('admin', 'orga')
def registration_wise18_export_stimmkarten_latex():
    unis = Uni.query.all()
    result = []
    for uni in unis:
        uni_regs = [reg for reg in Registration.query.filter_by(uni_id = uni.id) if reg.is_zapf_attendee]
        if len(uni_regs) > 0:
            result.append("\\stimmkarte{{{0}}}".format(uni.name))
    return Response("\n".join(result), mimetype="application/x-latex")

@registration_blueprint.route('/admin/registration/report/wise18/idkarten/latex')
@groups_sufficient('admin', 'orga')
def registration_wise18_export_idkarten_latex():
    result = ["\\idcard{{{}}}{{{}}}{{{}}}".format(reg.id, reg.user.full_name, reg.uni.name)
                for reg in Registration.query.order_by(Registration.uni_id) if reg.is_zapf_attendee]
    return Response("\n".join(result), mimetype="application/x-latex")

@registration_blueprint.route('/admin/registration/report/wise18/tagungsausweise/latex')
@groups_sufficient('admin', 'orga')
def registration_wise18_export_tagungsausweise_latex():
    def get_sort_key(entry):
        return entry[0]
    registrations = [reg for reg in Registration.query.all() if reg.is_zapf_attendee]
    result_exkursionen = wise18_calculate_exkursionen(registrations)
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
    return Response("\n".join(result), mimetype="application/x-latex")

@registration_blueprint.route('/admin/registration/report/wise18/strichlisten/latex')
@groups_sufficient('admin', 'orga')
def registration_wise18_export_strichlisten_latex():
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
    return Response("\n".join(result), mimetype="application/x-latex")

@registration_blueprint.route('/admin/registration/report/wise18/bmbflisten/latex')
@groups_sufficient('admin', 'orga')
def registration_wise18_export_bmbflisten_latex():
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
    return Response("\n".join(result), mimetype="application/x-latex")

@registration_blueprint.route('/admin/registration/report/wise18/taschentassenlisten/latex')
@groups_sufficient('admin', 'orga')
def registration_wise18_export_taschentassenlisten_latex():
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
    return Response("\n".join(result), mimetype="application/x-latex")

@registration_blueprint.route('/admin/registration/report/wise18/ausweisidbeitraglisten/latex')
@groups_sufficient('admin', 'orga')
def registration_wise18_export_ausweisidbeitraglisten_latex():
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
    return Response("\n".join(result), mimetype="application/x-latex")

@registration_blueprint.route('/admin/registration/report/wise18/t-shirt/latex')
@groups_sufficient('admin', 'orga')
def registration_wise18_export_t_shirt_latex():
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
    return Response("\n".join(result), mimetype="application/x-latex")

@registration_blueprint.route('/admin/registration/report/wise18/exkursionen/latex')
@groups_sufficient('admin', 'orga')
def registration_wise18_export_exkursionen_latex():
    registrations = [reg for reg in Registration.query.all() if reg.is_zapf_attendee]
    result_exkursionen = wise18_calculate_exkursionen(registrations)
    result = []
    for name, data in result_exkursionen.items():
        buffer = ["\\exkursionspage{{{type}}}{{".format(type=EXKURSIONEN_TYPES[name][2])]
        for reg in data['registrations']:
            buffer.append("{} & {} \\\\ \\hline".format(reg[0].user.full_name, reg[0].uni.name))
        buffer.append("}")
        result.append("\n".join(buffer))
    return Response("\n".join(result), mimetype="application/x-latex")

@registration_blueprint.route('/admin/registration/report/wise18/unis/latex')
@groups_sufficient('admin', 'orga')
def registration_wise18_export_unis_latex():
    unis = Uni.query.all()
    result = []
    for uni in unis:
        uni_regs = [reg for reg in Registration.query.filter_by(uni_id = uni.id) if reg.is_zapf_attendee]
        if len(uni_regs) > 0:
            result.append("\\item{{{0}}}".format(uni.name))
    return Response("\n".join(result), mimetype="application/x-latex")

@registration_blueprint.route('/admin/registration/report/wise18/unis-teilnehmer/latex')
@groups_sufficient('admin', 'orga')
def registration_wise18_export_unis_teilnehmer_latex():
    unis = Uni.query.all()
    result = []
    for uni in unis:
        uni_regs = [reg for reg in Registration.query.filter_by(uni_id = uni.id) if reg.is_zapf_attendee]
        if len(uni_regs) > 0:
            result.append("\\item{{{0} - {1}}}".format(uni.name, len(uni_regs)))
    return Response("\n".join(result), mimetype="application/x-latex")

@registration_blueprint.route('/admin/registration/report/wise18/bestaetigungen/latex')
@groups_sufficient('admin', 'orga')
def registration_wise18_export_bestaetigungen_latex():
    registrations = [reg for reg in Registration.query.order_by(Registration.uni_id) if reg.is_zapf_attendee]
    result = []
    for reg in registrations:
        result.append("\\bestaetigung{{{}}}{{{}}}".format(reg.user.full_name, reg.uni.name))
    return Response("\n".join(result), mimetype="application/x-latex")

@registration_blueprint.route('/admin/registration/report/wise18/id_name/csv')
@groups_sufficient('admin', 'orga')
def registrations_wise18_export_id_name_csv():
    registrations = Registration.query.all()
    result = io.StringIO()
    writer = csv.writer(result, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows([[reg.id, "{} ({})".format(reg.user.full_name, reg.uni.name)]
                      for reg in registrations if reg.is_zapf_attendee])
    return Response(result.getvalue(), mimetype='text/csv')
