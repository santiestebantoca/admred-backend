# -*- coding: utf-8 -*-
__author__ = 'jorge.santiesteban'


@request.restful()
def niveles():

    def GET(*args, **vars):
        res = db(db.nivel).select()
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()
