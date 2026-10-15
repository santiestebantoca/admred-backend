# -*- coding: utf-8 -*-
__author__ = "jorge.santiesteban"


@request.restful()
def auth_groups():

    def GET():
        res = db(db.auth_group.id > 0).select()
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()
