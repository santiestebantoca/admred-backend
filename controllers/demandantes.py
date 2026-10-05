# -*- coding: utf-8 -*-
__author__ = "jorge.santiesteban"

# API diseñada para reportes.
# Devuelve las areas que han originado solicitudes a un *area en *un período
@request.restful()
def demandantes():

    @auth.requires_login()
    def GET(desde, hasta, destino_id=None, origen_nivel=None):
        """
        Puedo preguntar por los demandantes de un destino o los 
        demandantes que pertenecen a uno o varios niveles...
        """
        
        fds = [
            db.solicitudes.origen,
            db.solicitudes.origen_id,
        ]
        args = dict(distinct=True, orderby=db.solicitudes.origen)
        q = db.solicitudes.solicitado_en >= desde
        q &= db.solicitudes.solicitado_en <= hasta + ' 23:59:59'
        if destino_id:
            q &= db.solicitudes.destino_id == destino_id
        if origen_nivel:
            _lista = origen_nivel if isinstance(origen_nivel, list) else [origen_nivel]
            q &= db.solicitudes.origen_nivel.belongs(_lista)
        res = db(q).select(*fds, **args)
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()
