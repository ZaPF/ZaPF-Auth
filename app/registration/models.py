from app.db import db
from app.user.models import User
from flask import Blueprint, abort, current_app, json


class Registration(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.Text(), unique=True)
    blob = db.Column(db.Text())
    _priority = db.Column("priority", db.Integer())
    _confirmed = db.Column("confirmed", db.Boolean())
    uni_id = db.Column(db.Integer(), db.ForeignKey("uni.id"))
    uni = db.relationship(
        "Uni",
        backref=db.backref(
            "Registrations", lazy="dynamic", cascade="all, delete-orphan"
        ),
    )

    @property
    def user(self):
        return User.get(self.username)

    @property
    def is_guaranteed(self):
        return any(
            map(self.user.is_in_group, current_app.config["ZAPF_GUARANTEED_GROUPS"])
        )

    @property
    def confirmed(self):
        return self._confirmed or self.is_guaranteed

    @confirmed.setter
    def confirmed(self, value):
        if not self.is_guaranteed:
            self._confirmed = value

    @property
    def priority(self):
        return self._priority if not self.is_guaranteed else -1

    @priority.setter
    def priority(self, value):
        self._priority = value if not self.is_guaranteed else None

    @property
    def data(self):
        return json.loads(self.blob)

    @data.setter
    def data(self, value):
        self.blob = json.dumps(value)

    @property
    def is_zapf_attendee(self):
        return self.confirmed and self.priority < self.uni.slots


class Uni(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    token = db.Column(db.String(256), unique=True)
    name = db.Column(db.Text(), unique=True)
    slots = db.Column(db.Integer())

    def __init__(self, name, token, slots=3):
        self.name = name
        self.token = token
        self.slots = slots

    def __repr__(self):
        return "<Uni: {}>".format(self.name)


class Mascot(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.Text(), unique=False)
    uni_id = db.Column(db.Integer(), db.ForeignKey("uni.id"))
    uni = db.relationship(
        "Uni",
        backref=db.backref("Mascots", lazy="dynamic", cascade="all, delete-orphan"),
    )

    def __init__(self, name, uni_id):
        self.name = name
        self.uni_id = uni_id

    def __repr__(self):
        return "<Mascot: {}>".format(self.name)
