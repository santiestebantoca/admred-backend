# -*- coding: utf-8 -*-
__author__ = 'jorge.santiesteban'


# Statics

@request.restful()
def authgroup():

    def GET(*args, **vars):
        return response.json(db(db.auth_group).select())

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


@request.restful()
def areas():

    def GET(*args, **vars):
        return response.json(db(db.area).select())

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()

# //


@request.restful()
def user():

    @auth.requires_login()  # it uses auth.user
    def GET(id=None, **vars):
        if id:
            def deletable():
                q = db.solicitud.tramitador == id
                q |= db.solicitud.remitente == id
                q |= db.solicitud.supervisor == id
                return not db(q).count()

            def membership():
                res = db(db.auth_membership.user_id == id)._select(
                    db.auth_membership.group_id)
                return db(db.auth_group.id.belongs(res)).select().as_list()
        
            def name(user):
                if not user:
                    return ''
                return '{first_name} {last_name}'.format(**user).strip()

            fields = [db.auth_user.id,
                      db.auth_user.first_name,
                      db.auth_user.last_name,
                      db.auth_user.username,
                      db.auth_user.email,
                      db.auth_user.movil,
                      db.auth_user.fijo,
                      db.auth_user.registration_key,
                      db.auth_user.area,
                      db.auth_user.created_by,
                      db.auth_user.modified_by,
                      db.auth_user.created_on,
                      db.auth_user.modified_on]
            user = db(db.auth_user.id == id).select(*fields).first()
            user['name'] = name(user)
            user['area'] = db.area(user.area)
            user['membership'] = membership()
            user['deletable'] = deletable()
            user['created_by'] = name(db.auth_user(user['created_by']))
            user['modified_by'] = name(db.auth_user(user['modified_by']))
            return response.json(user)
        else:
            from gluon.storage import Storage
            from applications.admred.modules.db.admin import users
            return response.json(users(db, auth, Storage(vars)))

    @auth.requires_membership('administrador')
    def POST(*args, **vars):
        db.auth_user.password.requires = None  # disable validator
        if db.area(auth.user.area).rol_key != 'AR':  # admin no AR
            vars['area'] = auth.user.area
        res = db.auth_user.validate_and_insert(**vars)
        return response.json(res)

    @auth.requires_membership('administrador')
    @Validate.user_in_scope
    def PUT(id, **vars):
        current_values = db(db.auth_user.id == id).select(
            db.auth_user.email,
            db.auth_user.username
        ).first()

        # `email` and `username`, fails to update with same values,
        # it is due to fields requires NOT_IN_DB
        if ('email' in vars) and vars['email'] == current_values.email:
            del vars['email']
        if ('username' in vars) and vars['username'] == current_values.username:
            del vars['username']
        # admin from area not AR, is not allow to change `area`
        if db.area(auth.user.area).rol_key != 'AR':
            del vars['area']

        res = db(db.auth_user.id == id).validate_and_update(**vars)
        return response.json(res)

    @auth.requires_membership('administrador')
    @Validate.user_in_scope
    @Validate.user_not_referenced
    def DELETE(id, **vars):
        res = db(db.auth_user.id == id).delete()
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


@request.restful()
def membership():

    def GET(user_id, **vars):
        res = db(db.auth_membership.user_id == user_id).select()
        return response.json([r.group_id for r in res])

    @auth.requires_membership('administrador')
    def POST(*args, **vars):
        group_id = int(vars['group_id'])
        user_id = int(vars['user_id'])
        res = auth.add_membership(group_id, user_id)
        return response.json(dict(id=res, errors={}))

    @auth.requires_membership('administrador')
    def DELETE(*args, **vars):
        group_id = int(vars['group_id'])
        user_id = int(vars['user_id'])
        res = auth.del_membership(group_id, user_id)
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


class Validate:
    """
    Validate authorization for methods, based on user administration scope (user area role_key)
    and integrity of request variables
    """

    @staticmethod
    def user_not_referenced(fn):
        """
        User is not referenced by any "solicitud".
        """
        def run(*k, **kw):
            id = k[0]
            q = db.solicitud.tramitador == id
            q |= db.solicitud.remitente == id
            q |= db.solicitud.supervisor == id
            if db(q).count():
                raise HTTP(
                    405, 'Una regla de integridad impidió realizar esta acción.')
            return fn(*k, **kw)

        return run

    @staticmethod
    def user_in_scope(fn):
        """
        Administrador is from the "AR" area or shares the same area as the updated user.
        """
        def run(*k, **kw):
            id = k[0]
            c = db.area(auth.user.area).rol_key == 'AR'
            # c |= db.auth_user(id).area == auth.user.area
            # New to consider scoped admins to action over no area users
            c |= db.auth_user(id).area in [auth.user.area, None]
            if not c:
                raise HTTP(403, 'Forbidden.')
            return fn(*k, **kw)

        return run
