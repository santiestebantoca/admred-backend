# -*- coding: utf-8 -*-
__author__ = 'jorge.santiesteban'


@request.restful()
def tipo():
    def GET(id=None, **vars):
        if id:
            def deletable():
                q = db.solicitud.tipo == id
                return not db(q).count()
        
            def name(user):
                if not user:
                    return ''
                return '{first_name} {last_name}'.format(**user).strip()

            tipo = db(db.tipo.id == id).select().first()
            tipo['deletable'] = deletable()
            tipo['created_by'] = name(db.auth_user(tipo['created_by']))
            tipo['modified_by'] = name(db.auth_user(tipo['modified_by']))
            return response.json(tipo)
        else:            
            from gluon.storage import Storage
            from applications.admred.modules.db.admin import tipos
            return response.json(tipos(db, auth, Storage(vars)))
            # res = db.executesql(db(db.tipo)._select(orderby=~db.tipo.id))
            # return response.json(res)

    @auth.requires_membership('administrador')
    @Validate.auth_from_AR
    def POST(*args, **vars):
        res = db.tipo.validate_and_insert(**vars)
        return response.json(res)

    @auth.requires_membership('administrador')
    @Validate.auth_from_AR
    def PUT(id, **vars):
        res = db(db.tipo.id == id).validate_and_update(**vars)
        return response.json(res)

    @auth.requires_membership('administrador')
    @Validate.auth_from_AR
    @Validate.tipo_not_referenced
    def DELETE(id, **vars):
        res = db(db.tipo.id == id).delete()
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
    def auth_from_AR(fn):
        def run(*k, **kw):
            if not db.area(auth.user.area).rol_key == 'AR':
                raise HTTP(403, 'Forbidden.')
            return fn(*k, **kw)

        return run

    @staticmethod
    def tipo_not_referenced(fn):
        def run(*k, **kw):
            id = k[0]
            if db(db.solicitud.tipo == id).count():
                raise HTTP(
                    405, 'Una regla de integridad impidió realizar esta acción.')
            return fn(*k, **kw)

        return run
