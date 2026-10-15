# -*- coding: utf-8 -*-
__author__ = "jorge.santiesteban"


@request.restful()
def tipos():

    @auth.requires_login()
    def GET(id=None, search=None, search_in=None, nombre=None, descripcion=None, uso=None, page=None, limit=None):
        db.tipo.uso = Field.Virtual(lambda row: db(db.solicitud.tipo == row.tipo.id).count())
        if id:
            tipo = db.tipo(id)
            tipo.modified_by = tipo.modified_by and db.vw_usuario(tipo.modified_by).name
            tipo.permisos = {
                "eliminar": not tipo.uso
            }
                        
            return response.json(tipo)
        
        from math import ceil
        
        fds = [
            db.tipo.id,
            db.tipo.nombre,
            db.tipo.descripcion,
        ]
        args = dict(distinct=True, orderby=~db.tipo.id)
        q = db.tipo.id > 0
        if nombre:
            q &= db.tipo.nombre.contains(nombre)
        if descripcion:
            q &= db.tipo.descripcion.contains(descripcion)
        if uso:
            if uso == "0":
                tipos_usados = db(db.solicitud.tipo != None)._select(db.solicitud.tipo, distinct=True)
                q &= ~db.tipo.id.belongs(tipos_usados)
            else:
                contador = db.solicitud.tipo.count()
                tipos_poco_usados = db(db.solicitud.tipo != None).select(
                    db.solicitud.tipo,
                    contador,
                    groupby=db.solicitud.tipo,
                    having=contador <= int(uso)
                )
                ids = [row['solicitud']['tipo'] for row in tipos_poco_usados]
                q &= db.tipo.id.belongs(ids)
        if search and search_in:
            if isinstance(search_in, str):
                search_in = [search_in]
                
            qor = None
            for field in search_in:
                if qor:
                    qor |= db.tipo[field].contains(search)
                else:
                    qor = db.tipo[field].contains(search)
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
        res = db.tipo.validate_and_insert(**vars)
        if (res.errors):
            response.status = 422
            return response.json(res.errors)
        return response.json(res)
    
    @auth.requires_membership('administrador')
    @Validate.auth_from_AR
    def PUT(id, **vars):
        res = db(db.tipo.id == id).validate_and_update(**vars)
        if (res.errors):
            response.status = 422
            return response.json(res.errors)
        return response.json(res)

    @auth.requires_membership('administrador')
    @Validate.auth_from_AR
    @Validate.tipo_not_referenced
    def DELETE(id):
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
                raise HTTP(403, 'Forbidden.', **headers)
            return fn(*k, **kw)

        return run
    
    @staticmethod
    def tipo_not_referenced(fn):
        def run(*k, **kw):
            id = k[0]
            if db(db.solicitud.tipo == id).count():
                raise HTTP(405, 'No permitido por una regla de integridad.', **headers)
            return fn(*k, **kw)

        return run