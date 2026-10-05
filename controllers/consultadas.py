# -*- coding: utf-8 -*-
__author__ = "jorge.santiesteban"

# API diseñada para reportes.
# Devuelve las areas de destino de solicitudes de un *area en *un período
@request.restful()
def consultadas():

    @auth.requires_login()
    def GET(desde, hasta, origen_id=None, origen_nivel=None):
        """
        Puedo preguntar por las consultadas de un origen o de
        un conjunto de origenes definidos por su nivel
        OJO: solo se devuelven destinos de solicitudes *originales*
        """
                
        fds = [
            db.solicitudes.destino,
            db.solicitudes.destino_id,
        ]
        args = dict(distinct=True, orderby=db.solicitudes.destino)
        q = db.solicitudes.solicitado_en >= desde
        q &= db.solicitudes.solicitado_en <= hasta + ' 23:59:59'
        q &= db.solicitudes.padre_id == None
        if origen_id:
            q &= db.solicitudes.origen_id == origen_id
        elif origen_nivel:
            _lista = origen_nivel if isinstance(origen_nivel, list) else [origen_nivel]
            q &= db.solicitudes.origen_nivel.belongs(_lista)
        res = db(q).select(*fds, **args)
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()
