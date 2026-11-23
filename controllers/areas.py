# -*- coding: utf-8 -*-
__author__ = 'jorge.santiesteban'


def _es_admin_no_ar():
    """
    Administrador autenticado cuya área no tiene rol AR.
    """
    if not auth.user or not auth.has_membership('administrador'):
        return False
    area = db.area(auth.user.area)
    return bool(area) and area.rol_key != 'AR'


def _ids_subarbol(area_id):
    """
    Ids del área indicada y de todos sus descendientes.

    Incluye el propio id y usa un conjunto de visitados para no entrar en un
    bucle si los datos trajeran un ciclo.
    """
    if not area_id:
        return set()
    filas = db(db.area.id > 0).select(db.area.id, db.area.padre)
    hijas = {}
    for fila in filas:
        hijas.setdefault(fila.padre, []).append(fila.id)
    ids = set()
    pendientes = [area_id]
    while pendientes:
        actual = pendientes.pop()
        if actual in ids:
            continue
        ids.add(actual)
        pendientes.extend(hijas.get(actual, []))
    return ids


def _nivel_hijo(nivel_id):
    """
    Nivel que corresponde a las hijas de un nivel.

    El nivel 5 es autorrecursivo; el resto sigue el `padre_id` del catálogo.
    """
    if not nivel_id:
        return None
    if nivel_id == 5:
        return 5
    fila = db(db.nivel.padre_id == nivel_id).select(
        db.nivel.id, limitby=(0, 1)).first()
    return fila.id if fila else None


def _alta_no_ar(vars):
    """
    Ajusta el alta del administrador no AR: padre del subárbol y nivel derivado.

    Solo se aceptan los campos propios del alta; en particular se descartan
    `rol_key` e `is_active`, que no puede fijar un administrador no AR.
    """
    padre_id = vars.get('padre') or auth.user.area
    try:
        padre_id = int(padre_id)
    except (TypeError, ValueError):
        raise HTTP(422, 'Área padre no válida.', **headers)
    if padre_id not in _ids_subarbol(auth.user.area):
        raise HTTP(403, 'Forbidden.', **headers)
    padre_area = db.area(padre_id)
    nivel_id = _nivel_hijo(padre_area.nivel) if padre_area else None
    if not nivel_id:
        raise HTTP(422, 'El área padre no admite áreas hijas.', **headers)
    return {
        'nombre': vars.get('nombre'),
        'padre': padre_id,
        'nivel': nivel_id,
    }


@request.restful()
def areas():
    def padre(vars):
        """
        Para formularios.
        Quita/pone un "área padre" según la lógica de negocio (esquema de niveles):
        - Niveles 1, 4 y 6 son root, no tienen nivel padre, por tanto no tienen área padre.
        - El nivel 2 tiene al nivel 1 de padre, este último con una única área, VPOR.
        - El nivel 5 puede colgar de un área de nivel 4 o de otra de nivel 5.
        """
        
        if vars['nivel'] in ['1', '4', '6']:
            vars['padre'] = None
        elif vars['nivel'] == '2':
            vars['padre'] = 1
        return vars

    def GET(id=None, search=None, search_in=None, nombre=None, padre=None, nivel=None, rol_key=None, page=None, limit=None):
        if id:
            id = int(id)
            no_ar = _es_admin_no_ar()
            ambito = _ids_subarbol(auth.user.area) if no_ar else set()
            if no_ar and id not in ambito:
                raise HTTP(403, 'Forbidden.', **headers)

            area_en_solicitud = db.solicitud.origen == id
            area_en_solicitud |= db.solicitud.destino == id
            area_en_usuario = db.auth_user.area == id

            area = db.area(id)
            area.nivel = db.nivel(area.nivel)
            area.padre = db.area(area.padre)
            area.modified_by = area.modified_by and db.vw_usuario(area.modified_by).name
            area.permisos = {
                "editar": bool(
                    auth.user
                    and auth.has_membership('administrador')
                    and (not no_ar or (id in ambito and id != auth.user.area))
                ),
                "eliminar": (
                    not bool(db(area_en_solicitud).count() + db(area_en_usuario).count())
                    and not (no_ar and id == auth.user.area)
                )
            }
            return response.json(area)
        
        from math import ceil
                
        fds = [
            db.areas.id,
            db.areas.nombre,
            db.areas.padre,
            db.areas.nivel,
            db.areas.rol_key,
            db.areas.padre_id,
            db.areas.nivel_id,
        ]
        args = dict(distinct=True, orderby=~db.areas.id)
        q = db.areas.id > 0
        if _es_admin_no_ar():
            q &= db.areas.id.belongs(list(_ids_subarbol(auth.user.area)))
        if nombre:
            q &= db.areas.nombre.contains(nombre)
        if nivel:
            q &= db.areas.nivel_id == nivel
        if padre:
            q &= db.areas.padre_id == padre
        if rol_key:
            q &= db.areas.rol_key != None
        if search and search_in:
            if isinstance(search_in, str):
                search_in = [search_in]
                
            qor = None
            for field in search_in:
                if qor:
                    qor |= db.areas[field].contains(search)
                else:
                    qor = db.areas[field].contains(search)
            q &= qor
        # return::
        if page and limit:
            _page = int(page)
            _limit = int(limit)
            args.update(limitby=((_page - 1) * _limit, _page * _limit))
            data = db(q).select(*fds, **args).as_list()
            total = db(q).count()
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
        data = db(q).select(*fds, **args).as_list()
        return response.json({
            "data": data,
            "meta": { "total": len(data) }
        }) 

    @auth.requires_membership('administrador')
    def POST(**vars):
        if _es_admin_no_ar():
            vars = _alta_no_ar(vars)
        else:
            vars = padre(vars)
        res = db.area.validate_and_insert(**vars)
        if (res.errors):
            response.status = 422
            return response.json(res.errors)
        return response.json(res)

    @auth.requires_membership('administrador')
    @Validate.area_in_scope
    def PUT(id, **vars):
        if _es_admin_no_ar():
            # El no AR solo puede cambiar el nombre: no mueve el área, no
            # cambia su nivel y no puede fijar `rol_key` ni `is_active`.
            vars = {k: vars[k] for k in ('nombre',) if k in vars}
        else:
            vars = padre(vars)
        res = db(db.area.id == id).validate_and_update(**vars)        
        if (res.errors):
            response.status = 422
            return response.json(res.errors)
        return response.json(res)

    @auth.requires_membership('administrador')
    @Validate.area_in_scope
    @Validate.area_not_referenced
    def DELETE(id, **vars):
        res = db(db.area.id == id).delete()
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
    def area_in_scope(fn):
        """
        El administrador no AR solo opera sobre el subárbol de su área y nunca
        sobre su propia área.
        """
        def run(*k, **kw):
            if _es_admin_no_ar():
                id = int(k[0] if k else kw.get('id'))
                if id == auth.user.area or id not in _ids_subarbol(auth.user.area):
                    raise HTTP(403, 'Forbidden.', **headers)
            return fn(*k, **kw)

        return run

    @staticmethod
    def area_not_referenced(fn):
        def run(*k, **kw):
            id = k[0]
            c = db(db.area.padre == id).count()
            c += db(db.auth_user.area == id).count()
            c += db((db.solicitud.origen == id) |
                    (db.solicitud.destino == id)).count()
            if c:
                raise HTTP(405, 'No permitido por una regla de integridad', **headers)
            return fn(*k, **kw)

        return run
