from app.db import db
from app.user.models import User
from flask import Blueprint, abort, current_app, json

RecipientToList = db.Table('recipient_to_list',
    db.Column('list_id', db.Integer, db.ForeignKey('recipients_lists.id'), primary_key=True),
    db.Column('recipient_id', db.Integer, db.ForeignKey('recipients.id'), primary_key=True),
    info={'bind_key': 'stapf'}
)

DecisionRecipientsLists = db.Table('decision_recipients_lists',
    db.Column('decision_id', db.Integer, db.ForeignKey('decisions.id'), primary_key=True),
    db.Column('recipients_list_id', db.Integer, db.ForeignKey('recipients_lists.id'), primary_key=True),
    info={'bind_key': 'stapf'}
)

class Recipient(db.Model):
    __bind_key__ = 'stapf'
    __tablename__ = 'recipients'
    id = db.Column(db.Integer(), primary_key = True)
    name = db.Column(db.Text())
    organisation_name = db.Column(db.Text())
    addressline1 = db.Column(db.Text())
    addressline2 = db.Column(db.Text())
    street = db.Column(db.Text())
    postal_code = db.Column(db.Integer())
    locality = db.Column(db.Text())
    country = db.Column(db.Text())
    mail = db.Column(db.Text())
    comment = db.Column(db.Text())

    @property
    def has_address(self):
        return self.street and self.locality

class RecipientsList(db.Model):
    __bind_key__ = 'stapf'
    __tablename__ = 'recipients_lists'
    id = db.Column(db.Integer(), primary_key = True)
    name = db.Column(db.Text(), unique = True)
    recipients = db.relationship("Recipient", secondary=RecipientToList, backref=db.backref('lists', lazy=True))
    comment = db.Column(db.Text())

class Decision(db.Model):
    __bind_key__ = 'stapf'
    __tablename__ = 'decisions'
    id = db.Column(db.Integer(), primary_key = True)
    title = db.Column(db.Text())
    decided = db.Column(db.Date())
    recipients_lists = db.relationship("RecipientsList", secondary=DecisionRecipientsLists, backref=db.backref('decisions', lazy=True))
    filename = db.Column(db.Text())
    file_path = db.Column(db.Text())
    comment = db.Column(db.Text())

class Batch(db.Model):
    __bind_key__ = 'stapf'
    __tablename__ = 'batches'
    id = db.Column(db.Integer(), primary_key = True)
    subject = db.Column(db.Text())
    message = db.Column(db.Text())
    decision_id = db.Column(db.Integer(), db.ForeignKey('decisions.id'))
    decision = db.relationship("Decision", backref=db.backref('batches', lazy=True))
    sent = db.Column(db.Boolean(), default=False)
    sent_at = db.Column(db.DateTime())
    comment = db.Column(db.Text())
