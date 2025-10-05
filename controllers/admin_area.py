# -*- coding: utf-8 -*-
__author__ = 'jorge.santiesteban'


# Statics

@request.restful()
def niveles():

    def GET(*args, **vars):
        return response.json(db(db.nivel).select())

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


@request.restful()
def padres():

    def GET(*args, **vars):
        from gluon.storage import Storage
        from applications.admred.modules.db.admin import padres
        return response.json(padres(db, auth, Storage(vars)))

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()

@request.restful()
def area():
    def padre(vars):
        if vars['nivel'] in ['1', '4']:
            vars['padre'] = None
        elif vars['nivel'] == '2':
            vars['padre'] = 1  # It is VPOR
        return vars

    def GET(id=None, **vars):
        if id:
            def deletable():
                q = db.solicitud.origen == id
                q |= db.solicitud.destino == id
                in_solicitud = db(q).count()
                q = db.auth_user.area == id
                in_auth_user = db(q).count()
                return not (in_solicitud + in_auth_user)
        
            def name(user):
                if not user:
                    return ''
                return '{first_name} {last_name}'.format(**user).strip()

            area = db(db.area.id == id).select().first()
            area['nivel'] = db.nivel(area.nivel)
            area['padre'] = db.area(area.padre)
            area['deletable'] = deletable()
            area['created_by'] = name(db.auth_user(area['created_by']))
            area['modified_by'] = name(db.auth_user(area['modified_by']))
            return response.json(area)
        else:
            from gluon.storage import Storage
            from applications.admred.modules.db.admin import areas
            return response.json(areas(db, auth, Storage(vars)))

    @auth.requires_membership('administrador')
    @Validate.auth_from_AR
    def POST(*args, **vars):
        vars = padre(vars)
        res = db.area.validate_and_insert(**vars)
        return response.json(res)

    @auth.requires_membership('administrador')
    @Validate.auth_from_AR
    def PUT(id, **vars):
        vars = padre(vars)
        res = db(db.area.id == id).validate_and_update(**vars)
        return response.json(res)

    @auth.requires_membership('administrador')
    @Validate.auth_from_AR
    @Validate.area_not_referenced
    def DELETE(id, **vars):
        res = db(db.area.id == id).delete()
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
    def area_not_referenced(fn):
        def run(*k, **kw):
            id = k[0]
            c = db(db.area.padre == id).count()
            c += db(db.auth_user.area == id).count()
            c += db((db.solicitud.origen == id) |
                    (db.solicitud.destino == id)).count()
            if c:
                raise HTTP(
                    405, 'Una regla de integridad impidió realizar esta acción.')
            return fn(*k, **kw)

        return run


"""
Antes:
1. Verificar que las areas de provision esten bien asociadas a su padre correspondiente.
2. Marcar las 15 (excluyendo La Habana) areas de provision con una X.
3. Ir al URL: /admred/admin_area/integracion_areas
4. Verificar que las areas de provision hayan sido eliminadas y los usuarios y solicitudes reasignadas.
"""
def integracion_areas():
    areas_provision = db(db.area.rol_key == 'X').select()
    for area in areas_provision:
        db(db.auth_user.area == area.id).update(area=area.padre)
        db(db.solicitud.origen == area.id).update(origen=area.padre)
        db(db.solicitud.destino == area.id).update(destino=area.padre)
        db(db.area.id == area.id).delete()

    return "Integración de áreas de provisión a áreas de administración finalizada."