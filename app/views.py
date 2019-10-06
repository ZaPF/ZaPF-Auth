from flask import render_template, url_for, request
from flask_wtf import FlaskForm
from wtforms import SubmitField
from functools import wraps, partial

try:
    from urllib.parse import urlparse, urljoin
except ImportError:
    from urlparse import urlparse, urljoin


def is_safe_url(target):
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


def get_redirect_target():
    for target in request.args.get("next"), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return target


class ConfirmationForm(FlaskForm):
    submit = SubmitField("Do it")


def confirm(
    func=None,
    title="Are you sure?",
    action="Yes",
    prompt=None,
    text="There is probably no turning back after this...",
    back=None,
):
    """
    Render a confirmation form before executing this view.
    """
    if func is None:
        return partial(confirm, title=title, action=action, back=back)

    @wraps(func)
    def f(*args, **kwargs):
        form = ConfirmationForm()
        if form.validate_on_submit():
            return func(*args, **kwargs)
        return render_template(
            "confirm.html",
            form=form,
            data={
                "title": title,
                "action": action,
                "back": back,
                "prompt": prompt,
                "text": text,
            },
        )

    return f
