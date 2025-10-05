# -*- coding: utf-8 -*-
__author__ = 'jorge.santiesteban'


@request.restful()
def buscar():

    @auth.requires_login()
    def GET(*args, **vars):
        res = db(db.solicitud.codigo.contains(vars['codigo'])).select(
            db.solicitud.id, db.solicitud.codigo, limitby=(0, 10))
        return response.json(res or {})

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


@request.restful()
def areas():

    @auth.requires_login()
    def GET(*args, **vars):
        if 'nivel' in vars:
            # New for "nivel 5" that is an extension of "nivel 4"
            if vars['nivel'] == 4:
                q = db.area.nivel.belongs((4, 5))
            else:
                q = db.area.nivel == vars['nivel']
        else:
            q = db.area
        res = db(q).select(db.area.id, db.area.nombre)
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


@request.restful()
def pendientes():

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
def externas():

    @Validate.auth_from_AR
    def GET(*args, **vars):
        """
        solicitudes from VPOR outer areas, to DAR area
        :return:
        """
        fields = [
            db.solicitudes.id,
            db.solicitudes.codigo,
            db.solicitudes.objetivo,
            db.solicitudes.origen,
            db.solicitudes.destino,
            db.solicitudes.solicitado_en,
            db.solicitudes.terminado_en,
            db.solicitudes.estado,
        ]
        if request.vars.origen:
            q = db.solicitudes.origen_id == request.vars.origen
        else:
            area_ids = db(db.area.nivel == 4)._select(db.area.id)
            q = db.solicitudes.origen_id.belongs(area_ids)
        q &= db.solicitudes.destino_id == 2

        if request.vars.terminada:
            if request.vars.terminada == '1':
                q &= db.solicitudes.estado_id == 4
            if request.vars.terminada == '2':
                q &= db.solicitudes.estado_id < 4
        if request.vars.desde:
            q &= db.solicitudes.solicitado_en >= request.vars.desde
        if request.vars.hasta:
            q &= db.solicitudes.solicitado_en <= request.vars.hasta + ' 23:59:59'
        if request.vars.codigo:
            q &= db.solicitudes.codigo.contains(request.vars.codigo)
        if request.vars.objetivo:
            q &= db.solicitudes.objetivo.contains(request.vars.objetivo)
        res = db(q).select(*fields, orderby=db.solicitudes.id)
        for row in res:
            # fields = [
            #     db.solicitudes.id,
            #     db.solicitudes.codigo,
            #     db.solicitudes.estado,
            #     db.solicitudes.destino
            # ]
            # q = db.solicitudes.padre_id == row.id
            # row.update(related=db(q).select(*fields).as_list())
            row.update(related=traversal_render(row.id)[1:])
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


@request.restful()
def internas():

    @Validate.auth_from_AR
    def GET(*args, **vars):
        """
        [mar 6, 2022] by Aldo: select between 4 types of origin, with ('padre'==None):
        1- 'Dirección de Administración de la Red' (id: 2, rol_key == 'AR')
        2- 'Departamento de Administración' (id: 46, rol_key == 'AR')
        3- 'Departamento de Planificación y Provisión' (id: 47, rol_key == 'DAR')
        4- Other areas form VPOR, none of the ones before
        """
        fields = [
            db.solicitudes.id,
            db.solicitudes.codigo,
            db.solicitudes.objetivo,
            db.solicitudes.origen,
            db.solicitudes.destino,
            db.solicitudes.solicitado_en,
            db.solicitudes.terminado_en,
            db.solicitudes.estado,
        ]
        # expect a parameter name = origin : {'dir_adm', 'dep_adm', 'dep_pro', 'other'}
        if request.vars.origin == 'dir_adm':
            q = db.solicitudes.origen_id == 2
        if request.vars.origin == 'dep_adm':
            q = db.solicitudes.origen_id == 46
        if request.vars.origin == 'dep_pro':
            q = db.solicitudes.origen_id == 47
        if request.vars.origin == 'other':
            area_ids = [_.id for _ in db(db.area.nivel < 4).select(
                db.area.id) if _.id not in [2, 46, 47]]
            q = db.solicitudes.origen_id.belongs(area_ids)
        q &= db.solicitudes.padre_id == None
        if request.vars.destino:
            q &= db.solicitudes.destino_id == request.vars.destino
        if request.vars.terminada:
            if request.vars.terminada == '1':
                q &= db.solicitudes.estado_id == 4
            if request.vars.terminada == '2':
                q &= db.solicitudes.estado_id < 4
        if request.vars.desde:
            q &= db.solicitudes.solicitado_en >= request.vars.desde
        if request.vars.hasta:
            q &= db.solicitudes.solicitado_en <= request.vars.hasta + ' 23:59:59'
        if request.vars.codigo:
            q &= db.solicitudes.codigo.contains(request.vars.codigo)
        if request.vars.objetivo:
            q &= db.solicitudes.objetivo.contains(request.vars.objetivo)
        res = db(q).select(*fields, orderby=db.solicitudes.id)
        for row in res:
            # fields = [
            #     db.solicitudes.id,
            #     db.solicitudes.codigo,
            #     db.solicitudes.estado,
            #     db.solicitudes.destino
            # ]
            # q = db.solicitudes.padre_id == row.id
            # row.update(related=db(q).select(*fields).as_list())
            row.update(related=traversal_render(row.id)[1:])
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
def person():

    @auth.requires_login()
    def GET(*args, **vars):
        q = db.usuario.area_id == auth.user.area
        q &= ((db.usuario.registration_key == None) |
              (db.usuario.registration_key == ''))
        res = db(q).select(db.usuario.id, db.usuario.name)
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


@request.restful()
def solicitudes():

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
def consultadas():

    @Validate.auth_from_AR
    def GET(*args, **vars):
        """
        [jun 30, 2023] by Daymara: select between 4 types of origin:
        1- 'Dirección de Administración de la Red' (id: 2, rol_key == 'AR')
        2- 'Departamento de Administración' (id: 46, rol_key == 'AR')
        3- 'Departamento de Planificación y Provisión' (id: 47, rol_key == 'DAR')
        4- The three of them combined
        """
        fields = [
            # db.solicitudes.id,
            # db.solicitudes.codigo,
            # db.solicitudes.objetivo,
            # db.solicitudes.origen,
            db.solicitudes.destino,
            db.solicitudes.solicitado_en,
            db.solicitudes.terminado_en,
            # db.solicitudes.estado,
        ]
        # expect a parameter name = origin : {'dir_adm', 'dep_adm', 'dep_pro', 'comb'}
        if request.vars.origin == 'dir_adm':
            q = db.solicitudes.origen_id == 2
        if request.vars.origin == 'dep_adm':
            q = db.solicitudes.origen_id == 46
        if request.vars.origin == 'dep_pro':
            q = db.solicitudes.origen_id == 47
        if request.vars.origin == 'comb':
            q = db.solicitudes.origen_id.belongs([2, 46, 47])
        # q &= db.solicitudes.padre_id == None
        if request.vars.desde:
            q &= db.solicitudes.solicitado_en >= request.vars.desde
        if request.vars.hasta:
            q &= db.solicitudes.solicitado_en <= request.vars.hasta + ' 23:59:59'
        res = db(q).select(*fields, orderby=db.solicitudes.id)
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
