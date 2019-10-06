from flask import Blueprint
from flask_oauthlib.provider import OAuth2Provider
from flask_cache import Cache
from werkzeug.contrib.cache import SimpleCache
from .models import Client, Grant, Token
from flask_login import current_user
from datetime import datetime, timedelta

oauth2_blueprint = Blueprint("oauth2", __name__, template_folder="templates/")
oauth = OAuth2Provider()

# FIXME: Use a memcached in production.
cache = SimpleCache()

from . import views


def init_app(app):
    oauth.init_app(app)
    app.oauth2_provider = oauth

    # Set up sanity checks.
    from . import sanity

    getattr(app, "sanity_check_modules", []).append(sanity)

    return app


@oauth.clientgetter
def load_client(client_id):
    return Client.get(client_id)


@oauth.grantgetter
def load_grant(client_id, code):
    return cache.get("grant/{client_id}/{code}".format(client_id=client_id, code=code))


@oauth.grantsetter
def save_grant(client_id, code, request, *args, **kwargs):
    # decide the expires time yourself
    expires = datetime.utcnow() + timedelta(seconds=3600)
    grant = Grant(
        client_id=client_id,
        code=code["code"],
        redirect_uri=request.redirect_uri,
        _scopes=request.scopes,
        user_id=current_user.get_id(),
        expires=expires,
    )
    cache.set(
        "grant/{client_id}/{code}".format(client_id=client_id, code=code["code"]), grant
    )

    return grant


@oauth.tokengetter
def load_token(access_token=None, refresh_token=None):
    if access_token:
        return cache.get("token/access/{token}".format(token=access_token))
    elif refresh_token:
        return cache.get("token/refresh/{token}".format(token=refresh_token))


@oauth.tokensetter
def save_token(token, request, *args, **kwargs):
    expires_in = token.get("expires_in")
    expires = datetime.utcnow() + timedelta(seconds=expires_in)

    tok = Token(
        access_token=token["access_token"],
        refresh_token=token["refresh_token"],
        token_type=token["token_type"],
        _scopes=token["scope"].split(" "),
        expires=expires,
        client_id=request.client.client_id,
        user_id=request.user.get_id(),
    )
    cache.set("token/access/{tok}".format(tok=token["access_token"]), tok)
    cache.set("token/refresh/{tok}".format(tok=token["refresh_token"]), tok)

    return tok
