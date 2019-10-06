from flask import current_app
from ldap3 import ObjectDef
from ..sanity import _check_dn_exists


def check_userbase_exists(fix=True):
    """
    Check the User base DN exists, and if not, create it.
    """
    conn = current_app.ldap3_login_manager.connection
    ou = ObjectDef("organizationalunit", conn)
    userbase = "%s,%s" % (
        current_app.config["LDAP_USER_DN"],
        current_app.config["LDAP_BASE_DN"],
    )
    _check_dn_exists(userbase, ou, fix)


def check_group_base_exists(fix=True):
    """
    Check the Group base DN exists, and if not, create it.
    """
    conn = current_app.ldap3_login_manager.connection
    ou = ObjectDef("organizationalunit", conn)
    groupbase = "%s,%s" % (
        current_app.config["LDAP_GROUP_DN"],
        current_app.config["LDAP_BASE_DN"],
    )
    _check_dn_exists(groupbase, ou, fix)
