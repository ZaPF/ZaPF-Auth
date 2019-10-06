"""
Sanity checks for the environment of this app.
All functions starting with check_ are executed automatically.
"""
from flask import current_app
from ldap3 import ObjectDef, Reader, Writer
from ldap3.core.exceptions import LDAPNoSuchObjectResult


def _check_dn_exists(dn, object_def, fix=True):
    """
    Check if a certain DN exists, otherwise create it.

    The only MUST attribute of the object_def must be specified
    in the DN.
    """
    conn = current_app.ldap3_login_manager.connection
    r = Reader(conn, object_def, current_app.config["LDAP_BASE_DN"])
    try:
        base = r.search_object(dn)
    except LDAPNoSuchObjectResult:
        current_app.logger.error("DN does not exist: %s" % dn)
        if fix:
            current_app.logger.info("Attempting to fix...")
            w = Writer.from_cursor(r)
            base = w.new(dn)
            base.description = "Automagically added by quasisentient sanity checks"
            w.commit()
