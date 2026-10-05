# -*- coding: utf-8 -*-
__author__ = "jorge.santiesteban"


@request.restful()
def tipos():

    @auth.requires_login()
    def GET(search=None, search_in=None, nombre=None, descripcion=None, page=None, limit=None):
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
        if search:
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
        else:
            data = db(q).select(*fds, **args).as_list()
            return response.json({
                "data": data,
                "meta": { "total": len(data) }
            })

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()
