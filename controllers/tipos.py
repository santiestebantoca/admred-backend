# -*- coding: utf-8 -*-
__author__ = "jorge.santiesteban"


@request.restful()
def tipos():

    @auth.requires_login()
    def GET(search=None):
        q = db.tipo.id > 0
        if search:
            q &= db.tipo.nombre.contains(search)
        res = db(q).select()
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()
