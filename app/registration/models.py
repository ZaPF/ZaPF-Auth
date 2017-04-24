from app.db import db
from app.user.models import User
from flask import Blueprint, abort, current_app

class Registration(db.Model):
    id = db.Column(db.Integer(), primary_key = True)
    username = db.Column(db.Text(), unique = True)
    blob = db.Column(db.Text())
    _priority = db.Column('priority', db.Integer())
    _confirmed = db.Column('confirmed', db.Boolean())
    uni_id = db.Column(db.Integer(), db.ForeignKey('uni.id'))
    uni = db.relationship('Uni', backref=db.backref('Registrations', lazy='dynamic', cascade="all, delete-orphan"))

    @property
    def user(self):
        return User.get(self.username)

    @property
    def is_guaranteed(self):
        return any(map(self.user.is_in_group, current_app.config['ZAPF_GUARANTEED_GROUPS']))

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

class Uni(db.Model):
    id = db.Column(db.Integer(), primary_key = True)
    token = db.Column(db.String(256), unique = True)
    name = db.Column(db.Text(), unique = True)
    slots = db.Column(db.Integer())

    def __init__(self, name, token, slots = 3):
        self.name = name
        self.token = token
        self.slots = slots

    def __repr__(self):
        return "<Uni: {}>".format(self.name)
