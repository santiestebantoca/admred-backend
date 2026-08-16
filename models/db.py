# -*- coding: utf-8 -*-

from gluon.contrib.login_methods.ldap_auth import ldap_auth
from gluon.contrib.appconfig import AppConfig
from gluon.tools import Auth

request.requires_https()

configuration = AppConfig(reload=False)

db = DAL(
    configuration.get('db.uri'),
    pool_size=configuration.get('db.pool_size'),
    migrate_enabled=configuration.get('db.migrate'),
    migrate=False,
    check_reserved=['all'],
    lazy_tables=True  # Big perfomence boost offered by web2py
)

session.connect(request, response, db, masterapp=None)

# host names must be a list of allowed host names (glob syntax allowed)
# auth = Auth(db, host_names=configuration.get('host.names'))
auth = Auth(db, secure=False)

# -------------------------------------------------------------------------
# create all tables needed by auth, maybe add a list of extra fields
# -------------------------------------------------------------------------
auth.settings.extra_fields['auth_user'] = [
    Field('area', 'reference area', required=True),
    Field('fijo'),
    Field('movil'),
    auth.signature
]
auth.define_tables(username=True)

# -------------------------------------------------------------------------
# configure email
# -------------------------------------------------------------------------
mail = auth.settings.mailer
mail.settings.server = configuration.get('smtp.server')
mail.settings.sender = configuration.get('smtp.sender')
mail.settings.login = configuration.get('smtp.login')
mail.settings.tls = configuration.get('smtp.tls') or False
mail.settings.ssl = configuration.get('smtp.ssl') or False

# -------------------------------------------------------------------------
# configure auth policy
# -------------------------------------------------------------------------
auth.settings.registration_requires_verification = False
auth.settings.registration_requires_approval = False
auth.settings.reset_password_requires_verification = True
auth.settings.remember_me_form = False
auth.settings.create_user_groups = False
auth.settings.actions_disabled = [
    'request_reset_password',
    'retrieve_username'
]
auth.settings.expiration = 30 * 60  # 30 min

# lds.etecsa.cu
auth.settings.login_methods.append(
    ldap_auth(
        server='172.29.30.200',
        base_dn='ou=etecsa.cu,ou=People,dc=etecsa,dc=cu',
        secure=True,
        self_signed_certificate=True,
        # tls=True,
        logging_level='debug')
)

# after defining tables, uncomment below to enable auditing
# auth.enable_record_versioning(db)

tabla = db.define_table

T.force('es')

"""
As long as possible, we use validate_and_update/insert rather than update or SQLFORM
* validate_and_update returns an Object with 'updated' and 'errors' which is a standard on client side
* validate_and_insert returns an Object with 'id' and 'errors' which is a standard on client side
"""

# CORS Policy (RESTFUL API )
"""
Using X-Requested-With header, implies using OPTIONS for any method (GET, POST, ...)
We force X-Requested-With: XMLHttpRequest in client request,
that is the way web2py recognizes the ajax request.
"""

# frontURL = configuration.get('front.url', request.env.http_origin)
frontURL = request.env.http_origin

response.headers['Access-Control-Allow-Origin'] = frontURL
response.headers['Access-Control-Allow-Credentials'] = 'true'

headers = {
    'Access-Control-Allow-Origin': frontURL,
    'Access-Control-Allow-Credentials': 'true',
    'Access-Control-Allow-Headers': 'X-Requested-With, Content-Type',
    'Access-Control-Allow-Methods': 'OPTIONS, GET, HEAD, POST, PUT, DELETE, TRACE, CONNECT',
    # 24hrs  // cache for Allow Header & Allow Methods
    'Access-Control-Max-Age': 86400,
}

# response.headers.update(**headers)

if request.ajax:

    def resp401():
        raise HTTP(401, **headers)


    def resp403():
        raise HTTP(403, **headers)

    auth.settings.on_failed_authentication = resp401
    auth.settings.on_failed_authorization = resp403
