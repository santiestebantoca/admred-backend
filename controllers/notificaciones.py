# -*- coding: utf-8 -*-
__author__ = "jorge.santiesteban"


@request.restful()
def notificaciones():
    """
    cantidad de solicitudes pendientes (recibidas / enviadas)
    supervisor: todas / especialista: si remitente o tramitador
    """
    from applications.admred.modules.db.solicitudes import (
        solicitudes_recibidas,
        solicitudes_enviadas,
    )

    @auth.requires_login()  # it uses auth.user
    def GET():
        def lista_de_recibidas_por_asignar():
            # TODO: or tramitador_rk == 'blocked'
            if auth.has_membership("supervisor"):
                q = db.solicitudes.estado_id == 1
                q &= db.solicitudes.destino_id == auth.user.area
                return db(q).select(db.solicitudes.id, db.solicitudes.codigo)
            else:
                return []

        def lista_de_recibidas_por_responder():
            q = db.solicitudes.estado_id == 2
            q &= db.solicitudes.tramitador_id == auth.user_id
            return db(q).select(db.solicitudes.id, db.solicitudes.codigo)

        def lista_de_recibidas_por_aprobar():
            q = db.solicitudes.estado_id == 3
            q &= db.solicitudes.supervisor_id == auth.user_id
            return db(q).select(db.solicitudes.id, db.solicitudes.codigo)

        def cantidad_de_recibidas_pendientes():
            q = solicitudes_recibidas(auth, db)
            q &= db.solicitudes.estado_id != 4
            return db(q).count()

        def cantidad_de_enviadas_pendientes():
            q = solicitudes_enviadas(auth, db)
            q &= db.solicitudes.estado_id != 4
            return db(q).count()
        
        res = {
            "pendientes": {
                "recibidas": {
                    "total": cantidad_de_recibidas_pendientes(),
                    "por_asignar": lista_de_recibidas_por_asignar(),
                    "por_responder": lista_de_recibidas_por_responder(),
                    "por_aprobar": lista_de_recibidas_por_aprobar(),
                },
                "enviadas": {
                    "total": cantidad_de_enviadas_pendientes(),
                }
            }
        }
        
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()
