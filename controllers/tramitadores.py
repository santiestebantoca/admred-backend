# -*- coding: utf-8 -*-
__author__ = "jorge.santiesteban"


@request.restful()
def tramitadores():

    @auth.requires_login()
    def GET(*args, **vars):
        q = db.vw_usuario.area_id == auth.user.area
        q &= (db.vw_usuario.registration_key == None) | (db.vw_usuario.registration_key == "")
        return response.json(db(q).select(db.vw_usuario.id, db.vw_usuario.name))

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()
