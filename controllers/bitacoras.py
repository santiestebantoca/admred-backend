# -*- coding: utf-8 -*-
__author__ = "jorge.santiesteban"


@request.restful()
def bitacoras():

    def GET(solicitudId):
        res = db(db.bitacora.solicitud == solicitudId).select()
        for row in res:
            row["by"] = db.vw_usuario(row.por)
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()