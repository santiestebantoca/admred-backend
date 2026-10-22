# -*- coding: utf-8 -*-
__author__ = "jorge.santiesteban"

from gluon import current


def create_membership(user_id, group_ids=[]):

    if not user_id:
            return

    db = current.db

    if isinstance(group_ids, str):
        group_ids = [group_ids]

    for group_id in group_ids:
        db.auth_membership.insert(user_id=user_id, group_id=group_id)


def update_membership(user_id, group_ids=[]):

    if not user_id:
        return

    db = current.db

    if isinstance(group_ids, str):
        group_ids = [group_ids]

    # 1. Eliminar los que ya no están
    deleteQuery = db.auth_membership.user_id == user_id
    deleteQuery &= ~db.auth_membership.group_id.belongs(group_ids)
    db(deleteQuery).delete()

    # 2. Crear los nuevos (bulk)
    existentes = db(db.auth_membership.user_id == user_id).select(
        db.auth_membership.group_id)
    existentes_set = set(row.group_id for row in existentes)

    nuevos = [{'user_id': user_id, 'group_id': id}
                for id in group_ids if id not in existentes_set]
    if nuevos:
        db.auth_membership.bulk_insert(nuevos)

    # 3. Devolver los registros existentes después del PUT
    # return db(db.auth_membership.user_id == user_id).select()
