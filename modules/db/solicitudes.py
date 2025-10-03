# -*- coding: utf-8 -*-
__author__ = "jorge.santiesteban"


def limitby(vars):
    min, max = vars.limit.split(",")
    return (int(min), int(max))


def codigo(db):
    """
    `codigo` is a db view
    """
    from datetime import date

    year, consec = str(date.today().year)[2:], 1
    rows = db.executesql("SELECT codigo FROM codigo", as_dict=True)
    if len(rows):
        _, _year, _consec = rows[0]["codigo"].split("-")
        consec = int(_consec) + 1 if _year == year else 1
    return "S-%s-%04d" % (year, consec)


def solicitudes_recibidas(auth, db):
    if auth.has_membership("supervisor"):
        return db.solicitudes.destino_id == auth.user.area
    return db.solicitudes.tramitador_id == auth.user_id


def solicitudes_enviadas(auth, db):
    if auth.has_membership("supervisor"):
        return db.solicitudes.origen_id == auth.user.area
    return db.solicitudes.remitente_id == auth.user_id


def terminado_en_periodo(db, period):
    """
    Period ago:
    [14 days, 1 month, 6 months, 1 year]
    """
    from datetime import date, timedelta

    start = date.today()
    if period in ["2", "3", "4"]:
        i_month = start.month - [1, 6, 12][int(period) - 2]
        month = i_month if i_month > 0 else i_month + 12
        year = start.year if i_month > 0 else start.year - 1
        start = date(year, month, start.day)
    else:
        start -= timedelta(days=14)
    return db.solicitudes.terminado_en > start


def solicitudes(db, auth, vars):
    """
    returns::
    """
    left = False
    fds = [
        db.solicitudes.id,
        db.solicitudes.codigo,
        db.solicitudes.objetivo,
        db.solicitudes.estado,
        db.solicitudes.solicitado_en,
        db.solicitudes.terminado_en,
        db.solicitudes.origen if vars.tray == "recibidas" else db.solicitudes.destino,
        # *([db.solicitudes.origen] if vars.tray == "recibidas" else []), Python 3.x
        # *([db.solicitudes.destino] if vars.tray == "enviadas" else []),
        # db.solicitudes.supervisor_rk, # future
        # db.solicitudes.tramitador_rk # future
        db.solicitudes.padre_id
    ]
    args = dict(distinct=True, orderby=~db.solicitudes.id)
    vars.limit and args.update(limitby=limitby(vars))
    q = db.solicitudes.id > 0
    if vars.tray == "recibidas":
        q = solicitudes_recibidas(auth, db)
    elif vars.tray == "enviadas":
        q = solicitudes_enviadas(auth, db)
    if vars.state == "pendientes":
        q &= db.solicitudes.estado_id != 4
    elif vars.state == "terminadas":
        q &= db.solicitudes.estado_id == 4
        q &= terminado_en_periodo(db, vars.period)
    if vars.stateId:
        q &= db.solicitudes.estado_id == vars.stateId
    if vars.codigo:
        q &= db.solicitudes.codigo.contains(vars.codigo)
    if vars.objetivo:
        q &= db.solicitudes.objetivo.contains(vars.objetivo)
    if vars.origen:
        q &= db.solicitudes.origen.contains(vars.origen)
    if vars.destino:
        q &= db.solicitudes.destino.contains(vars.destino)
    # Search in fields
    if vars.search:
        qor = None
        for field in vars.headers.split(","):
            if qor:
                qor |= db.solicitudes[field].contains(vars.search)
            else:
                qor = db.solicitudes[field].contains(vars.search)
        q &= qor
    # return::
    sql = db(q)._select(*fds, left=left, **args)
    rows = db.executesql(sql)
    sql = db(q)._select(*fds, left=left).split(" FROM ", 1)
    sql = "SELECT COUNT(DISTINCT solicitudes.id) FROM " + sql[1]
    count = db.executesql(sql)[0][0]
    return dict(data=rows, total=count)


def add_adjuntos(db, solicitud_id, upload_ids, tipo=1):
    for upload_id in upload_ids:
        if (
            db(
                (db.adjunto.solicitud_id == solicitud_id)
                & (db.adjunto.upload_id == upload_id)
                & (db.adjunto.tipo == tipo)
            ).count()
            == 0
        ):
            db.adjunto.insert(solicitud_id=solicitud_id, upload_id=upload_id, tipo=tipo)
