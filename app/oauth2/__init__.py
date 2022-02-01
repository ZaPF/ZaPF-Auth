from flask import Blueprint, current_app
from flask_caching import Cache
from .models import Client, AuthorizationCode, Token
from flask_login import current_user
from datetime import datetime, timedelta
from authlib.integrations.flask_oauth2 import AuthorizationServer
from authlib.oauth2.rfc6749 import grants

oauth2_blueprint = Blueprint("oauth2", __name__, template_folder="templates/")

from . import views


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_basic", "client_secret_post"]

    def save_authorization_code(self, code, request):
        client = request.client
        auth_code = AuthorizationCode(
            code=code,
            client_id=client.client_id,
            redirect_uri=request.redirect_uri,
            scope=request.scope,
            user_id=request.user.id,
        )
        current_app.cache.set(
            "grant/{client_id}/{code}".format(client_id=client.client_id, code=code),
            grant,
        )

        return auth_code

    def query_authorization_code(self, code, client):
        item = current_app.cache.get(
            "grant/{client_id}/{code}".format(client_id=client.client_id, code=code)
        )
        if item and not item.is_expired():
            return item

    def delete_authorization_code(self, authorization_code):
        current_app.cache.delete(
            "grant/{client_id}/{code}".format(
                client_id=authorization_code.client_id, code=authorization_code.code
            )
        )

    def authenticate_user(self, authorization_code):
        return authorization_code.user


class RefreshTokenGrant(grants.RefreshTokenGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_basic", "client_secret_post"]

    def authenticate_refresh_token(self, refresh_token):
        item = current_app.cache.get(
            "token/refresh/{token}".format(token=refresh_token)
        )

        # FIXME: define is_refresh_token_valid by yourself
        # usually, you should check if refresh token is expired and revoked
        if item:  # and item.is_refresh_token_valid():
            return item

    def authenticate_user(self, credential):
        return credential.user

    def revoke_old_credential(self, credential):
        current_app.cache.delete("token/refresh/{code}".format(code=credential.code))


def init_app(app):
    app.cache = Cache(app)

    # Set up sanity checks.
    from . import sanity

    getattr(app, "sanity_check_modules", []).append(sanity)

    server = AuthorizationServer()
    server.init_app(app, query_client=load_client, save_token=save_token)

    # register it to grant endpoint
    server.register_grant(grants.ImplicitGrant)
    server.register_grant(AuthorizationCodeGrant)
    server.register_grant(RefreshTokenGrant)

    app.auth_server = server
    return app


def load_client(client_id):
    return Client.get(client_id)


def load_token(access_token=None, refresh_token=None):
    if access_token:
        return current_app.cache.get("token/access/{token}".format(token=access_token))


def save_token(token, request):
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
    current_app.cache.set("token/access/{tok}".format(tok=token["access_token"]), tok)
    current_app.cache.set("token/refresh/{tok}".format(tok=token["refresh_token"]), tok)

    return tok
