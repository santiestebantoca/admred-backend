# -*- coding: utf-8 -*-
__author__ = "jorge.santiesteban"


@request.restful()
def auth_membership():

    def GET(usuario_id=0):
        group_ids = db(db.auth_membership.user_id == usuario_id)._select(db.auth_membership.group_id)
        res = db(db.auth_group.id.belongs(group_ids)).select()
        return response.json(res)
    
    def PUT(user_id, group_id):        
        # 1. Eliminar los que ya no están
        deleteQuery = db.auth_membership.user_id == user_id
        deleteQuery &= ~db.auth_membership.group_id.belongs(group_id)
        db(deleteQuery).delete()

        # 2. Crear los nuevos (bulk)
        existentes = db(db.auth_membership.user_id == user_id).select(
            db.auth_membership.group_id)
        existentes_set = set(row.group_id for row in existentes)

        nuevos = [{'user_id': user_id, 'group_id': id}
                  for id in group_id if id not in existentes_set]
        if nuevos:
            db.auth_membership.bulk_insert(nuevos)

        # 3. Devolver los registros existentes después del PUT
        # res = db(db.auth_membership.user_id == usuario_id).select()

        return response.json([])

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()
