import os
import ldap3
import logging
from flask_ldap3_login import LDAP3LoginManager

basedir = os.path.abspath(os.path.dirname(__file__))

log = logging.getLogger(__name__)


def _mock_connection(
    self, bind_user=None, bind_password=None, contextualise=True, **kwargs
):

    authentication = ldap3.ANONYMOUS
    if bind_user:
        authentication = getattr(
            ldap3, self.config.get("LDAP_BIND_AUTHENTICATION_TYPE")
        )

    mock_server = ldap3.Server.from_definition(
        "mocked_server",
        os.path.join(basedir, "info.json"),
        os.path.join(basedir, "schema.json"),
    )

    log.debug(
        "Opening mocked connection"
        "with bind user '{0}'".format(bind_user or "Anonymous")
    )

    connection = ldap3.Connection(
        server=mock_server,
        read_only=self.config.get("LDAP_READONLY"),
        user=bind_user,
        password=bind_password,
        client_strategy=ldap3.MOCK_SYNC,
        authentication=authentication,
        check_names=True,
        raise_exceptions=True,
        **kwargs
    )
    connection.strategy.add_entry(
        bind_user, {"userPassword": bind_password, "sn": "mock_bind", "revision": 0}
    )
    connection.strategy.entries_from_json(os.path.join(basedir, "entries.json"))

    if contextualise:
        self._contextualise_connection(connection)
    return connection
