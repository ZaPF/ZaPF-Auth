from flask import render_template, redirect, url_for, flash, current_app, send_file
from . import stapf_blueprint
from app.db import db
from .models import Recipient, RecipientsList, Decision, Batch
from .helpers import import_recipients_from_list, send_batch_mails
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, TextAreaField, SubmitField, IntegerField, SelectField, SelectMultipleField, validators
from wtforms.fields.html5 import EmailField, DateField
from werkzeug.utils import secure_filename
from app.user import groups_sufficient
from app.views import confirm
import os
import datetime

class RecipientForm(FlaskForm):
    name = StringField('Name')
    organisation_name = StringField('Organisation')
    addressline1 = StringField('Adresszeile 1')
    addressline2 = StringField('Adresszeile 2')
    street = StringField('Straße und Hausnummer')
    postal_code = IntegerField('PLZ', validators=[validators.Optional()])
    locality = StringField('Ort')
    country = StringField('Staat', default='Deutschland')
    mail = EmailField('E-Mail')
    comment = TextAreaField('Kommentar')
    submit = SubmitField()

class RecipientsListForm(FlaskForm):
    name = StringField('Name')
    recipients = SelectMultipleField('Adressaten', coerce=int)
    comment = TextAreaField('Kommentar')
    submit = SubmitField()

class RecipientsListImportMailsForm(FlaskForm):
    name = StringField('Name')
    recipients = TextAreaField('Adressaten als Liste')
    comment = TextAreaField('Kommentar')
    submit = SubmitField()

class DecisionForm(FlaskForm):
    title = StringField('Titel')
    decided = DateField('Beschlossen am', validators=[validators.Required()])
    recipients_lists = SelectMultipleField('Adressaten-Listen', coerce=int)
    upload = FileField('Beschluss als PDF', validators=[FileAllowed(['pdf'], 'PDFs only!')])
    comment = TextAreaField('Kommentar')
    submit = SubmitField()

class BatchForm(FlaskForm):
    subject = StringField('Betreff')
    message = TextAreaField('Anschreiben')
    decision = SelectField('Beschluss', coerce=int, validators=[validators.Required()])
    comment = TextAreaField('Kommentar')
    submit = SubmitField()

@stapf_blueprint.route('/stapf/recipients')
@groups_sufficient('admin', 'StAPF')
def recipients():
    recipients = Recipient.query.order_by(Recipient.name)
    return render_template('recipients.html',
        recipients = recipients
    )

@stapf_blueprint.route('/stapf/recipient/new', methods=['GET', 'POST'])
@groups_sufficient('admin', 'StAPF')
def recipient_new():
    form = RecipientForm()
    if form.validate_on_submit():
       recipient = Recipient()
       recipient.name = form.name.data
       recipient.organisation_name = form.organisation_name.data
       recipient.addressline1 = form.addressline1.data
       recipient.addressline2 = form.addressline2.data
       recipient.street = form.street.data
       recipient.postal_code = form.postal_code.data
       recipient.locality = form.locality.data
       recipient.country = form.country.data
       recipient.mail = form.mail.data
       recipient.comment = form.comment.data
       db.session.add(recipient)
       db.session.commit()
       flash('Adressat erfolgreich angelegt', 'success')
       return redirect(url_for('stapf.recipients'))

    return render_template('recipient.html',
        form = form
    )

@stapf_blueprint.route('/stapf/recipient/<int:recipient_id>', methods=['GET', 'POST'])
@groups_sufficient('admin', 'StAPF')
def recipient(recipient_id):
    recipient = Recipient.query.filter_by(id=recipient_id).first()
    form = RecipientForm()
    if form.validate_on_submit():
       recipient.name = form.name.data
       recipient.organisation_name = form.organisation_name.data
       recipient.addressline1 = form.addressline1.data
       recipient.addressline2 = form.addressline2.data
       recipient.street = form.street.data
       recipient.postal_code = form.postal_code.data
       recipient.locality = form.locality.data
       recipient.country = form.country.data
       recipient.mail = form.mail.data
       recipient.comment = form.comment.data
       db.session.add(recipient)
       db.session.commit()
       flash('Adressat erfolgreich geändert', 'success')
       return redirect(url_for('stapf.recipients'))

    form.name.data = recipient.name
    form.organisation_name.data = recipient.organisation_name
    form.addressline1.data = recipient.addressline1
    form.addressline2.data = recipient.addressline2
    form.street.data = recipient.street
    form.postal_code.data = recipient.postal_code
    form.locality.data = recipient.locality
    form.country.data = recipient.country
    form.mail.data = recipient.mail
    form.comment.data = recipient.comment
    return render_template('recipient.html',
        form = form
    )

@stapf_blueprint.route('/stapf/recipient/<int:recipient_id>/delete', methods=['GET', 'POST'])
@groups_sufficient('admin', 'StAPF')
@confirm(title='Lösche Adressat',
        action='Löschen',
        back='stapf.recipients')
def recipient_delete(recipient_id):
    recipient = Recipient.query.filter_by(id=recipient_id).first()
    db.session.delete(recipient)
    db.session.commit()
    flash('Adressat "{}" wurde gelöscht'.format(recipient.name), 'success')
    return redirect(url_for('stapf.recipients'))

@stapf_blueprint.route('/stapf/recipients_lists')
@groups_sufficient('admin', 'StAPF')
def recipients_lists():
    recipients_lists = RecipientsList.query.order_by(RecipientsList.name)
    return render_template('recipients_lists.html',
        recipients_lists = recipients_lists
    )

@stapf_blueprint.route('/stapf/recipients_list/new', methods=['GET', 'POST'])
@groups_sufficient('admin', 'StAPF')
def recipients_list_new():
    form = RecipientsListForm()
    form.recipients.choices = [(r.id, "{} ({})".format(r.name, r.organisation_name))
                               for r in Recipient.query.order_by(Recipient.name)]
    if form.validate_on_submit():
       recipients_list = RecipientsList()
       recipients_list.name = form.name.data
       recipients_list.recipients = [Recipient.query.filter_by(id=i).first() for i in form.recipients.data]
       recipients_list.comment = form.comment.data
       db.session.add(recipients_list)
       db.session.commit()
       flash('Adressaten-Liste erfolgreich angelegt', 'success')
       return redirect(url_for('stapf.recipients_lists'))

    return render_template('recipients_list.html',
        form = form
    )

@stapf_blueprint.route('/stapf/recipients_list/<int:recipients_list_id>', methods=['GET', 'POST'])
@groups_sufficient('admin', 'StAPF')
def recipients_list(recipients_list_id):
    recipients_list = RecipientsList.query.filter_by(id=recipients_list_id).first()
    form = RecipientsListForm()
    form.recipients.choices = [(r.id, "{} ({})".format(r.name, r.organisation_name))
                               for r in Recipient.query.order_by(Recipient.name)]
    if form.validate_on_submit():
       recipients_list.name = form.name.data
       recipients_list.recipients = [Recipient.query.filter_by(id=i).first() for i in form.recipients.data]
       recipients_list.comment = form.comment.data
       db.session.add(recipients_list)
       db.session.commit()
       flash('Adressaten-Liste erfolgreich geändert', 'success')
       return redirect(url_for('stapf.recipients_lists'))

    form.name.data = recipients_list.name
    form.recipients.data = [r.id for r in recipients_list.recipients]
    form.comment.data = recipients_list.comment
    return render_template('recipients_list.html',
        form = form
    )

@stapf_blueprint.route('/stapf/recipients_list/<int:recipients_list_id>/delete', methods=['GET', 'POST'])
@groups_sufficient('admin', 'StAPF')
@confirm(title='Lösche Adressaten-Liste',
        action='Löschen',
        back='stapf.recipients_lists')
def recipients_list_delete(recipients_list_id):
    recipients_list = RecipientsList.query.filter_by(id=recipients_list_id).first()
    db.session.delete(recipients_list)
    db.session.commit()
    flash('Adressaten-Liste "{}" wurde gelöscht'.format(recipients_list.name), 'success')
    return redirect(url_for('stapf.recipients_lists'))

@stapf_blueprint.route('/stapf/recipients_list/import_mails', methods=['GET', 'POST'])
@groups_sufficient('admin', 'StAPF')
def recipients_list_import_mails():
    form = RecipientsListImportMailsForm()
    if form.validate_on_submit():
       recipients_list = RecipientsList()
       recipients_list.name = form.name.data
       recipients_list.recipients = import_recipients_from_list(form.recipients.data)
       recipients_list.comment = form.comment.data
       db.session.add(recipients_list)
       db.session.commit()
       flash('Adressaten-Liste erfolgreich importiert', 'success')
       return redirect(url_for('stapf.recipients_lists'))

    return render_template('recipients_list_import.html',
        form = form
    )

@stapf_blueprint.route('/stapf/decisions')
@groups_sufficient('admin', 'StAPF')
def decisions():
    decisions = Decision.query.order_by(Decision.decided)
    return render_template('decisions.html',
        decisions = decisions
    )

@stapf_blueprint.route('/stapf/decision/new', methods=['GET', 'POST'])
@groups_sufficient('admin', 'StAPF')
def decision_new():
    form = DecisionForm()
    form.recipients_lists.choices = [(l.id, l.name) for l in RecipientsList.query.order_by(RecipientsList.name)]
    form.upload.validators.append(FileRequired())
    if form.validate_on_submit():
       decision = Decision()
       decision.title = form.title.data
       decision.recipients_lists = [RecipientsList.query.filter_by(id=i).first() for i in form.recipients_lists.data]
       decision.decided = form.decided.data
       decision.comment = form.comment.data
       db.session.add(decision)
       db.session.flush()

       f = form.upload.data
       filename = secure_filename(f.filename)
       file_path = os.path.join(current_app.config['STAPF_DECISIONS_PATH'], "{}_{}".format(decision.id, filename))
       f.save(file_path)
       decision.filename = filename
       decision.file_path = file_path

       db.session.commit()
       flash('Beschluss erfolgreich angelegt', 'success')
       return redirect(url_for('stapf.decisions'))

    return render_template('decision.html',
        form = form,
        isNew = True
    )

@stapf_blueprint.route('/stapf/decision/<int:decision_id>', methods=['GET', 'POST'])
@groups_sufficient('admin', 'StAPF')
def decision(decision_id):
    decision = Decision.query.filter_by(id=decision_id).first()
    form = DecisionForm()
    form.recipients_lists.choices = [(l.id, l.name) for l in RecipientsList.query.order_by(RecipientsList.name)]
    if form.validate_on_submit():
       decision.title = form.title.data
       decision.recipients_lists = [RecipientsList.query.filter_by(id=i).first() for i in form.recipients_lists.data]
       decision.decided = form.decided.data
       decision.comment = form.comment.data

       db.session.add(decision)
       db.session.commit()
       flash('Beschluss erfolgreich geändert', 'success')
       return redirect(url_for('stapf.decisions'))

    form.title.data = decision.title
    form.recipients_lists.data = [l.id for l in decision.recipients_lists]
    form.decided.data = decision.decided
    form.comment.data = decision.comment

    return render_template('decision.html',
        form = form,
        isNew = False,
        decision_id = decision_id
    )

@stapf_blueprint.route('/stapf/decision/<int:decision_id>/file')
@groups_sufficient('admin', 'StAPF')
def decision_file(decision_id):
    decision = Decision.query.filter_by(id=decision_id).first()
    return send_file(decision.file_path, mimetype='application/pdf', as_attachment=True, attachment_filename=decision.filename)

@stapf_blueprint.route('/stapf/decision/<int:decision_id>/delete', methods=['GET', 'POST'])
@groups_sufficient('admin', 'StAPF')
@confirm(title='Lösche Beschluss',
        action='Löschen',
        back='stapf.decisions')
def decision_delete(decision_id):
    decision = Decision.query.filter_by(id=decision_id).first()
    db.session.delete(decision)
    db.session.commit()
    os.remove(decision.file_path)
    flash('Beschluss "{}" wurde gelöscht'.format(decision.title), 'success')
    return redirect(url_for('stapf.decisions'))

@stapf_blueprint.route('/stapf/batches')
@groups_sufficient('admin', 'StAPF')
def batches():
    batches = Batch.query.order_by(Batch.sent)
    return render_template('batches.html',
        batches = batches
    )

@stapf_blueprint.route('/stapf/batch/new', methods=['GET', 'POST'])
@groups_sufficient('admin', 'StAPF')
def batch_new():
    form = BatchForm()
    form.decision.choices = [(d.id, d.title) for d in Decision.query.order_by(Decision.decided)]
    if form.validate_on_submit():
       batch = Batch()
       batch.subject = form.subject.data
       batch.message = form.message.data
       batch.decision_id = form.decision.data
       batch.comment = form.comment.data
       db.session.add(batch)
       db.session.commit()
       flash('Mail-Auftrag erfolgreich angelegt', 'success')
       return redirect(url_for('stapf.batches'))

    return render_template('batch.html',
        form = form
    )

@stapf_blueprint.route('/stapf/batch/<int:batch_id>', methods=['GET', 'POST'])
@groups_sufficient('admin', 'StAPF')
def batch(batch_id):
    batch = Batch.query.filter_by(id=batch_id).first()
    form = BatchForm()
    form.decision.choices = [(d.id, d.title) for d in Decision.query.order_by(Decision.decided)]
    if not batch.sent and form.validate_on_submit():
       batch.subject = form.subject.data
       batch.message = form.message.data
       batch.decision_id = form.decision.data
       batch.comment = form.comment.data
       db.session.add(batch)
       db.session.commit()
       flash('Mail-Auftrag erfolgreich geändert', 'success')
       return redirect(url_for('stapf.batches'))

    form.subject.data = batch.subject
    form.message.data = batch.message
    form.decision.data = batch.decision_id
    form.comment.data = batch.comment
    return render_template('batch.html',
        form = form,
        readonly = batch.sent
    )

@stapf_blueprint.route('/stapf/batch/<int:batch_id>/send', methods=['GET', 'POST'])
@groups_sufficient('admin', 'StAPF')
@confirm(title='Versende Mail-Auftrag',
        action='Senden',
        back='stapf.batches')
def batch_send(batch_id):
    batch = Batch.query.filter_by(id=batch_id).first()
    if batch.sent:
        flash('Mail-Auftrag "{}" wurde bereits versendet. Bitte neuen Auftrag, wenn nötig, anlegen'.format(batch.subject), 'warning')
        return redirect(url_for('stapf.batches'))
    send_batch_mails(batch)
    batch.sent = True
    batch.sent_at = datetime.datetime.now()
    db.session.add(batch)
    db.session.commit()
    flash('Mail-Auftrag "{}" wurde versendet'.format(batch.subject), 'success')
    return redirect(url_for('stapf.batches'))

@stapf_blueprint.route('/stapf/batch/<int:batch_id>/delete', methods=['GET', 'POST'])
@groups_sufficient('admin', 'StAPF')
@confirm(title='Lösche Mail-Auftrag',
        action='Löschen',
        back='stapf.batches')
def batch_delete(batch_id):
    batch = Batch.query.filter_by(id=batch_id).first()
    db.session.delete(batch)
    db.session.commit()
    flash('Mail-Auftrag "{}" wurde gelöscht'.format(batch.subject), 'success')
    return redirect(url_for('stapf.batches'))
