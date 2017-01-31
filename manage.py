#!/usr/bin/env python3
from flask_script import Manager
from app import create_app, check_sanity

app = create_app()
manager = Manager(app)

@manager.command
def sanity():
    """
    Run a number of sanity checks and attempt to automatically
    fix any inconsistencies.
    """
    check_sanity()

def _getpass():
    """
    Simple getpass wrapper that asks for a password twice.
    """
    from getpass import getpass
    password = getpass('New password: ')
    if (getpass('Repeat password: ') != password):
        raise Exception("Paswords were not equal")
    return password

def _query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        choice = input(question + prompt).lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            print("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")

@manager.command
def passwd(username, password=None):
    """
    Change a user's password
    """
    from app.user.models import User
    try:
        user = User.get(username)
    except LookupError:
        app.logger.fatal("User does not exist: %d", dn)
    else:
        user.password = password or _getpass()
        user.save()
        return user

@manager.command
def create_user(uid, givenName, sn, mail=None, password=None):
    """
    Create a user
    """
    from app.user.models import User
    return User.create(uid, givenName, sn, password or _getpass(), mail)

@manager.command
def delete_user(uid):
    """
    Delete a user
    """
    if _query_yes_no('Are you sure to delete user "{}"?'.format(uid), None):
        from app.user.models import User
        return User.get(uid).delete()
    else:
        print('Aborting...')

@manager.command
def groups():
    """
    List groups
    """
    from app.user.models import Group
    groups = Group.query()
    for group in groups:
        print('{0.group_name}: {0.description}'.format(group))

@manager.command
def members(group_id):
    from app.user.models import Group
    group = Group.get(group_id)
    for member in group.members:
        print('{0.username}: {0.full_name}'.format(member))

@manager.command
def join(username, group_name):
    """
    Add a user to a group
    """
    from app.user.models import User, Group
    from ldap3.core.exceptions import LDAPAttributeOrValueExistsResult
    try:
        group = Group.get(group_name)
        if not group:
            raise AttributeError("group does not exist")
        group.join(User.get(username))
        group.save()
    except LDAPAttributeOrValueExistsResult:
        print("User already in group")
    except AttributeError:
        print("User or Group does not exist")

@manager.command
def remove(username, group_name):
    """
    Remove a user from a group
    """
    from app.user.models import User, Group
    group = Group.get(group_name)
    if not group:
        raise AttributeError("group does not exist")
    group.leave(User.get(username))
    group.save()

@manager.command
def delgroup(group_name):
    """
    Delete a group
    """
    from app.user.models import Group
    Group.get(group_name).delete()

@manager.command
def newgroup(group_name):
    """
    Create a group
    """
    from app.user.models import User, Group
    g = Group(name = group_name)
    g.description = input('Enter a description of the group '
                          '(or leave blank for none): ') or None
    print('Enter a list of initial user names to be added to the group, one on '
          'each line, ending with an empty line: ')
    users = []
    while True:
        username = input('> ')
        if not username:
            break

        user = User.get(username)
        if not user:
            print('Could not find user: {}'.format(username))
            continue

        if user in users:
            print('Heard you the first time.')
            continue

        users.append(user)

    g.members = users
    g.save()

if __name__ == "__main__":
    if app.config['MOCKSERVER'] == True:
        from unittest import mock
        from flask_ldap3_login import LDAP3LoginManager
        from test.MockLDAP import _mock_connection
        with mock.patch.object(LDAP3LoginManager, '_make_connection', new=_mock_connection):
            app.logger.info("using mocked ldap")
            manager.run()
    else:
        manager.run()
