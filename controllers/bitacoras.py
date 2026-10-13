# -*- coding: utf-8 -*-
__author__ = "jorge.santiesteban"


@request.restful()
def bitacoras():

    def GET(solicitudId):
        db.bitacora.by = Field.Virtual(lambda row: db.vw_usuario(row.bitacora.por))
        res = db(db.bitacora.solicitud == solicitudId).select()
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()