import email.utils
from app.db import db
from .models import Recipient
from flask import current_app
from flask_mail import Message

def import_recipients_from_list(mail_list):
    result = []
    for line in mail_list.splitlines():
        parsed_mail = email.utils.parseaddr(line)
        recipient = Recipient()
        recipient.name = parsed_mail[0]
        recipient.mail = parsed_mail[1]
        recipient.comment = 'Automatisch importiert (bitte überprüfen)'
        db.session.add(recipient)
        result.append(recipient)
    db.session.commit()
    return result

def send_batch_mails(batch):
    with current_app.mail.connect() as conn:
        for recipients_list in batch.decision.recipients_lists:
            for recipient in recipients_list.recipients:
                if not recipient.mail:
                    continue
                msg = Message(batch.subject, recipients=[recipient.mail],
                        body=batch.message, sender=current_app.config['MAIL_STAPF'])
                with current_app.open_resource(batch.decision.file_path) as fp:
                    msg.attach(batch.decision.filename, "application/pdf", fp.read())
                conn.send(msg)

        msg = Message(batch.subject, recipients=[current_app.config['MAIL_STAPF']],
                      body=batch.message, sender=current_app.config['MAIL_STAPF'])
        with current_app.open_resource(batch.decision.file_path) as fp:
            msg.attach(batch.decision.filename, "application/pdf", fp.read())
        conn.send(msg)

