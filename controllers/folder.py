# -*- coding: utf-8 -*-
__author__ = "jorge.santiesteban"


# Statics for input controls


@request.restful()
def destinos():

    @auth.requires_login()
    def GET(*args, **vars):
        area = db.area(auth.user.area)
        if area.rol_key in ["AR", "DAR"]:  # Administración
            q = db.area
        elif area.nivel == 1:  # 1 Vicepresidencia
            q = db.area.id == 2
        elif area.nivel == 2:  # 2 Direcciones y Grupos
            q = db.area.nivel == 2
            q |= db.area.padre == area.id
        elif area.nivel == 3:  # 3 Departamentos
            q = db.area.id == area.padre
        elif area.nivel >= 4:  # 4 Áreas externas
            q = db.area.id == 2
        return response.json(db(q).select(db.area.id, db.area.nombre))

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


@request.restful()
def tramitadores():

    @auth.requires_login()
    def GET(*args, **vars):
        q = db.usuario.area_id == auth.user.area
        q &= (db.usuario.registration_key == None) | (db.usuario.registration_key == "")
        return response.json(db(q).select(db.usuario.id, db.usuario.name))

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


@request.restful()
def tipos():

    @auth.requires_login()
    def GET(*args, **vars):
        return response.json(db(db.tipo).select())

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


# Client component custom data interface


@request.restful()
def pending():
    """
    cantidad de solicitudes pendientes (recibidas / enviadas)
    supervisor: todas / especialista: si remitente o tramitador
    """
    from applications.admred.modules.db.solicitudes import (
        solicitudes_recibidas,
        solicitudes_enviadas,
    )

    @auth.requires_login()  # it uses auth.user
    def GET(*args, **vars):
        def lista_por_asignar():
            # TODO: or tramitador_rk == 'blocked'
            if auth.has_membership("supervisor"):
                q = db.solicitudes.estado_id == 1
                q &= db.solicitudes.destino_id == auth.user.area
                sql = db(q)._select(db.solicitudes.id, db.solicitudes.codigo)
                return db.executesql(sql)
            else:
                return []

        def lista_por_responder():
            q = db.solicitudes.estado_id == 2
            q &= db.solicitudes.tramitador_id == auth.user_id
            sql = db(q)._select(db.solicitudes.id, db.solicitudes.codigo)
            return db.executesql(sql)

        def lista_por_aprobar():
            q = db.solicitudes.estado_id == 3
            q &= db.solicitudes.supervisor_id == auth.user_id
            sql = db(q)._select(db.solicitudes.id, db.solicitudes.codigo)
            return db.executesql(sql)

        q = db.solicitudes.estado_id != 4
        recibidas = q & solicitudes_recibidas(auth, db)
        enviadas = q & solicitudes_enviadas(auth, db)
        return response.json(
            dict(
                incoming=db(recibidas).count(),
                outgoing=db(enviadas).count(),
                assign=lista_por_asignar(),
                reply=lista_por_responder(),
                approve=lista_por_aprobar(),
            )
        )

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


# Dynamic data interfaces
@request.restful()
def bitacora():

    def GET(*args, **vars):
        res = db(db.bitacora.solicitud == vars["solicitud"]).select()
        for row in res:
            row["by"] = db.usuario(row.por).username
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


@request.restful()
def solicitud():
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
            res["remitente"] = db.usuario(res.remitente)
            res["supervisor"] = db.usuario(res.supervisor)
            res["tramitador"] = db.usuario(res.tramitador)
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

            return response.json(res)
        else:
            from gluon.storage import Storage
            from applications.admred.modules.db.solicitudes import solicitudes

            return response.json(solicitudes(db, auth, Storage(vars)))

    @auth.requires_login()
    def PUT(id, **vars):  # assign, reply, approve and evaluate
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
            return response.json(res)
        if "observaciones" in vars:
            from applications.admred.modules.db.solicitudes import add_adjuntos

            Validate.reply(solicitud=db.solicitud(solicitud_id))
            response.callback = "reply"
            vars["respuesta_en"] = request.now
            vars["estado"] = 3
            res = db(q).validate_and_update(**vars)
            if res.updated:
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
            return response.json(res)
        if "evaluacion" in vars:
            Validate.rate(solicitud=db.solicitud(solicitud_id))
            response.callback = "rate"
            res = db(q).validate_and_update(**vars)
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
        if res.id:
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


@request.restful()
def nota():
    def GET(*args, **vars):
        res = db(db.nota.solicitud == vars["solicitud"]).select(orderby=db.nota.id)
        for row in res:
            row["supervisor"] = db.usuario(row.supervisor)
            row["tramitador"] = db.usuario(row.tramitador)
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
