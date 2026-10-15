# -*- coding: utf-8 -*-
__author__ = 'jorge.santiesteban'


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
            usuario.permisos = {
                "eliminar": not bool(db(usuario_en_solicitud).count())
            }
            return response.json(usuario)
        
        """
        returns::
        (admin): all rows from `usuario`
        (admin no AR): rows from `usuario` where
            (`usuario` with same `area` as auth.user) or \
            ((`usuario` has no area) and (`usuario` is created by auth.user))
        """
        
        from math import ceil
        
        left = False
        fds = [
            db.vw_usuario.id,
            db.vw_usuario.name,
            db.vw_usuario.username,
            db.vw_usuario.registration_key,
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
        if db.area(auth.user.area).rol_key != 'AR':
            q &= db.vw_usuario.area_id == auth.user.area
            q |= (db.vw_usuario.area_id == None) & (db.vw_usuario.created_by == auth.user_id)
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
        `email` y `username`, que no estén tomados.
        `password` es requerido.
        Reglas:
        1. Se disabilita la validación de Auth para `password`.
        2. Un administrador no AR solo crea usuarios en su área.
        """
        db.auth_user.password.requires = None
        if db.area(auth.user.area).rol_key != 'AR':
            vars['area'] = auth.user.area
        res = db.auth_user.validate_and_insert(**vars)
        if (res.errors):
            response.status = 422
            return response.json(res.errors)
        # Membership
        from applications.admred.modules.db.auth import create_membership
        
        create_membership(res['id'], grupos)

        return response.json(res)

    @auth.requires_membership('administrador')
    @Validate.user_in_scope
    def PUT(id, grupos, **vars):
        """
        `registration_key`="", web2py lo inserta con NULL.
        Cambio este comportamiento con registration_key.requires = None
        Reglas:
        1. `email` y `username` no permiten vacíos y no pueden existir en otros registros.
        2. Un administrador no AR no cambia `area`.
        3. `username` se puede cambiar solo si el usuario no tiene actividad auditable.
        """
        db.auth_user.registration_key.requires = None
        otros_usuarios = db(db.auth_user.id != id)
        db.auth_user.username.requires = [
            IS_NOT_EMPTY(),
            IS_NOT_IN_DB(otros_usuarios, "auth_user.username")
        ]
        db.auth_user.email.requires = [
            IS_NOT_EMPTY(),
            IS_NOT_IN_DB(otros_usuarios, "auth_user.email")
        ]
        if db.area(auth.user.area).rol_key != "AR":
            del vars['area']
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
        Administrador is from the "AR" area or shares the same area as the updated user.
        """
        def run(*k, **kw):
            id = k[0]
            c = db.area(auth.user.area).rol_key == 'AR'
            c |= db.auth_user(id).area in [auth.user.area, None]  # None, permite usuarios sin area 
            if not c:
                raise HTTP(403, 'Forbidden.', **headers)
            return fn(*k, **kw)

        return run
