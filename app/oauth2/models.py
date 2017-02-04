from app.orm import LDAPOrm
from app.user.models import User
from flask_login import AnonymousUserMixin

class Grant(object):
    user_id =  None
    client_id =  None
    code = None
    redirect_uri = None
    expires = None
    _scopes = []

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def delete(self):
        return self

    @property
    def user(self):
        return User.get(self.user_id) or AnonymousUserMixin()

    @property
    def scopes(self):
        return self._scopes

class Token(object):
    client_id = None
    user_id = None
    token_type = "bearer"
    access_token = None
    refresh_token = None
    expires = None
    _scopes = []

    def delete(self):
        return self

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @property
    def scopes(self):
        return self._scopes


class Client(LDAPOrm):
    basedn_config_var = 'LDAP_OAUTH2_CLIENT_DN'
    objectClasses = ['oauthClientMetadata']
    keyMapping = ('oauthClientID', 'client_id')

    # human readable name, not required
    name = None
    description = None
    client_id = None
    _client_secret = None
    is_confidential = True
    _redirect_uris = []
    _default_scopes = []

    def __init__(self, client_id=None):
        import uuid
        self.client_id = client_id or str(uuid.uuid4())

    def __repr__(self):
        return '<OAuth2Client: {}>'.format(
                self.name or self.client_id)

    @staticmethod
    def create(name = None, redirect_uris=[], default_scopes=[], description=None):
        client = Client()
        client.name = name
        client.description = description
        client._redirect_uris = redirect_uris
        client._default_scopes = default_scopes
        client.save()
        return client

    @property
    def client_secret(self):
        import uuid
        # Generate a UUID if it isn't set yet.
        if not self._client_secret:
            self._client_secret = str(uuid.uuid4())
        return self._client_secret

    def _orm_mapping_load(self, entry):
        # FIXME: It would be nice if the ORM could somehow automagically
        # build up this mapping.
        self.client_id = entry.oauthClientID.value
        self._client_secret = entry.oauthClientSecret.value
        self.description = entry.description.value
        self._redirect_uris = entry.oauthRedirectURI.values
        self._default_scopes = entry.oauthScopeValue.values
        self.name = entry.oauthClientName.value

    def _orm_mapping_save(self, entry):
        # FIXME: It would be nice if the ORM could somehow automagically
        # build up this mapping.
        entry.oauthClientSecret = self.client_secret
        if self.name:
            entry.oauthClientName = self.name
        if self.description:
            entry.description = self.description
        if self._redirect_uris:
            entry.oauthRedirectURI = self._redirect_uris
        if self._default_scopes:
            entry.oauthScopeValue = self._default_scopes

    @property
    def client_type(self):
        if self.is_confidential:
            return 'confidential'
        return 'public'

    @property
    def redirect_uris(self):
        if self._redirect_uris:
            return self._redirect_uris
        return []

    @property
    def default_redirect_uri(self):
        return self.redirect_uris[0]

    @property
    def default_scopes(self):
        if self._default_scopes:
            return self._default_scopes
        return []
