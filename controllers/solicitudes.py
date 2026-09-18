# -*- coding: utf-8 -*-
__author__ = "jorge.santiesteban"


@request.restful()
def solicitudes():
    @auth.requires_login()  # it uses auth.user
    def GET(id=None, **vars):
        if id:
            fields = [
                db.solicitud.id,
                db.solicitud.codigo,
                db.solicitud.objetivo,
                db.solicitud.origen,
                db.solicitud.destino,
                db.solicitud.tipo,
                db.solicitud.estado,
                db.solicitud.remitente,
                db.solicitud.supervisor,
                db.solicitud.tramitador,
                db.solicitud.padre,
                db.solicitud.solicitado_en,
                db.solicitud.tramitador_en,
                db.solicitud.respuesta_en,
                db.solicitud.terminado_en,
                db.solicitud.cumplir_en,
                db.solicitud.observaciones,
                db.solicitud.evaluacion,
            ]
            fields2 = [
                db.solicitudes.id,
                db.solicitudes.codigo,
                db.solicitudes.origen,
                db.solicitudes.destino,
                db.solicitudes.estado,
                db.solicitudes.origen_id,
                db.solicitudes.destino_id,
            ]
            res = db(db.solicitud.id == id).select(*fields).first()
            # Validate.get(solicitud=res)
            res["padre"] = db(db.solicitudes.id == res.padre).select(*fields2).first()
            res["hijos"] = db(db.solicitudes.padre_id == id).select(*fields2).as_list()
            res["remitente"] = db.vw_usuario(res.remitente)
            res["supervisor"] = db.vw_usuario(res.supervisor)
            res["tramitador"] = db.vw_usuario(res.tramitador)
            res["origen"] = db.area(res.origen)
            res["destino"] = db.area(res.destino)
            res["tipo"] = db.tipo(res.tipo)
            res["estado"] = db.estado(res.estado)
            res["cant_nota"] = db(db.nota.solicitud == id).count()
            q = db.adjuntos.solicitud_id == id
            res["adjuntos_solicitud"] = (
                db(q & (db.adjuntos.tipo == 1)).select().as_list()
            )
            res["adjuntos_respuesta"] = (
                db(q & (db.adjuntos.tipo == 2)).select().as_list()
            )
            # Usuario: roles y permisos contextuales
            esSupervisorAreaDemandada = auth.has_membership("supervisor") and (res["destino"]["id"] == auth.user.area)
            esSupervisorSolicitud = res["supervisor"]["id"] == auth.user_id if res["supervisor"] else False
            esTramitadorSolicitud = res["tramitador"]["id"] == auth.user_id if res["tramitador"] else False
            esRemitenteSolicitud = res["remitente"]["id"] == auth.user_id if res["remitente"] else False
            res["permisos"] = {
                "asignar": (
                    res["estado"]["id"] < 3  # solicitada, en proceso (asignada)
                    and esSupervisorAreaDemandada  # puede asignar o reasignar
                ),
                "reenviar": ((
                    res["estado"]["id"] == 2  # en proceso
                    and esTramitadorSolicitud  # puede reenviar solicitudes a su cargo
                )
                or (
                    res["estado"]["id"] == 1  # solicitada (no asignada)
                    and esSupervisorAreaDemandada  # puede reenviar (convirtiendose en tramitador) 
                )),
                "responder": (
                    res["estado"]["id"] == 2  # en proceso
                    and esTramitadorSolicitud  # puede responder solicitudes a su cargo
                ),
                "aprobar": (
                    res["estado"]["id"] == 3  # en evaluacion (respondida)
                    and esSupervisorSolicitud  # puede aprobar solicitudes a su cargo
                ),
                "evaluar": (
                    res["estado"]["id"] == 4  # terminada
                    and not res["evaluacion"]  # no evaluada
                    and esRemitenteSolicitud  # puede evaluar sus solicitudes
                    # TODO: acotar en tiempo (plazo para evaluar)
                ),
                "comentar": (
                    res["estado"]["id"] < 4  # no terminada
                    and (  # puede escribir notas estando asociado la solicitud
                        esSupervisorSolicitud
                        or esTramitadorSolicitud
                        or esRemitenteSolicitud
                    )
                )
            }            

            return response.json(res)
        else:
            from gluon.storage import Storage
            from applications.admred.modules.db.solicitudes import solicitudes

            return response.json(solicitudes(db, auth, Storage(vars)))

    @auth.requires_login()
    def PUT(id, **vars):  # asignar, responder, aprobar and evaluar
        solicitud_id = int(id)
        adjuntos = vars.pop("adjuntos", [])
        q = db.solicitud.id == solicitud_id
        if "tramitador" in vars:
            Validate.assign(
                tramitador=db.auth_user(int(vars["tramitador"])),
                solicitud=db.solicitud(solicitud_id),
            )
            response.callback = "assign"
            vars["supervisor"] = auth.user_id
            vars["tramitador_en"] = request.now
            vars["estado"] = 2
            res = db(q).validate_and_update(**vars)
            if (res.errors):
                response.status = 422
                return response.json(res.errors)
            return response.json(res.updated)
        if "observaciones" in vars:
            from applications.admred.modules.db.solicitudes import add_adjuntos

            Validate.reply(solicitud=db.solicitud(solicitud_id))
            response.callback = "reply"
            vars["respuesta_en"] = request.now
            vars["estado"] = 3
            res = db(q).validate_and_update(**vars)
            if (res.errors):
                response.status = 422
                return response.json(res.errors)
            elif res.updated:
                add_adjuntos(db, solicitud_id, adjuntos, 2)
            return response.json(res)
        if "aprobado" in vars:
            Validate.approve(solicitud=db.solicitud(solicitud_id))
            # response.callback = 'approve'
            if vars["aprobado"] == "1":  # '1' or '0'
                response.callback = "approve"
                res = db(q).validate_and_update(estado=4, terminado_en=request.now)
            else:
                response.callback = "disapprove"
                res = db(q).validate_and_update(estado=2)
            if (res.errors):
                response.status = 422
                return response.json(res.errors)
            return response.json(res)
        if "evaluacion" in vars:
            Validate.rate(solicitud=db.solicitud(solicitud_id))
            response.callback = "rate"
            res = db(q).validate_and_update(**vars)
            if (res.errors):
                response.status = 422
                return response.json(res.errors)
            return response.json(res)

    @auth.requires_login()
    def POST(*args, **vars):
        """
        user: destino, objetivo, adjuntos, tipo, cumplir_en,
              (if forward) padre
        system: codigo, solicitado_en, origen, remitente, estado,
                (if forward) [Kevin rule] supervisor, tramitador, tramitador_en, estado
        """
        from applications.admred.modules.db.solicitudes import codigo, add_adjuntos

        if vars.get("cumplir_en", None):
            from datetime import datetime

            vars["cumplir_en"] = datetime.strptime(vars["cumplir_en"], "%Y-%m-%d")

        adjuntos = vars.pop("adjuntos", [])

        vars["codigo"] = codigo(db)
        vars["solicitado_en"] = request.now
        vars["origen"] = auth.user.area
        vars["remitente"] = auth.user_id
        vars["estado"] = 1
        res = db.solicitud.validate_and_insert(**vars)
        if (res.errors):
            response.status = 422
            return response.json(res.errors)
        add_adjuntos(db, res.id, adjuntos, 1)
        if "padre" in vars:
            response.callback = False  # this action is invisible to callbacks
            q = db.solicitud.id == vars["padre"]
            q &= db.solicitud.estado == 1
            db(q).update(
                supervisor=auth.user_id,
                tramitador=auth.user_id,
                tramitador_en=request.now,
                estado=2,
            )
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


class Validate:
    """
    Validate authorization for methods, based on user relationship with current 'solicitud'
    and integrity of request variables
    """

    @staticmethod
    def get(solicitud):
        """
        User has to be from source or destination area.
        """
        # if '/report' in request.env.http_referer \
        if db.area(auth.user.area).rol_key == "AR":
            return
        if auth.user.area not in [solicitud.origen, solicitud.destino]:
            raise HTTP(403, "Forbidden")

    @staticmethod
    def assign(tramitador, solicitud):
        """
        User has to be 'supervisor'.
        User and 'tramitador', they both have to be from the destination area.
        """
        if not (
            auth.has_membership("supervisor")
            and auth.user.area == solicitud.destino
            and tramitador.area == solicitud.destino
        ):
            raise HTTP(403, "Forbidden")

    @staticmethod
    def reply(solicitud):
        """
        User has to be the 'tramitador' of this 'solicitud'
        """
        if not (auth.user_id == solicitud.tramitador):
            raise HTTP(403, "Forbidden")

    @staticmethod
    def approve(solicitud):
        """
        User has to be the 'supervisor' of this 'solicitud'
        """
        if not (auth.user_id == solicitud.supervisor):
            raise HTTP(403, "Forbidden")

    @staticmethod
    def rate(solicitud):
        """
        User has to be the 'remitente' of this 'solicitud'
        """
        if not (auth.user_id == solicitud.remitente):
            raise HTTP(403, "Forbidden")
