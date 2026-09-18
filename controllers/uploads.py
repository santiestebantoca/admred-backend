# -*- coding: utf-8 -*-
__author__ = 'jorge.santiesteban'


@request.restful()
def uploads():

    def GET(id=None, solicitud_id=None, tipo=1):
        if (id):
            return response.json(db.upload(id))
        elif solicitud_id:
            sq = db.adjunto.solicitud_id == solicitud_id
            sq &= db.adjunto.tipo == tipo
            q = db.upload.id.belongs(db(sq)._select(db.adjunto.upload_id))
            res = db(q).select()
            return response.json(res)

    def POST(*args, **vars):
        res = db.upload.validate_and_insert(**vars)
        if (res.errors):
            response.status = 422
            return response.json(res.errors)
        upload = db.upload(res.id)
        return response.json(upload)

    def DELETE(id, **vars):
        res = 0
        if db(db.adjunto.upload_id == id).isempty():
            res = db(db.upload.id == id).delete()
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()
