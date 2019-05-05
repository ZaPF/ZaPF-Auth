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

def check_default_user_exists(fix=True):
    from .models import User
    default_uid = current_app.config['DEFAULT_USER_UID']

    if User.get(default_uid):
            return

    if fix:
        User.create(
            default_uid,
            current_app.config['DEFAULT_USER_GIVENNAME'],
            current_app.config['DEFAULT_USER_SN'],
            current_app.config['DEFAULT_USER_PASSWORD'],
            current_app.config['DEFAULT_USER_MAIL'],
        )

def check_default_group_exists(fix=True):
    """
    Check whether the all users group exists
    """
    from .models import User, Group
    check_default_user_exists(fix)
    default_group_names = current_app.config['DEFAULT_GROUPS']
    default_uid = current_app.config['DEFAULT_USER_UID']
    default_user = User.get(default_uid)
    for group_name in default_group_names:
        default_group = Group.get(group_name)
        if default_group:
            continue

        if fix:
            default_group = Group(name=group_name)
            default_group.members = [default_user]
            default_group.save()