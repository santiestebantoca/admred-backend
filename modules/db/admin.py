# -*- coding: utf-8 -*-
__author__ = 'jorge.santiesteban'


def limitby(vars):
    min, max = vars.limit.split(',')
    return (int(min), int(max))


def users(db, auth, vars):
    """
    returns::
    (admin): all rows from `usuario`
    (admin no AR): rows from `usuario` where
        (`usuario` with same `area` as auth.user) or \
        ((`usuario` has no area) and (`usuario` is created by auth.user))
    """
    left = False
    fds = [
        db.usuario.id,
        db.usuario.name,
        db.usuario.username,
        db.usuario.registration_key,
    ]
    args = dict(distinct=True, orderby=~db.usuario.id)
    vars.limit and args.update(limitby=limitby(vars))
    q = db.usuario.id > 0
    if vars.name:
        q &= db.usuario.name.contains(vars.name)
    # if vars.no_area:
    #     q &= db.usuario.area_id == None
    elif vars.area:
        q &= db.usuario.area_id == vars.area
    if vars.blocked:
        q &= db.usuario.registration_key == 'blocked'
    if vars.group:
        q &= db.usuario.id == db.auth_membership.user_id
        q &= db.auth_membership.group_id == vars.group
    # administrador no AR::
    if db.area(auth.user.area).rol_key != 'AR':
        q &= db.usuario.area_id == auth.user.area
        q |= (db.usuario.area_id == None) & (db.usuario.created_by == auth.user_id)
    # return::
    sql = db(q)._select(*fds, left=left, **args)
    rows = db.executesql(sql)
    sql = db(q)._select(*fds, left=left).split(' FROM ', 1)
    sql = 'SELECT COUNT(DISTINCT usuario.id) FROM ' + sql[1]
    count = db.executesql(sql)[0][0]
    return dict(data=rows, total=count)


def areas(db, auth, vars):
    """
    returns::
    db.executesql(db(db.areas)._select(orderby=~db.areas.id))
    """
    left = False
    fds = [
        db.areas.id,
        db.areas.nombre,
        db.areas.padre,
        db.areas.nivel,
        db.areas.rol_key,
    ]
    args = dict(distinct=True, orderby=~db.areas.id)
    vars.limit and args.update(limitby=limitby(vars))
    q = db.areas.id > 0
    if vars.nombre:
        q &= db.areas.nombre.contains(vars.nombre)
    if vars.nivel:
        q &= db.areas.nivel_id == vars.nivel
    if vars.padre:
        q &= db.areas.padre_id == vars.padre
    # return::
    sql = db(q)._select(*fds, left=left, **args)
    rows = db.executesql(sql)
    sql = db(q)._select(*fds, left=left).split(' FROM ', 1)
    sql = 'SELECT COUNT(DISTINCT areas.id) FROM ' + sql[1]
    count = db.executesql(sql)[0][0]
    return dict(data=rows, total=count)


def padres(db, auth, vars):
    """
    niveles
    (1) Vicepresidencia VPOR -> (2) Direcciones... -> (3) Departamentos
    (4) Vicepresidencias esternas -> (5) Direcciones, Grupos, Departamentos...
    """
    fds = [
        db.areas.id,
        db.areas.nombre,
    ]
    args = dict(orderby=db.areas.nombre)
    if vars.nivel:
        nivel = int(vars.nivel)
        if nivel in [2, 3, 5]:
            nivel = nivel - 1
            q = db.areas.nivel_id == nivel
            # return::
            sql = db(q)._select(*fds, **args)
            rows = db.executesql(sql)
            return rows
    return []


def tipos(db, auth, vars):
    """
    returns::
    """
    fds = [db.tipo.id, db.tipo.nombre, db.tipo.descripcion]
    args = dict(orderby=~db.tipo.id)
    vars.limit and args.update(limitby=limitby(vars))
    q = db.tipo.id > 0
    if vars.nombre:
        q &= db.tipo.nombre.contains(vars.nombre)
    if vars.descripcion:
        q &= db.tipo.descripcion.contains(vars.descripcion)
    # return::
    sql = db(q)._select(*fds, **args)
    rows = db.executesql(sql)
    sql = db(q)._select(*fds).split(' FROM ', 1)
    sql = 'SELECT COUNT(DISTINCT tipo.id) FROM ' + sql[1]
    count = db.executesql(sql)[0][0]
    return dict(data=rows, total=count)
