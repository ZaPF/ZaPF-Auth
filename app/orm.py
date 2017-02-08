from flask import current_app

class LDAPOrm(object):
    @classmethod
    def _objectdef(cls):
        """
        Helper function to construct the objectdef at runtime.

        Subclasses MUST specify the objectClasses used in the
        `objectClasses` class attribute.
        """
        from ldap3 import ObjectDef
        conn = current_app.ldap3_login_manager.connection
        return ObjectDef(cls.objectClasses, conn)

    @classmethod
    def _basedn(cls):
        """
        Helper function to construct the base DN at runtime.

        Subclasses MUST specify the configuration variable that holds
        the base DN in the `basedn_config_var` class attribute.
        """
        # FIXME: If basedn_config_var is not specified, allow basedn to be
        # specified explicitely using cls.basedn.
        return current_app.ldap3_login_manager.compiled_sub_dn(
            current_app.config[cls.basedn_config_var])

    @classmethod
    def _get_read_cursor(cls, qry=None):
        """
        Get a generic read cursor for this class.
        """
        from ldap3 import Reader
        from ldap3.core.exceptions import LDAPNoSuchObjectResult

        conn = current_app.ldap3_login_manager.connection

        r = Reader(conn,
                cls._objectdef(),
                cls._basedn(),
                qry)
        try:
            r.search()
        except LDAPNoSuchObjectResult:
            raise LookupError("No such object: {qry}".format(qry = qry))
            return None

        return r

    @classmethod
    def from_dn(cls, dn):
        from ldap3 import Reader
        from ldap3.core.exceptions import LDAPNoSuchObjectResult
        conn = current_app.ldap3_login_manager.connection

        r = Reader(conn,
                cls._objectdef(),
                cls._basedn())
        try:
            entry = r.search_object(dn)
        except LDAPNoSuchObjectResult:
            raise LookupError("No such object: {qry}".format(qry = qry))
            return None

        item = cls()
        item._orm_mapping_load(entry)
        return item

    @classmethod
    def query(cls, qry=None):
        r = cls._get_read_cursor(qry)
        def populate_from(entry):
            item = cls()
            item._orm_mapping_load(entry)
            return item
        return [populate_from(entry) for entry in r]

    @classmethod
    def get(cls, key):
        key_attr, _ = cls.keyMapping
        try:
            return cls.query('{key_attr}: {key}'.format(
                key_attr = key_attr,
                key = key))[0]
        except IndexError:
            return None

    @property
    def key(self):
        '''
        Get the default key (rdn attribute) used by this class.

        Subclasses MUST specify the mapping of their key attribute to the rdn
        attribute in the `keyMapping` class attribute in the form `(rdn, attr)`.
        '''
        _, key = self.keyMapping
        return getattr(self, key)

    @property
    def _default_read_cursor(self):
        """
        return a read cursor containing just this instance.
        """
        attr, key = self.keyMapping
        return self._get_read_cursor(
                '{key_attr}: {key}'.format(key_attr = attr, key = self.key)
                )

    @property
    def _default_write_cursor(self):
        """
        return a write cursor containing just this instance.
        """
        from ldap3 import Writer
        return Writer.from_cursor(self._default_read_cursor)


    def load(self):
        """
        Load the object from the LDAP
        """
        self._orm_mapping_load(self._default_read_cursor[0])

    def save(self):
        """
        Save the object to LDAP
        """
        writer = self._default_write_cursor
        try:
            entry = writer[0]
        except:
            attr, _ = self.keyMapping
            entry = writer.new(
                    '{key_attr}={key},{basedn}'.format(
                        key_attr = attr,
                        key = self.key,
                        basedn = self._basedn())
                )

        self._orm_mapping_save(entry)
        writer.commit()

    def delete(self):
        """
        Delete the object
        """
        writer = self._default_write_cursor
        try:
            entry = writer[0]
        except:
            # doesn't exist anyways
            return
        entry.entry_delete()
        writer.commit()
