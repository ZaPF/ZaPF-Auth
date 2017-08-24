import json
import binascii
import os
import time
from flask_login import UserMixin, AnonymousUserMixin
from flask import current_app

from app.orm import LDAPOrm

from .helpers import send_password_reset_mail, send_confirm_mail

class AnonymousUser(AnonymousUserMixin):
    @property
    def groups(self):
        return []

    def is_in_group(self, group):
        return False

class User(UserMixin, LDAPOrm):
    # This doesn't really work either, so we have to overload _basedn
    # basedn_config_var = 'LDAP_OAUTH2_CLIENT_DN'
    @classmethod
    def _basedn(cls):
        return current_app.ldap3_login_manager.full_user_search_dn

    objectClasses = ['inetOrgPerson','simpleSecurityObject']
    # FIXME: 'uid' should really be current_app.config['LDAP_USER_LOGIN_ATTR']
    # here. Unfortunately, current_app doesn't really work here, so the ORM
    # has to be adapted to deal with this.
    keyMapping = ('uid', 'username')

    def __init__(self, username=None, dn=None, firstName=None, surname=None, mail=None):
        self.dn = dn
        self.username = username
        self.firstName = firstName
        self.surname = surname
        self._full_name = None
        self._password = None
        self.mail = mail
        self.reset_password = None
        self.confirm_mail = None

    # FIXME: This could be simplified to just create a User object, populate it,
    @staticmethod
    def create(username, givenName, surname, password, mail = None):
        """
        Create a user and save it.
        """
        user = User(username = username, firstName = givenName, surname = surname, mail = mail)
        user.password = password
        user.save()
        return user

    def delete(self):
        """
        Remove a user.
        """
        for group in self.groups:
            group.leave(self)
            if len(group.members) == 0:
                group.delete();
            else:
                group.save()
        super().delete()

    def update(self, givenName, surname, mail = None, password = None):
        """
        Update the user information.
        """
        self.firstName = givenName
        self.surname = surname
        self._full_name = "{firstName} {surname}".format(
            firstName = self.firstName,
            surname = self.surname
        )
        if mail:
            self.mail = mail
        if password:
            self.password = password
        self.save()

    @property
    def password(self):
        """
        Return if the password has been changed
        """
        if self._password:
            return True
        return False

    @password.setter
    def password(self, value):
        """
        Set the password
        """
        from ldap3.utils.hashed import hashed
        self._password = hashed(current_app.config['PASSWORD_HASHING_FUNC'], value)

    @property
    def groups(self):
        return [
                Group.from_dn(membership['dn'])
                for membership in current_app.ldap3_login_manager.get_user_groups(
                    self.dn,
                    _connection = current_app.ldap3_login_manager.connection
                    )
                ]

    @property
    def is_admin(self):
        return self.is_in_group('admin')

    def is_in_group(self, group_name):
        return group_name in [group.group_name for group in self.groups]

    def _orm_mapping_load(self, entry):
        # FIXME: It would be nice if the ORM could somehow automagically
        # build up this mapping.
        self.dn = entry.entry_dn
        (self.username,) = getattr(entry, current_app.config['LDAP_USER_LOGIN_ATTR'])[0],
        self.firstName = entry.givenName.value
        self.surname = entry.sn.value
        self._full_name = entry.cn.value
        self.mail = entry.mail.value
        self.data = entry.description.value

    def _orm_mapping_save(self, entry):
        # FIXME: It would be nice if the ORM could somehow automagically
        # build up this mapping.
        entry.sn = self.surname
        entry.cn = self.full_name
        entry.givenName = self.firstName
        entry.description = self.data
        if self.password:
            entry.userPassword = self._password
        if self.mail:
            entry.mail = self.mail

    def __repr__(self):
        return "<User: {full_name}>".format(full_name = self.full_name)

    def get_id(self):
        return self.username

    @property
    def full_name(self):
        return self._full_name or "{firstName} {surname}".format(
                firstName = self.firstName,
                surname = self.surname
                )

    @property
    def data(self):
        return json.dumps({'confirm_mail': self.confirm_mail,
                           'reset_password': self.reset_password})

    @data.setter
    def data(self, value):
        try:
            jsonData = json.loads(value)
        except:
            self.confirm_mail = None
            self.reset_password = None
            return
        self.confirm_mail = jsonData['confirm_mail']
        self.reset_password = jsonData['reset_password']

    def reset_password_start(self):
        self.reset_password = (binascii.hexlify(os.urandom(20)).decode('ascii'), int(time.time()) + 24 * 60 * 60)
        send_password_reset_mail(self)
        self.save()

    def confirm_mail_start(self):
        self.confirm_mail = {'confirmed': False,
          'token': binascii.hexlify(os.urandom(20)).decode('ascii'), 'valid_till': int(time.time()) + 24 * 60 * 60}
        send_confirm_mail(self)
        self.save()

class Group(LDAPOrm):
    # This doesn't really work either, so we have to overload _basedn
    # basedn_config_var = 'LDAP_OAUTH2_GROUP_DN'
    @classmethod
    def _basedn(cls):
        return current_app.ldap3_login_manager.full_group_search_dn

    objectClasses = ['groupOfNames']
    # FIXME: 'cn' should really be current_app.config['LDAP_GROUP_LOGIN_ATTR']
    # here. Unfortunately, current_app doesn't really work here, so the ORM
    # has to be adapted to deal with this.
    keyMapping = ('cn', 'group_name')

    def __init__(self, name = None, description=None, members=None):
        self._group_name = name
        self.description = description
        self._members = members

    @property
    def group_name(self):
        # Read-only.
        return self._group_name

    @property
    def members(self):
        return [User.from_dn(dn) for dn in self._members]

    @members.setter
    def members(self, users):
        self._members = [user.dn for user in users]

    def join(self, user):
        """
        Add a user to the group.
        """
        self._members.append(user.dn)

    def leave(self, user):
        """
        Remove a user from the group.
        """
        self._members = [ dn for dn in self._members if dn != user.dn ]

    def _orm_mapping_load(self, entry):
        # FIXME: It would be nice if the ORM could somehow automagically
        # build up this mapping.
        self.dn = entry.entry_dn
        self._group_name = entry.cn.value
        self.description = entry.description.value
        self._members = entry.member.values

    def _orm_mapping_save(self, entry):
        # FIXME: It would be nice if the ORM could somehow automagically
        # build up this mapping.
        if self._members:
            entry.member = self._members
        if self.description:
            entry.description = self._group_name

    def __repr__(self):
        return '<Group {name}>'.format(name=self.group_name)
