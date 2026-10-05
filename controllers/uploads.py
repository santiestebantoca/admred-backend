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

    def DELETE(id):
        """
        Cuando se está creando una solicitud o una respuesta, el archivo que se carga
        se puede eliminar. En ese caso es seguro eliminarlo: no está compartido con 
        otra solicitud y no es un adjunto aún (no se ha creado la relación).
        Casos parecidos de interacción del usuario:
        Cuando se está reenviando una solicitud se puede eliminar el adjunto heredado;
        en este caso no se elimina el archivo cargado, solo que no se asocia a la solicitud.
        Cuando se está reeditando una respuesta se puede eliminar un adjunto heredado;
        en este caso sí se elimina el archivo cargado (se meneja en el UPDATE de la solicitud).
        """
        
        res = db(db.upload.id == id).delete()
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()
