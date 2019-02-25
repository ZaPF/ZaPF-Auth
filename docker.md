# Instructions for setting up with docker

This application ships with a docker-compose file. The values within it are
set for debugging, not for production use.

## OpenLDAP

An OpenLDAP server is provided using the [osixia/openldap] docker image.

**Do not use this setup for persistent data, as no persistence is configured!**

### Bind DNs

**Make sure to change the passwords for the following default accounts:**

The admin DN for the main tree at `dc=zapf,dc=in` is `cn=admin,dc=zapf,dc=in`
with the password specified in `LDAP_ADMIN_PASSWORD` environment variable.
This defaults to `admin`.

The admin DN for the config tree at `cn=config` is `cn=admin,cn=config` with
the password specified in `LDAP_CONFIG_PASSWORD`.
This defaults to `config`.

The bind user for the auth application is `uid=zapf-auth,dc=zapf,dc=in`.
The password is specified in the
[`docker/bootstrap_openldap/ldif/bootstrap.ldif`] file.
This defaults to `test`.
When changing this password, hash it using `slappasswd`.

### Tree Structure

The OU entries for `ou=people,dc=zapf,dc=in`, `ou=groups,dc=zapf,dc=in` and
`ou=oauth,dc=zapf,dc=in` are created on startup.

## App configuration

Create an app configuration in `docker/auth.conf`.

For basic functionality, the following variables MUST be set:

```python
DEBUG=True
SECRET_KEY = 'plschangeme'
BOOTSTRAP_SERVE_LOCAL = True

# LDAP
LDAP_HOST = 'openldap'
LDAP_PORT = 389
LDAP_BASE_DN = 'dc=zapf,dc=in'
LDAP_BIND_USER_DN = 'uid=zapf-auth,dc=zapf,dc=in'
LDAP_BIND_USER_PASSWORD = 'test'
import ldap3
PASSWORD_HASHING_FUNC = ldap3.HASHED_SALTED_SHA

# Recaptcha needs to be configured for signup to work.
# The following keys are test keys that always confirm
RECAPTCHA_PUBLIC_KEY="6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"
RECAPTCHA_PRIVATE_KEY="6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"

# Mail needs to be configured for signup to work
MAIL_SERVER='smtp.example.org'
MAIL_PORT=465
MAIL_USE_TLS = False
MAIL_USE_SSL=True
MAIL_USERNAME='zapf-auth-sender'
MAIL_PASSWORD='CHANGEME'

# To prevent open redirects in OAuth logout
LOGOUT_ALLOWED_NEXT= [
  'http://url/of/oauth_client/oauth/loggedout',
]
```

[osixia/openldap]: https://github.com/osixia/docker-openldap
[`docker/bootstrap_openldap/ldif/bootstrap.ldif`]: docker/bootstrap_openldap/ldif/bootstrap.ldif
