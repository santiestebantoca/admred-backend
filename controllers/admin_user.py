# -*- coding: utf-8 -*-
__author__ = 'jorge.santiesteban'


# Statics

@request.restful()
def authgroup():

    def GET(*args, **vars):
        return response.json(db(db.auth_group).select())

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


@request.restful()
def areas():

    def GET(*args, **vars):
        return response.json(db(db.area).select())

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()


@request.restful()
def membership():

    def GET(user_id, **vars):
        res = db(db.auth_membership.user_id == user_id).select()
        return response.json([r.group_id for r in res])

    @auth.requires_membership('administrador')
    def POST(*args, **vars):
        group_id = int(vars['group_id'])
        user_id = int(vars['user_id'])
        res = auth.add_membership(group_id, user_id)
        return response.json(dict(id=res, errors={}))

    @auth.requires_membership('administrador')
    def DELETE(*args, **vars):
        group_id = int(vars['group_id'])
        user_id = int(vars['user_id'])
        res = auth.del_membership(group_id, user_id)
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()
