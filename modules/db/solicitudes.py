# -*- coding: utf-8 -*-
__author__ = "jorge.santiesteban"

from gluon import current


def codigo():
    """
    `codigo` is a db view
    """
    from datetime import date

    db = current.db
    
    year, consec = str(date.today().year)[2:], 1
    rows = db.executesql("SELECT codigo FROM codigo", as_dict=True)
    if len(rows):
        _, _year, _consec = rows[0]["codigo"].split("-")
        consec = int(_consec) + 1 if _year == year else 1
    return "S-%s-%04d" % (year, consec)


def solicitudes_recibidas():

    db = current.db
    auth = current.auth
    
    if auth.has_membership("supervisor"):
        return db.solicitudes.destino_id == auth.user.area
    return db.solicitudes.tramitador_id == auth.user_id


def solicitudes_enviadas():

    db = current.db
    auth = current.auth
    
    if auth.has_membership("supervisor"):
        return db.solicitudes.origen_id == auth.user.area
    return db.solicitudes.remitente_id == auth.user_id


def terminado_en_periodo(period):
    """
    Period ago:
    [14 days, 1 month, 6 months, 1 year]
    """
    from datetime import date, timedelta

    db = current.db
    
    start = date.today()
    if period in ["2", "3", "4"]:
        i_month = start.month - [1, 6, 12][int(period) - 2]
        month = i_month if i_month > 0 else i_month + 12
        year = start.year if i_month > 0 else start.year - 1
        start = date(year, month, start.day)
    else:  # period == 1 or period == None
        start -= timedelta(days=14)
    return db.solicitudes.terminado_en > start


def solicitudes(
    tray,
    state,
    period=None,
    status=None,
    codigo=None,
    objetivo=None,
    origen=None,
    destino=None,
    search=None,
    search_in=None,
    page=None,
    limit=None
    ):
    """
    returns::
    """

    db = current.db
    auth = current.auth
    
    left = False
    fds = [
        db.solicitudes.id,
        db.solicitudes.codigo,
        db.solicitudes.objetivo,
        db.solicitudes.estado,
        db.solicitudes.solicitado_en,
        db.solicitudes.terminado_en,
        db.solicitudes.origen if tray == "recibidas" else db.solicitudes.destino,
        db.solicitudes.padre_id
    ]
    args = dict(distinct=True, orderby=~db.solicitudes.id)
    q = db.solicitudes.id > 0
    if tray == "recibidas":
        q = solicitudes_recibidas()
    elif tray == "enviadas":
        q = solicitudes_enviadas()
    if state == "pendientes":
        q &= db.solicitudes.estado_id != 4
    elif state == "terminadas":
        q &= db.solicitudes.estado_id == 4
        q &= terminado_en_periodo(period)
    if status:
        q &= db.solicitudes.estado_id == status
    if codigo:
        q &= db.solicitudes.codigo.contains(codigo)
    if objetivo:
        q &= db.solicitudes.objetivo.contains(objetivo)
    if origen:
        q &= db.solicitudes.origen.contains(origen)
    if destino:
        q &= db.solicitudes.destino.contains(destino)
    # Search in fields
    if search:
        qor = None
        for field in search_in:
            if qor:
                qor |= db.solicitudes[field].contains(search)
            else:
                qor = db.solicitudes[field].contains(search)
        q &= qor
    # return::
    if page and limit:
        _page = int(page)
        _limit = int(limit)
        args.update(limitby=((_page - 1) * _limit, _page * _limit))
        sql = db(q)._select(*fds, left=left, **args)
        data = db.executesql(sql)
        sql = db(q)._select(*fds, left=left).split(" FROM ", 1)
        sql = "SELECT COUNT(DISTINCT solicitudes.id) FROM " + sql[1]
        total = db.executesql(sql)[0][0]
        total_pages = ceil(total / _limit)
        return response.json({
            "data": data,
            "meta": {
                "total": total,
                "page": _page,
                "limit": _limit,
                "totalPages": total_pages,
                "hasNext": _page < total_pages,
                "hasPrev": _page > 1
            }
        })    
    sql = db(q)._select(*fds, left=left, **args)
    data = db.executesql(sql)    
    return {
        "data": data,
        "meta": {
            "total": len(data)
        }
    }


def add_adjuntos(solicitud_id, upload_ids, tipo=1):
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
