# -*- coding: utf-8 -*-
__author__ = "jorge.santiesteban"


@request.restful()
def notas():
    def GET(solicitudId):
        def get_usuario(id):
            return db(db.vw_usuario.id == id).select(db.vw_usuario.name).first()
        
        fds = [
            db.nota.id,
            db.nota.fecha,
            db.nota.texto,
            db.nota.evento,
            db.nota.supervisor,
            db.nota.tramitador,            
        ]
        args = dict(orderby=db.nota.id)
        
        res = db(db.nota.solicitud == solicitudId).select(*fds, **args)
        for row in res:
            if row.tramitador:
                row["autor"] = get_usuario(row.tramitador)
                row["como"] = "tramitador"
            elif row.supervisor:
                row["autor"] = get_usuario(row.supervisor)
                row["como"] = "supervisor"
            else:
                remitente_id = db.solicitud(solicitudId).remitente
                row["autor"] = get_usuario(remitente_id)
                row["como"] = "remitente"
            del row["tramitador"]
            del row["supervisor"]
        return response.json(res)

    @auth.requires_login()
    def POST(*args, **vars):
        # new [nov 16, 2021] by Mabel, note writer can be 'remitente' also.
        # The solution in this case was to leave empty tramitador and supervisor fields
        # It implies changes in:
        # 1. controller validation.
        # 2. Item view to show action to user
        # 3. Note view to let remitente write down a note, and to show note correctly.
        # -------------------------
        # new [feb 15, 2022] by Aldo: 'supervisor' can also create a note

        solicitud = db.solicitud(int(vars["solicitud"]))
        Validate.nota(solicitud=solicitud)
        if solicitud.tramitador == auth.user_id:
            vars["tramitador"] = auth.user_id
        elif solicitud.supervisor == auth.user_id:
            vars["supervisor"] = auth.user_id

        res = db.nota.validate_and_insert(**vars)
        if (res.errors):
            response.status = 422
            return response.json(res.errors)
        # nota = db.nota(res.id)
        return response.json(res.id)
    
    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


class Validate:
    """
    Validate authorization for methods, based on user relationship with current 'solicitud'
    and integrity of request variables
    """

    @staticmethod
    def nota(solicitud):
        """
        User has to be the 'tramitador' of this 'solicitud'
        new [nov 16, 2021] by Mabel: 'remitente' can also create a note
        new [feb 15, 2022] by Aldo: 'supervisor' can also create a note
        """
        if not (
            auth.user_id
            in [solicitud.tramitador, solicitud.remitente, solicitud.supervisor]
        ):
            raise HTTP(403, "Forbidden")
