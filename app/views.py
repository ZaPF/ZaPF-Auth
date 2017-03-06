from flask_wtf import FlaskForm
from wtforms import SubmitField

class ConfirmationForm(FlaskForm):
    submit = SubmitField('Do it')

class ConfirmationFormData(object):
    def __init__(self, title=None, action=None, backTo=None):
        self.title = title
        self.action = action
        self.backTo = backTo
