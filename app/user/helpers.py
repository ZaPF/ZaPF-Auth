from flask import current_app, url_for, render_template, flash, redirect
from flask_mail import Message
from .models import User


class EmailConfirmation(object):
    _confirm_mail_token = None
    TOKEN_NAMESPACE = "confirm_mail"

    @classmethod
    def get(cls, token):
        key = cls.cache_key(token)
        print(key)
        instance = current_app.cache.get(key)
        return instance

    @classmethod
    def cache_key(cls, token):
        return "user/{namespace}/{token}".format(
            namespace=cls.TOKEN_NAMESPACE, token=token
        )

    def __init__(self, username, mail, subject, body):
        self.subject = subject
        self.body = body
        self.send_mail(username, mail)
        cache_key = self.cache_key(self.confirm_mail_token)
        print(cache_key)
        current_app.cache.set(cache_key, self)

    @property
    def confirm_mail_token(self):
        if self._confirm_mail_token is None:
            import secrets

            self._confirm_mail_token = secrets.token_urlsafe(
                current_app.config["CONFIRM_MAIL_TOKEN_LENGTH"]
            )
        return self._confirm_mail_token

    def send_mail(self, username, mail):
        msg = Message(
            self.subject,
            recipients=[mail],
            sender=current_app.config["MAIL_DEFAULT_SENDER"],
        )

        msg.body = self.body

        if current_app.config["MAIL_SUPPRESS_SEND"]:
            # log mail instead
            print(" * Would send the following mail:")
            print(msg)

        current_app.mail.send(msg)

    def confirm(self):
        raise NotImplementedError()


class UserCreationRequest(EmailConfirmation):
    """
    Represents a user with an unconfirmed email. Not added to the LDAP yet, but
    saved in the cache.
    """

    def __init__(self, username, password, mail, *args, **kwargs):
        kwargs.update(
            {
                "username": username,
                "password": password,
                "mail": mail,
            }
        )

        self.params = (args, kwargs)
        subject = "{branding}: E-Mail bestätigen".format(
            branding=current_app.config["BRANDING"]
        )
        url = url_for(
            "user.confirm_mail_finish",
            token=self.confirm_mail_token,
            _external=True,
        )
        body = render_template(
            "confirm_mail.j2",
            username=username,
            url=url,
            branding=current_app.config["BRANDING"],
        )
        super(UserCreationRequest, self).__init__(username, mail, subject, body)

    def confirm(self):
        User.create(*self.params[0], **self.params[1])
        flash("Your user account has been created!", "success")
        return redirect("/")


class UserEmailChangeRequest(EmailConfirmation):
    def __init__(self, username, mail):
        self.username = username
        self.mail = mail
        subject = "{branding}: E-Mail bestätigen".format(
            branding=current_app.config["BRANDING"]
        )

        url = url_for(
            "user.confirm_mail_finish",
            token=self.confirm_mail_token,
            _external=True,
        )

        body = render_template(
            "confirm_mail.j2",
            username=username,
            url=url,
            branding=current_app.config["BRANDING"],
        )
        super(UserEmailChangeRequest, self).__init__(username, mail, subject, body)

    def confirm(self):
        user = User.get(self.username)

        if not user:
            raise Exception("Invalid user in email change request!")

        user.mail = self.mail
        user.save()
        flash("E-Mail confirmed", "success")
        return redirect("/")


class PasswordResetRequest(EmailConfirmation):
    TOKEN_NAMESPACE = "reset_password"

    def __init__(self, username):
        self._user = None
        self.username = username
        subject = "{branding}: Passwort zurücksetzen".format(
            branding=current_app.config["BRANDING"]
        )
        url = url_for(
            "user.reset_password_finish",
            token=self.confirm_mail_token,
            _external=True,
        )

        body = render_template(
            "password_reset_mail.j2",
            username=username,
            url=url,
            branding=current_app.config["BRANDING"],
        )
        super(PasswordResetRequest, self).__init__(
            username, self.user.mail, subject, body
        )

    @property
    def user(self):
        if not self._user:
            self._user = User.get(self.username)
        return self._user

    def confirm(self, password):
        self.user.password = password
        self.user.save()
        flash("New password has been set.", "info")
        return redirect(url_for("user.login"))
