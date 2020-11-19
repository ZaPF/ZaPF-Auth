from flask import current_app, url_for
from flask_mail import Message


def send_password_reset_mail(user):
    msg = Message(
        f"{current_app.config['BRANDING']}: Passwort zurücksetzen",
        recipients=[user.mail],
        sender=current_app.config["MAIL_DEFAULT_SENDER"],
    )
    url = url_for(
        "user.reset_password_finish",
        username=user.username,
        token=user.reset_password[0],
        _external=True,
    )

    msg.body = """Hallo Benutzer "{0.username}",

du kannst dein Passwort auf folgender Website zurücksetzen:

{1}

Der Link ist für 1 Tag gültig.

Viele Grüße
Dein {2}}""".format(
        user, url, current_app.config["BRANDING"]
    )

    current_app.mail.send(msg)


def send_confirm_mail(user):
    msg = Message(
        f"{current_app.config['BRANDING']}: E-Mail bestätigen",
        recipients=[user.mail],
        sender=current_app.config["MAIL_DEFAULT_SENDER"],
    )
    url = url_for(
        "user.confirm_mail_finish",
        username=user.username,
        token=user.confirm_mail["token"],
        _external=True,
    )

    msg.body = """Hallo Benutzer "{0.username}",

um deine E-Mail zu bestätigen, gehe bitte auf folgende Website:

{1}

Der Link ist für 1 Tag gültig.

Viele Grüße
Dein {2}}""".format(
        user, url, current_app.config["BRANDING"]
    )

    current_app.mail.send(msg)
