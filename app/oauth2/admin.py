"""
Administrative views for OAuth2.
"""
from flask import render_template, url_for, redirect, flash, request, current_app
from flask_wtf import FlaskForm
from wtforms import StringField, TextField, SubmitField, FieldList
from wtforms.validators import DataRequired

from .models import Client
from app.user import groups_required, login_required
from . import oauth2_blueprint


class AddClientForm(FlaskForm):
    name = StringField("name", validators=[DataRequired()])
    description = TextField("description")

    scopes = FieldList(StringField("Name"))
    scope = StringField("Scope")
    addScope = SubmitField("Add Scope")

    uris = FieldList(StringField("Name"))
    uri = StringField("URI")
    addURI = SubmitField("Add URI")

    submit = SubmitField("Submit")

    def remove_empty(self, field):
        temp = []
        while field.entries:
            entry = field.pop_entry()
            if entry.data:
                temp.append(entry.data)
        while temp:
            field.append_entry(temp.pop())


@oauth2_blueprint.route("/admin/oauth2/client")
@login_required
@groups_required("admin")
def clients():
    clients = Client.query()
    return render_template("/admin/oauth2/clients.html", clients=clients)


@oauth2_blueprint.route("/admin/oauth2/client/<string:client_id>/delete")
@login_required
@groups_required("admin")
def delete_client(client_id):
    client = Client.get(client_id)
    flash(
        "Deleted client: {uuid}({name})".format(
            uuid=client.client_id, name=client.name
        ),
        "info",
    )
    client.delete()
    return redirect(url_for("oauth2.clients"))


@oauth2_blueprint.route(
    "/admin/oauth2/client/<string:client_id>", methods=["GET", "POST"]
)
@login_required
@groups_required("admin")
def edit_client(client_id):
    client = Client.get(client_id)

    form = AddClientForm(
        name=client.name,
        description=client.description,
        scopes=client._default_scopes,
        uris=client._redirect_uris,
    )

    if form.validate_on_submit() and form.submit.data:
        form.remove_empty(form.scopes)
        form.remove_empty(form.uris)
        client.name = form.name.data
        client.description = form.description.data
        client._default_scopes = form.scopes.data
        client._redirect_uris = form.uris.data
        client.save()
        return redirect(url_for("oauth2.clients"))

    elif form.addScope.data:
        form.remove_empty(form.scopes)
        form.scopes.append_entry(form.scope.data)
        form.scope.data = ""
    elif form.addURI.data:
        form.remove_empty(form.uris)
        form.uris.append_entry(form.uri.data)
        form.uri.data = ""

    return render_template("/admin/oauth2/new.html", form=form)


@oauth2_blueprint.route("/admin/oauth2/client/new", methods=["GET", "POST"])
@login_required
@groups_required("admin")
def add_client():
    form = AddClientForm()
    if form.validate_on_submit() and form.submit.data:
        form.remove_empty(form.scopes)
        form.remove_empty(form.uris)
        client = Client.create(
            name=form.name.data,
            description=form.description.data,
            default_scopes=form.scopes.data,
            redirect_uris=form.uris.data,
        )
        flash(
            "Added client. Secret key is {secret_key}".format(
                secret_key=client.client_secret
            ),
            "info",
        )
        return redirect(url_for("oauth2.clients"))

    elif form.addScope.data:
        form.remove_empty(form.scopes)
        form.scopes.append_entry(form.scope.data)
    elif form.addURI.data:
        form.remove_empty(form.uris)
        form.uris.append_entry(form.uri.data)

    return render_template("/admin/oauth2/new.html", form=form)
