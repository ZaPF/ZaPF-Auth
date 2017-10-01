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
  'lennestadt': ('Sauerland-Pyramiden', 20, 'Sauerland'),
  'vbsi': ('Versorgungsbetriebe Siegen', 20, 'Versorgungsbetriebe'),
  'fokos': ('FoKoS', 20, 'FoKoS'),
  'bwf': ('Bergwerksfuehrung', 20, 'Bergwerk'),
  'stf': ('Stadtführung', 20, 'Stadtführung'),
  'wandern': ('Wandern', 20, 'Wandern'),
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

@registration_blueprint.route('/admin/registration/report/wise17')
@groups_sufficient('admin', 'orga')
def registration_wise17_reports():
    return render_template('admin/wise17/reports.html')

@registration_blueprint.route('/admin/registration/report/wise17/exkursionen')
@groups_sufficient('admin', 'orga')
def registration_wise17_report_exkursionen():
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result = wise17_calculate_exkursionen(registrations)
    return render_template('admin/wise17/exkursionen.html',
        result = result,
        exkursionen_types = EXKURSIONEN_TYPES,
        exkursionen_types_birthday = EXKURSIONEN_TYPES_BIRTHDAY
    )

@registration_blueprint.route('/admin/registration/report/wise17/t-shirts')
@groups_sufficient('admin', 'orga')
def registration_wise17_report_tshirts():
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
    return render_template('admin/wise17/t-shirts.html',
        result = result,
        result_unis = result_unis,
        TSHIRTS_TYPES = TSHIRTS_TYPES
    )

@registration_blueprint.route('/admin/registration/report/wise17/hoodie')
@groups_sufficient('admin', 'orga')
def registration_wise17_report_hoodie():
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    unis = Uni.query.order_by(Uni.id)
    result = {}
    result_unis = {}
    result_muetze = []
    for uni in unis:
        result_unis[uni.id] = {
            'name': uni.name,
            'registrations': [],
            'types': {name: 0 for name, label in TSHIRTS_TYPES.items()}
        }
    for name, label in TSHIRTS_TYPES.items():
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
    return render_template('admin/wise17/hoodie.html',
        result = result,
        result_unis = result_unis,
        result_muetze = result_muetze,
        TSHIRTS_TYPES = TSHIRTS_TYPES
    )

@registration_blueprint.route('/admin/registration/report/wise17/essen')
@groups_sufficient('admin', 'orga')
def registration_wise17_report_essen():
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result_essen = {}
    result_heisse_getraenke = {}
    result_getraenkewunsch = []
    result_allergien = []
    result_mittag1 = {}
    result_mittag2 = {}
    result_mittag3 = {}
    for name, label in ESSEN_TYPES.items():
        result_essen[name] = {'label': label, 'registrations': []}
    for name, label in MITTAG1_TYPES.items():
        result_mittag1[name] = {'label': label, 'registrations': []}
    for name, label in MITTAG2_TYPES.items():
        result_mittag2[name] = {'label': label, 'registrations': []}
    for name, label in MITTAG3_TYPES.items():
        result_mittag3[name] = {'label': label, 'registrations': []}
    for name, label in HEISSE_GETRAENKE_TYPES.items():
        result_heisse_getraenke[name] = {'label': label, 'registrations': []}
    for reg in registrations:
        essen_type = reg.data['essen']
        heisse_getraenke = reg.data['heissgetraenk']
        getraenkewunsch = reg.data['getraenk']
        allergien = reg.data['allergien']
        mittag1_type = reg.data['mittag1']
        mittag2_type = reg.data['mittag2']
        mittag3_type = reg.data['mittag3']
        if (not result_essen[essen_type] or not result_heisse_getraenke[heisse_getraenke] or
            not result_mittag1[mittag1_type] or not result_mittag2[mittag2_type] or not result_mittag3[mittag3_type]):
            return None
        result_essen[essen_type]['registrations'].append(reg)
        if essen_type == 'vegetarisch' or essen_type == 'vegan':
            result_mittag1['vegan']['registrations'].append(reg)
            result_mittag2['vegan']['registrations'].append(reg)
            result_mittag3['vegan']['registrations'].append(reg)
        else:
            result_mittag1[mittag1_type]['registrations'].append(reg)
            result_mittag2[mittag2_type]['registrations'].append(reg)
            result_mittag3[mittag3_type]['registrations'].append(reg)
        result_heisse_getraenke[heisse_getraenke]['registrations'].append(reg)
        if getraenkewunsch:
            result_getraenkewunsch.append(reg)
        if allergien:
            result_allergien.append(reg)
    return render_template('admin/wise17/essen.html',
        result_essen = result_essen,
        result_heisse_getraenke = result_heisse_getraenke,
        result_getraenkewunsch = result_getraenkewunsch,
        result_allergien = result_allergien,
        result_mittag1 = result_mittag1,
        result_mittag2 = result_mittag2,
        result_mittag3 = result_mittag3
    )

@registration_blueprint.route('/admin/registration/report/wise17/rahmenprogramm')
@groups_sufficient('admin', 'orga')
def registration_wise17_report_rahmenprogramm():
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result_mittwoch = []
    result_musikwunsch = []
    for reg in registrations:
        mittwoch = reg.data['workshop']
        musikwunsch = reg.data['musikwunsch']
        if mittwoch:
            result_mittwoch.append(reg)
        if musikwunsch:
            result_musikwunsch.append(reg)
    return render_template('admin/wise17/rahmenprogramm.html',
        result_mittwoch = result_mittwoch,
        result_musikwunsch = result_musikwunsch
    )

@registration_blueprint.route('/admin/registration/report/wise17/sonstiges')
@groups_sufficient('admin', 'orga')
def registration_wise17_report_sonstiges():
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result_schlafen = {}
    result_addx = []
    for name, label in SCHLAFEN_TYPES.items():
        result_schlafen[name] = {'label': label, 'registrations': []}
    for reg in registrations:
        schlafen_type = reg.data['schlafen']
        addx = reg.data['addx']
        result_schlafen[schlafen_type]['registrations'].append(reg)
        if addx:
            result_addx.append(reg)
    return render_template('admin/wise17/sonstiges.html',
        result_schlafen = result_schlafen,
        result_addx = result_addx
    )

@registration_blueprint.route('/admin/registration/report/wise17/spitznamen')
@groups_sufficient('admin', 'orga')
def registration_wise17_report_spitznamen():
    registrations = [reg for reg in Registration.query.order_by(Registration.id) if reg.is_zapf_attendee]
    result = {'with': [], 'without': []}
    for reg in registrations:
        spitzname = reg.data['spitzname']
        if spitzname and spitzname != "-":
            result['with'].append(reg)
        else:
            result['without'].append(reg)
    return render_template('admin/wise17/spitznamen.html',
        result = result
    )

@registration_blueprint.route('/admin/registration/<int:reg_id>/details_wise17', methods=['GET', 'POST'])
@groups_sufficient('admin', 'orga')
def registration_wise17_details_registration(reg_id):
    reg = Registration.query.filter_by(id=reg_id).first()
    form = Winter17ExkursionenOverwriteForm()
    if form.validate_on_submit():
        data = reg.data
        old_spitzname = data['spitzname']
        if 'exkursion_overwrite' in reg.data:
            old_overwrite = data['exkursion_overwrite']
        data['spitzname'] = form.spitzname.data
        data['exkursion_overwrite'] = form.exkursion_overwrite.data
        reg.data = data
        db.session.add(reg)
        db.session.commit()
        if old_spitzname != form.spitzname.data:
            return redirect(url_for('registration.registration_wise17_report_spitznamen'))
        elif old_overwrite and old_overwrite != form.exkursion_overwrite.data:
            return redirect(url_for('registration.registration_wise17_report_exkursionen'))
        else:
            return redirect(url_for('registration.registration_wise17_details_registration', reg_id = reg_id))
    if 'exkursion_overwrite' in reg.data:
        form.exkursion_overwrite.data = reg.data['exkursion_overwrite']
    form.spitzname.data = reg.data['spitzname']
    return render_template('admin/wise17/details.html',
        reg = reg,
        form = form,
        EXKURSIONEN_TYPES = EXKURSIONEN_TYPES,
        ESSEN_TYPES = ESSEN_TYPES,
        MITTAG1_TYPES = MITTAG1_TYPES,
        MITTAG2_TYPES = MITTAG2_TYPES,
        MITTAG3_TYPES = MITTAG3_TYPES,
        TSHIRTS_TYPES = TSHIRTS_TYPES,
        SCHLAFEN_TYPES = SCHLAFEN_TYPES,
        HEISSE_GETRAENKE_TYPES = HEISSE_GETRAENKE_TYPES,
        ANREISE_TYPES = ANREISE_TYPES
    )

@registration_blueprint.route('/admin/registration/report/wise17/stimmkarten/latex')
@groups_sufficient('admin', 'orga')
def registration_wise17_export_stimmkarten_latex():
    unis = Uni.query.all()
    result = []
    for uni in unis:
        uni_regs = [reg for reg in Registration.query.filter_by(uni_id = uni.id) if reg.is_zapf_attendee]
        if len(uni_regs) > 0:
            result.append("\\stimmkarte{{{0}}}".format(uni.name))
    return Response("\n".join(result), mimetype="application/x-latex")

@registration_blueprint.route('/admin/registration/report/wise17/idkarten/latex')
@groups_sufficient('admin', 'orga')
def registration_wise17_export_idkarten_latex():
    result = ["\\idcard{{{}}}{{{}}}{{{}}}".format(reg.id, reg.user.full_name, reg.uni.name)
                for reg in Registration.query.order_by(Registration.uni_id) if reg.is_zapf_attendee]
    return Response("\n".join(result), mimetype="application/x-latex")

@registration_blueprint.route('/admin/registration/report/wise17/tagungsausweise/latex')
@groups_sufficient('admin', 'orga')
def registration_wise17_export_tagungsausweise_latex():
    def get_sort_key(entry):
        return entry[0]
    registrations = [reg for reg in Registration.query.all() if reg.is_zapf_attendee]
    result_exkursionen = wise17_calculate_exkursionen(registrations)
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

@registration_blueprint.route('/admin/registration/report/wise17/strichlisten/latex')
@groups_sufficient('admin', 'orga')
def registration_wise17_export_strichlisten_latex():
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

@registration_blueprint.route('/admin/registration/report/wise17/bmbflisten/latex')
@groups_sufficient('admin', 'orga')
def registration_wise17_export_bmbflisten_latex():
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

@registration_blueprint.route('/admin/registration/report/wise17/taschentassenlisten/latex')
@groups_sufficient('admin', 'orga')
def registration_wise17_export_taschentassenlisten_latex():
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

@registration_blueprint.route('/admin/registration/report/wise17/ausweisidbeitraglisten/latex')
@groups_sufficient('admin', 'orga')
def registration_wise17_export_ausweisidbeitraglisten_latex():
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

@registration_blueprint.route('/admin/registration/report/wise17/t-shirt/latex')
@groups_sufficient('admin', 'orga')
def registration_wise17_export_t_shirt_latex():
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

@registration_blueprint.route('/admin/registration/report/wise17/wichteln/csv')
@groups_sufficient('admin', 'orga')
def registrations_wise17_export_wichteln_csv():
    registrations = Registration.query.all()
    result = io.StringIO()
    writer = csv.writer(result, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows([[reg.user.full_name, reg.uni.name, reg.data['spitzname']]
                      for reg in registrations if reg.is_zapf_attendee])
    return Response(result.getvalue(), mimetype='text/csv')

@registration_blueprint.route('/admin/registration/report/wise17/exkursionen/latex')
@groups_sufficient('admin', 'orga')
def registration_wise17_export_exkursionen_latex():
    registrations = [reg for reg in Registration.query.all() if reg.is_zapf_attendee]
    result_exkursionen = wise17_calculate_exkursionen(registrations)
    result = []
    for name, data in result_exkursionen.items():
        buffer = ["\\exkursionspage{{{type}}}{{".format(type=EXKURSIONEN_TYPES[name][2])]
        for reg in data['registrations']:
            buffer.append("{} & {} \\\\ \\hline".format(reg[0].user.full_name, reg[0].uni.name))
        buffer.append("}")
        result.append("\n".join(buffer))
    return Response("\n".join(result), mimetype="application/x-latex")

@registration_blueprint.route('/admin/registration/report/wise17/unis/latex')
@groups_sufficient('admin', 'orga')
def registration_wise17_export_unis_latex():
    unis = Uni.query.all()
    result = []
    for uni in unis:
        uni_regs = [reg for reg in Registration.query.filter_by(uni_id = uni.id) if reg.is_zapf_attendee]
        if len(uni_regs) > 0:
            result.append("\\item{{{0}}}".format(uni.name))
    return Response("\n".join(result), mimetype="application/x-latex")

@registration_blueprint.route('/admin/registration/report/wise17/unis-teilnehmer/latex')
@groups_sufficient('admin', 'orga')
def registration_wise17_export_unis_teilnehmer_latex():
    unis = Uni.query.all()
    result = []
    for uni in unis:
        uni_regs = [reg for reg in Registration.query.filter_by(uni_id = uni.id) if reg.is_zapf_attendee]
        if len(uni_regs) > 0:
            result.append("\\item{{{0} - {1}}}".format(uni.name, len(uni_regs)))
    return Response("\n".join(result), mimetype="application/x-latex")

@registration_blueprint.route('/admin/registration/report/wise17/bestaetigungen/latex')
@groups_sufficient('admin', 'orga')
def registration_wise17_export_bestaetigungen_latex():
    registrations = [reg for reg in Registration.query.order_by(Registration.uni_id) if reg.is_zapf_attendee]
    result = []
    for reg in registrations:
        result.append("\\bestaetigung{{{}}}{{{}}}".format(reg.user.full_name, reg.uni.name))
    return Response("\n".join(result), mimetype="application/x-latex")

@registration_blueprint.route('/admin/registration/report/wise17/id_name/csv')
@groups_sufficient('admin', 'orga')
def registrations_wise17_export_id_name_csv():
    registrations = Registration.query.all()
    result = io.StringIO()
    writer = csv.writer(result, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows([[reg.id, "{} ({})".format(reg.user.full_name, reg.uni.name)]
                      for reg in registrations if reg.is_zapf_attendee])
    return Response(result.getvalue(), mimetype='text/csv')
