from flask import render_template, url_for
from flask_wtf import FlaskForm
from wtforms import SubmitField
from functools import wraps, partial

class ConfirmationForm(FlaskForm):
    submit = SubmitField('Do it')

def confirm(func=None,
        title="Are you sure?",
        action=None,
        prompt=None,
        text="There is probably no turning back after this...",
        back=None
        ):
    """
    Render a confirmation form before executing this view.
    """
    if func is None:
        return partial(confirm,
            title=title, action=action, back=back)
    @wraps(func)
    def f(*args, **kwargs):
        form = ConfirmationForm()
        if form.validate_on_submit():
            return func(*args, **kwargs)
        return render_template('confirm.html',
            form=form,
            data={
                'title': title,
                'action': action,
                'back': back,
                'prompt': prompt
                })
    return f
