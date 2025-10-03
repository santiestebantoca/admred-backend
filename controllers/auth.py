# -*- coding: utf-8 -*-
__author__ = 'jorge.santiesteban'


@request.restful()
def login():
    def GET():
        return response.json(user())

    def POST(*args, **vars):
        if auth.user:
            auth.log_event(auth.messages['logout_log'], auth.user)
            auth.logout_bare()
        res = login_bare(vars['username'], vars['password'])
        res.update(user=user())
        return response.json(res)

    def DELETE():
        if auth.user:
            auth.log_event(auth.messages['logout_log'], auth.user)
            auth.logout_bare()
        return response.json(user())

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


def user():
    if auth.user:
        area = db.area(auth.user.area)
        return dict(
            id=auth.user_id,
            name='{first_name} {last_name}'.format(**auth.user).strip(),
            username=auth.user.username,
            email=auth.user.email,
            movil=auth.user.movil,
            fijo=auth.user.fijo,
            admin=auth.has_membership('administrador'),
            supervisor=auth.has_membership('supervisor'),
            user_groups=auth.user_groups,
            is_impersonating=auth.is_impersonating(),
            can_impersonate=can_impersonate(),
            AR=area.rol_key == 'AR',
            DAR=area.rol_key == 'DAR',
            area=auth.user.area,
            area_nombre=area.nombre
        )
    return auth.user


def login_bare(username, password):
    """
    A version of Auth.login_bare from gluon.tools customized for this app
    In this version, user must be in database to login
    Differences:
    Returns {user, errors}
    Applies registration_key validation to any login method
    Skip password validation for local request (dev environment)
    Skip registration_key validation for user 'jorge.santiesteban'
    """
    def check_psw(username, password, user):
        if request.is_local:
            return True
        for login_method in auth.settings.login_methods:
            if login_method != auth and login_method(username, password):
                return True
        psw = db.auth_user.password.validate(password)[0]
        if psw == user.password:
            return True
        return False

    def check_registration_key(user):
        return (user.registration_key is None
                or not user.registration_key.strip()
                or username == 'jorge.santiesteban')

    def login_user(user):
        auth.login_user(user)
        auth.log_event(auth.messages['login_log'], user)
        return dict(user=user)

    def credential_error(username, password):
        message = 'Login failed with credentials %(username)s; %(password)s'
        args = dict(username=username, password=password)
        auth.log_event(message % args)
        return dict(error='Credenciales no válidas.')

    def registration_key_error():
        message = 'Login failed due to registration_key'
        auth.log_event(message)
        return dict(error='Usuario restringido.')

    user = db.auth_user(username=username)
    if user and check_psw(username, password, user):
        if check_registration_key(user):
            return login_user(user)
        else:
            return registration_key_error()
    return credential_error(username, password)


@request.restful()
def impersonate():
    def POST(*args, **vars):
        if can_impersonate():
            auth.impersonate(request.args(0) or '0')
        else:
            auth.impersonate('0')
        return response.json(user())

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


@request.restful()
def users():
    def GET(*args, **vars):
        if 'name' in vars:
            q = db.usuario.name.contains(vars['name'])
            res = db(q).select(limitby=(0, 10))
        else:
            res = db(db.usuario).select()
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


def can_impersonate():
    # Allowed now: Jorge Lino, Ignacio, Julito and Aldo
    return auth.user_id in [1, 2, 235, 4]
