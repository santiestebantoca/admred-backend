# -*- coding: utf-8 -*-
__author__ = 'jorge.santiesteban'


@request.restful()
def pendientes_del_area():

    @auth.requires_login()
    def GET(*args, **vars):
        _list = []
        if auth.has_membership('supervisor'):
            q = db.solicitud.origen == auth.user.area
        else:
            q = db.solicitud.remitente == auth.user_id
        q &= db.solicitud.estado != 4
        for s in db(q).select(db.solicitud.id, orderby=db.solicitud.id):
            _list.append(traversal(s.id))
        return response.json(_list)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


@request.restful()
def indicadores_del_usuario():

    @auth.requires_login()
    def GET(*args, **vars):
        user_id = vars['user_id']
        month = vars['month']
        year = vars['year']

        # supervisor | tramitador
        q1 = db.solicitud.tramitador == user_id
        q1 |= db.solicitud.supervisor == user_id

        # ended on selection
        q2 = db.solicitud.terminado_en.year() == year
        q2 &= db.solicitud.terminado_en.month() == month
        q = q1 & q2

        # not ended (pending)
        q3 = db.solicitud.terminado_en == None
        q3 &= db.solicitud.solicitado_en.year() <= year
        q3 &= db.solicitud.solicitado_en.month() <= month
        q = q1 & (q2 | q3)

        rows = db(q).select(
            db.solicitud.id,
            db.solicitud.codigo,
            db.solicitud.estado,
            db.solicitud.supervisor,
            db.solicitud.tramitador,
            db.solicitud.solicitado_en,
            db.solicitud.tramitador_en,
            db.solicitud.respuesta_en,
            db.solicitud.terminado_en,
            orderby=db.solicitud.id
        )

        # update with first child created time and last child terminated time
        for row in rows:
            row.update(tramitador=row.tramitador == int(user_id))
            row.update(supervisor=row.supervisor == int(user_id))
            if row.tramitador:
                children = db(db.solicitud.padre == row.id).select(
                    db.solicitud.solicitado_en, db.solicitud.terminado_en)
                if children:
                    children = children.sort(lambda _: _.solicitado_en)
                    row.update(hijo_en=children.first().solicitado_en)
                    # you can't sort datetime and None values
                    children = children.find(lambda _: _.terminado_en != None)
                    if children:
                        children = children.sort(lambda _: _.terminado_en)
                        row.update(
                            hijo_terminado_en=children.last().terminado_en)

        return response.json(rows)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


@request.restful()
def buscar_codigo():

    @auth.requires_login()
    def GET(*args, **vars):
        fds = [
            db.solicitud.id,
            db.solicitud.codigo,
            db.solicitud.objetivo,
            db.solicitud.solicitado_en,
            db.solicitud.terminado_en,
            db.solicitud.origen,
            db.solicitud.destino,
        ]
        q = db.solicitud.codigo.contains(vars['codigo'])
        res = db(q).select(*fds, limitby=(0, 10))
        for row in res:
            row["origen"] = db.area(row.origen).nombre
            row["destino"] = db.area(row.destino).nombre
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


@request.restful()
def solicitudes_externas():

    @Validate.auth_from_AR
    def GET(desde, hasta, origen=None, estado=None, codigo=None, objetivo=None):
        """
        origen: id de área externa a la VPOR
        """
        
        fds = [
            db.solicitudes.id,
            db.solicitudes.codigo,
            db.solicitudes.objetivo,
            db.solicitudes.origen,
            db.solicitudes.destino,
            db.solicitudes.solicitado_en,
            db.solicitudes.terminado_en,
            db.solicitudes.estado,
        ]
        args = dict(orderby=db.solicitudes.id)
        q = db.solicitudes.solicitado_en >= desde
        q &= db.solicitudes.solicitado_en <= hasta + ' 23:59:59'
        if origen:
            q &= db.solicitudes.origen_id == origen
        else:
            area_ids = db(db.area.nivel.belongs(NIVELES_AREAS_EXTERNAS))._select(db.area.id)
            q &= db.solicitudes.origen_id.belongs(area_ids)
        q &= db.solicitudes.destino_id == DIRECCION_ADMINISTRACION_ID
        if estado:
            _lista = estado if isinstance(estado, list) else [estado]
            q &= db.solicitudes.estado_id.belongs(_lista)
        if codigo:
            q &= db.solicitudes.codigo.contains(codigo)
        if objetivo:
            q &= db.solicitudes.objetivo.contains(objetivo)
        res = db(q).select(*fds, **args)
        for row in res:
            row.update(related=traversal_render(row.id)[1:])
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


@request.restful()
def solicitudes_internas():

    @Validate.auth_from_AR
    def GET(desde, hasta, origen=None, estado=None, codigo=None, objetivo=None, destino=None):
        """
        Solicitudes originales `padre` == None
        origen: siempre aplica (valor o áreas de la VPOR excluyendo áreas AR)
        destino: id de cualquier área, sino, no aplica
        [Aldo, 06/03/2022]:
        origen: id de área AR { 2, 46, 47 }, sino, ids de áreas de la VPOR excluyendo áreas AR
        """
        
        fds = [
            db.solicitudes.id,
            db.solicitudes.codigo,
            db.solicitudes.objetivo,
            db.solicitudes.origen,
            db.solicitudes.destino,
            db.solicitudes.solicitado_en,
            db.solicitudes.terminado_en,
            db.solicitudes.estado,
        ]
        args = dict(orderby=db.solicitudes.id)
        q = db.solicitudes.solicitado_en >= desde
        q &= db.solicitudes.solicitado_en <= hasta + ' 23:59:59'
        q &= db.solicitudes.padre_id == None
        if origen:
            q &= db.solicitudes.origen_id == origen
        else:
            _q = db.area.nivel.belongs(NIVELES_AREAS_INTERNAS)
            _q &= ~db.area.id.belongs(AREAS_AR_IDS)
            area_ids = db(_q)._select(db.area.id)
            q &= db.solicitudes.origen_id.belongs(area_ids)
        if estado:
            _lista = estado if isinstance(estado, list) else [estado]
            q &= db.solicitudes.estado_id.belongs(_lista)            
        if codigo:
            q &= db.solicitudes.codigo.contains(codigo)
        if objetivo:
            q &= db.solicitudes.objetivo.contains(objetivo)
        if destino:
            q &= db.solicitudes.destino_id == destino
        res = db(q).select(*fds, **args)
        for row in res:
            row.update(related=traversal_render(row.id)[1:])
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


@request.restful()
def areas_consultadas():

    @Validate.auth_from_AR
    def GET(desde, hasta, origen=None, curso=None):
        """
        curso: { 1: original, 2: reenviada }
        [Daymara, 30/06/2023]:
        origen: id de área AR { 2, 46, 47 }, sino, los tres combinados
        """
        
        fds = [
            db.solicitudes.destino,
            db.solicitudes.solicitado_en,
            db.solicitudes.terminado_en,
        ]
        args = dict(orderby=db.solicitudes.id)
        q = db.solicitudes.solicitado_en >= desde
        q &= db.solicitudes.solicitado_en <= hasta + ' 23:59:59'
        if origen:
            q &= db.solicitudes.origen_id == origen
        else:
            q &= db.solicitudes.origen_id.belongs(AREAS_AR_IDS)
        if curso == 1:
            q &= db.solicitudes.padre_id == None
        if curso == 2:
            q &= db.solicitudes.padre_id != None
        res = db(q).select(*fds, **args)
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


def traversal_render(solicitud_id):
    def travel(solicitud_id, root=False):
        _ = db(db.solicitudes.id == solicitud_id).select(
            db.solicitudes.id,
            db.solicitudes.codigo,
            db.solicitudes.padre_id,
            db.solicitudes.destino,
            db.solicitudes.estado,
            db.solicitudes.origen
        ).first()
        __ = db(db.solicitudes.padre_id ==
                solicitud_id).select(db.solicitudes.id)
        node_list.append(dict(
            id=_.id,
            codigo=_.codigo,
            leaf=not len(__),
            parent=_.padre_id,
            children=[row.id for row in __],
            estado=_.estado,
            destino=_.destino,
            origen=_.origen,
            root=root
        ))
        for r in __:
            travel(r.id)

    node_list = []
    travel(solicitud_id, root=True)
    return node_list


def traversal(solicitud_id):
    def travel(solicitud_id, root=False):
        _ = db(db.solicitud.id == solicitud_id).select(
            db.solicitud.id,
            db.solicitud.codigo,
            db.solicitud.padre,
            db.solicitud.destino,
            db.solicitud.estado,
            # db.solicitud.destino
        ).first()
        __ = db(db.solicitud.padre == solicitud_id).select(db.solicitud.id)
        node_list.append(dict(
            id=_.id,
            codigo=_.codigo,
            leaf=not len(__),
            parent=_.padre,
            children=[row.id for row in __],
            estado=_.estado,
            destino=_.destino,
            root=root
        ))
        for r in __:
            travel(r.id)

    node_list = []
    travel(solicitud_id, root=True)
    return node_list


@request.restful()
def solicitudes_raw():

    @Validate.auth_from_AR
    def GET(desde, hasta, destino_id):
        """
        [ago 10, 2026] by Raida:
        Se necesita un reporte crudo de las solicitudes al Departamento
        de Provisión y sus hijas para análisis de efectividad.
        """
        fds = [
            db.vw_solicitudes_raw.codigo,
            db.vw_solicitudes_raw.destino_id,
            db.vw_solicitudes_raw.origen,
            db.vw_solicitudes_raw.objetivo,
            db.vw_solicitudes_raw.solicitado_en,
            db.vw_solicitudes_raw.terminado_en,
            db.vw_solicitudes_raw.h_codigo,
            db.vw_solicitudes_raw.h_destino,
            db.vw_solicitudes_raw.h_objetivo,
            db.vw_solicitudes_raw.h_solicitado_en,
            db.vw_solicitudes_raw.h_terminado_en,
            db.vw_solicitudes_raw.supervisor,
            db.vw_solicitudes_raw.tramitador,
        ]
        q = db.vw_solicitudes_raw.solicitado_en >= desde
        q &= db.vw_solicitudes_raw.solicitado_en <= hasta + ' 23:59:59'
        q &= db.vw_solicitudes_raw.destino_id == destino_id
        res = db(q).select(*fds, orderby=db.vw_solicitudes_raw.codigo)
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


class Validate:
    """
    Validate authorization for methods, based on user administration scope (user area role_key)
    and integrity of request variables
    """

    @staticmethod
    def auth_from_AR(fn):
        def run(*k, **kw):
            if not db.area(auth.user.area).rol_key == 'AR':
                raise HTTP(403, 'Forbidden.')
            return fn(*k, **kw)

        return run
