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


def _en_ambito(usuario):
    """
    Usuario dentro del ámbito del administrador no AR: su subárbol o un
    usuario sin área creado por él. AR no se acota.
    """
    if not _es_admin_no_ar():
        return True
    if not usuario:
        return False
    if usuario.area in _ids_subarbol(auth.user.area):
        return True
    return usuario.area is None and usuario.created_by == auth.user_id


def _usuarios_del_ambito():
    """
    Query de `vw_usuario` con los usuarios visibles para el administrador no AR.
    """
    ids = list(_ids_subarbol(auth.user.area))
    q = db.vw_usuario.area_id.belongs(ids)
    q |= (db.vw_usuario.area_id == None) & (db.vw_usuario.created_by == auth.user_id)
    return q


@request.restful()
def usuarios():
    
    @auth.requires_membership('administrador')
    def GET(
        id=None,
        search=None,
        search_in=None,
        nombre=None,
        area=None,
        rol=None,
        estado=None,
        page=None,
        limit=None
    ):
        if id:
            id = int(id)
            usuario_scope = db.auth_user(id)
            if not usuario_scope:
                raise HTTP(404, 'Usuario no encontrado.', **headers)
            if not _en_ambito(usuario_scope):
                raise HTTP(403, 'Forbidden.', **headers)

            grupos_ids = db(db.auth_membership.user_id == id)._select(db.auth_membership.group_id)
            usuario_en_solicitud = db.solicitud.tramitador == id
            usuario_en_solicitud |= db.solicitud.remitente == id
            usuario_en_solicitud |= db.solicitud.supervisor == id
            
            fds = [
                db.auth_user.id,
                db.auth_user.first_name,
                db.auth_user.last_name,
                db.auth_user.username,
                db.auth_user.email,
                db.auth_user.registration_key,
                db.auth_user.area,
                db.auth_user.fijo,
                db.auth_user.movil,
                db.auth_user.modified_on,
                db.auth_user.modified_by,
            ]
            usuario = db(db.auth_user.id == id).select(*fds).first()
            usuario.area = db.area(usuario.area)
            usuario.grupos = db(db.auth_group.id.belongs(grupos_ids)).select().as_list()
            usuario.modified_by = usuario.modified_by and db.vw_usuario(usuario.modified_by).name
            actividad = bool(db(usuario_en_solicitud).count())
            usuario.permisos = {
                "editar_username": not actividad,
                "eliminar": not actividad and id != auth.user_id,
            }
            return response.json(usuario)
        
        """
        returns::
        (admin): all rows from `usuario`
        (admin no AR): rows from `usuario` where
            (`usuario` is in the subtree of auth.user's area) or \
            ((`usuario` has no area) and (`usuario` is created by auth.user))
        """
        
        from math import ceil
        
        left = False
        fds = [
            db.vw_usuario.id,
            db.vw_usuario.name,
            db.vw_usuario.username,
            db.vw_usuario.registration_key,
            db.vw_usuario.area,
            db.vw_usuario.area_id,
        ]
        args = dict(distinct=True, orderby=~db.vw_usuario.id)
        q = db.vw_usuario.id > 0
        if nombre:
            q &= db.vw_usuario.name.contains(nombre)
        if area:
            q &= db.vw_usuario.area_id == area
        if estado:
            q &= db.vw_usuario.registration_key == estado
        if rol:
            q &= db.vw_usuario.id == db.auth_membership.user_id
            q &= db.auth_membership.group_id == rol
        if search and search_in:
            if isinstance(search_in, str):
                search_in = [search_in]
                
            qor = None
            for field in search_in:
                if qor:
                    qor |= db.vw_usuario[field].contains(search)
                else:
                    qor = db.vw_usuario[field].contains(search)
            q &= qor
        # administrador no AR::
        if _es_admin_no_ar():
            q &= _usuarios_del_ambito()
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
    def POST(grupos, **vars):
        """
        Auth valida:
        1. `email` y `username` no vacíos y no tomados.
        2. `password` no vacío.
        Auth establece por defecto:
        1. `registration_key`, `reset_password_key`, `registration_id` en '' (vacío).
        Reglas:
        1. Se disabilita la validación de `password` (No viene en vars).
        2. Se establecen `registration_key`, `reset_password_key`, `registration_id` en None (NULL).
        3. Se valida que `area` pertenezca al subárbol del administrador no AR; si falta, se usa la propia.
        """
        db.auth_user.password.requires = None
        db.auth_user.email.requires = None
        db.auth_user.registration_key.default = None
        db.auth_user.reset_password_key.default = None
        db.auth_user.registration_id.default = None        
        if _es_admin_no_ar():
            area_id = vars.get('area') or auth.user.area
            try:
                area_id = int(area_id)
            except (TypeError, ValueError):
                raise HTTP(422, 'Área no válida.', **headers)
            if area_id not in _ids_subarbol(auth.user.area):
                raise HTTP(403, 'Forbidden.', **headers)
            vars['area'] = area_id
        res = db.auth_user.validate_and_insert(**vars)
        if (res.errors):
            response.status = 422
            return response.json(res.errors)
        # Membership
        from applications.admred.modules.db.auth import create_membership
        
        create_membership(res.id, grupos)

        return response.json(res)

    @auth.requires_membership('administrador')
    @Validate.user_in_scope
    def PUT(id, grupos, **vars):
        """
        Reglas:
        1. Se disabilita la validación de `email` (No viene en vars).
        2. Se validan `email` y `username` no vacíos y no tomados.
        3. El no AR solo puede mover el usuario dentro de su subárbol; el área del propio usuario se conserva.
        4. Se elimina `username` si el usuario tiene actividad auditable.
        """                
        id = int(id)
        otros_usuarios = db(db.auth_user.id != id)
        db.auth_user.username.requires = [
            IS_NOT_EMPTY(),
            IS_NOT_IN_DB(otros_usuarios, "auth_user.username")
        ]
        db.auth_user.email.requires = [
            IS_NOT_EMPTY(),
            IS_NOT_IN_DB(otros_usuarios, "auth_user.email")
        ]
        if _es_admin_no_ar():
            if id == auth.user_id:
                # El propio usuario conserva siempre su área.
                vars.pop('area', None)
            else:
                area_id = vars.get('area')
                if area_id in (None, ''):
                    vars.pop('area', None)
                else:
                    try:
                        area_id = int(area_id)
                    except (TypeError, ValueError):
                        raise HTTP(422, 'Área no válida.', **headers)
                    if area_id not in _ids_subarbol(auth.user.area):
                        raise HTTP(403, 'Forbidden.', **headers)
                    vars['area'] = area_id
        # Permitir editar `username`
        usuario_en_solicitud = db.solicitud.tramitador == id
        usuario_en_solicitud |= db.solicitud.remitente == id
        usuario_en_solicitud |= db.solicitud.supervisor == id
        if bool(db(usuario_en_solicitud).count()):
            del vars['username']
        res = db(db.auth_user.id == id).validate_and_update(**vars)
        if (res.errors):
            response.status = 422
            return response.json(res.errors)
        # Membership
        from applications.admred.modules.db.auth import update_membership
        
        update_membership(id, grupos)

        return response.json(res) 
          
    @auth.requires_membership('administrador')
    @Validate.user_in_scope
    @Validate.user_not_self
    @Validate.user_not_referenced
    def DELETE(id):
        res = db(db.auth_user.id == id).delete()
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
    def user_not_referenced(fn):
        """
        User is not referenced by any "solicitud".
        """
        def run(*k, **kw):
            id = k[0]
            q = db.solicitud.tramitador == id
            q |= db.solicitud.remitente == id
            q |= db.solicitud.supervisor == id
            if db(q).count():
                raise HTTP(405, 'No permitido por una regla de integridad.', **headers)
            return fn(*k, **kw)

        return run

    @staticmethod
    def user_in_scope(fn):
        """
        Administrador AR o usuario dentro del ámbito del administrador no AR.
        """
        def run(*k, **kw):
            id = int(k[0] if k else kw.get('id'))
            if not _en_ambito(db.auth_user(id)):
                raise HTTP(403, 'Forbidden.', **headers)
            return fn(*k, **kw)

        return run

    @staticmethod
    def user_not_self(fn):
        """
        Un administrador no puede borrar su propio usuario.
        """
        def run(*k, **kw):
            id = int(k[0] if k else kw.get('id'))
            if id == auth.user_id:
                raise HTTP(403, 'Forbidden.', **headers)
            return fn(*k, **kw)

        return run
