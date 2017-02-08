from flask import current_app
from flask_mail import Message

def send_registration_success_mail(user):
    msg = Message("ZaPF-Anmeldung gespeichert", recipients=[user.mail],
            sender=current_app.config['MAIL_NEXT_ZAPF_ORGA'])

    msg.body = """Hallo {0.firstName},

deine Anmeldung zur ZaPF wurde erfolgreich gespeichert. Solange
der Anmeldezeitraum noch läuft, kannst du aber jederzeit deine
Daten noch anpassen.

Viele Grüße
Deine ZaPF-Orga""".format(user)

    current_app.mail.send(msg)
