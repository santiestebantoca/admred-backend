# -*- coding: utf-8 -*-
__author__ = 'jorge.santiesteban'


@request.restful()
def attachment():

    def DELETE(id, **vars):
        row = db.adjunto(id)
        upload_id = row.upload_id if row else False
        res = db(db.adjunto.id == id).delete()
        if upload_id and db(db.adjunto.upload_id == upload_id).isempty(): 
            db(db.upload.id == upload_id).delete()
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()
