# -*- coding: utf-8 -*-
__author__ = 'jorge.santiesteban'


@request.restful()
def areas():
    def padre(vars):
        """
        Para formularios.
        Quita/pone un "área padre" según la lógica de negocio (esquema de niveles):
        - Niveles 1 y 4 son root, no tienen nivel padre, por tanto no tienen área padre.
        - El nivel 2 tiene al nivel 1 de padre, este último con una única área, VPOR.
        TODO: No tiene incorporada la lógica de los territorios, niveles 5 y 6.
        """
        
        if vars['nivel'] in ['1', '4']:
            vars['padre'] = None
        elif vars['nivel'] == '2':
            vars['padre'] = 1
        return vars

    def GET(id=None, search=None, search_in=None, nombre=None, padre=None, nivel=None, rol_key=None, page=None, limit=None):
        if id:
            area_en_solicitud = db.solicitud.origen == id
            area_en_solicitud |= db.solicitud.destino == id
            area_en_usuario = db.auth_user.area == id

            area = db.area(id)
            area.nivel = db.nivel(area.nivel)
            area.padre = db.area(area.padre)
            area.modified_by = area.modified_by and db.vw_usuario(area.modified_by).name
            area.permisos = {
                "eliminar": (
                    not bool(db(area_en_solicitud).count() + db(area_en_usuario).count())
                )
            }
            return response.json(area)
        
        from math import ceil
                
        fds = [
            db.areas.id,
            db.areas.nombre,
            db.areas.padre,
            db.areas.nivel,
            db.areas.rol_key,
        ]
        args = dict(distinct=True, orderby=~db.areas.id)
        q = db.areas.id > 0
        if nombre:
            q &= db.areas.nombre.contains(nombre)
        if nivel:
            q &= db.areas.nivel_id == nivel
        if padre:
            q &= db.areas.padre_id == padre
        if rol_key:
            q &= db.areas.rol_key != None
        if search:
            if isinstance(search_in, str):
                search_in = [search_in]
                
            qor = None
            for field in search_in:
                if qor:
                    qor |= db.areas[field].contains(search)
                else:
                    qor = db.areas[field].contains(search)
            q &= qor
        # return::
        if page and limit:
            _page = int(page)
            _limit = int(limit)
            args.update(limitby=((_page - 1) * _limit, _page * _limit))
            data = db(q).select(*fds, **args).as_list()
            total = db(q).count()
            total_pages = ceil(total / _limit)
            return response.json({
                "data": data,
                "meta": {
                    "total": total,
                    "page": _page,
                    "limit": _limit,
                    "totalPages": total_pages,
                    "hasNext": _page < total_pages,
                    "hasPrev": _page > 1
                }
            })
        data = db(q).select(*fds, **args).as_list()
        return response.json({
            "data": data,
            "meta": { "total": len(data) }
        }) 

    @auth.requires_membership('administrador')
    @Validate.auth_from_AR
    def POST(**vars):
        vars = padre(vars)
        res = db.area.validate_and_insert(**vars)
        if (res.errors):
            response.status = 422
            return response.json(res.errors)
        return response.json(res)

    @auth.requires_membership('administrador')
    @Validate.auth_from_AR
    def PUT(id, **vars):
        vars = padre(vars)
        res = db(db.area.id == id).validate_and_update(**vars)        
        if (res.errors):
            response.status = 422
            return response.json(res.errors)
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
