from flask import current_app
from ldap3 import ObjectDef
from ..sanity import _check_dn_exists

def check_userbase_exists(fix=True):
    """
    Check the User base DN exists, and if not, create it.
    """
    conn = current_app.ldap3_login_manager.connection
    ou = ObjectDef('organizationalunit', conn)
    userbase = "%s,%s"%(current_app.config['LDAP_USER_DN'],
            current_app.config['LDAP_BASE_DN'])
    _check_dn_exists(userbase, ou, fix)

def check_group_base_exists(fix=True):
    """
    Check the Group base DN exists, and if not, create it.
    """
    conn = current_app.ldap3_login_manager.connection
    ou = ObjectDef('organizationalunit', conn)
    groupbase = "%s,%s"%(current_app.config['LDAP_GROUP_DN'],
            current_app.config['LDAP_BASE_DN'])
    _check_dn_exists(groupbase, ou, fix)

def check_default_group_exists(fix=True):
    """
    Check whether the all users group exists
    """
    from .models import Group
    default_group_names = current_app.config['DEFAULT_GROUPS']
    for group_name in default_group_names:
        g = Group.get(group_name)
        print(g)