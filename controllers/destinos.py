# -*- coding: utf-8 -*-
__author__ = "jorge.santiesteban"


@request.restful()
def destinos():

    @auth.requires_login()
    def GET(limit=None, search=None):
        """
        db.area.id == 2, es la Dirección de Administración de la Red
        db.area.nivel == 2, es el nivel de Direcciones y Grupos (VPOR)
        db.area.padre == area.id, son las áreas hijas del área
        db.area.id == area.padre, es el padre del área
        """
        
        def limitby(limit):
            min, max = limit.split(",")
            return (int(min), int(max))

        left = False
        fds = [
            db.area.id,
            db.area.nombre
        ]
        args = dict(distinct=True, orderby=~db.area.id)
        limit and args.update(limitby=limitby(limit))
        # q = db.area.id > 0
        
        # Reglas de negocio usando el usuario autenticado
        area = db.area(auth.user.area)
        if area.rol_key == "AR":  # Dirección de Administración y sus Departamentos
            q = db.area.id > 0
        elif area.nivel == 1:  # 1 Vicepresidencia
            q = db.area.id == 2
        elif area.nivel == 2:  # 2 Direcciones y Grupos
            q = db.area.nivel == 2
            q |= db.area.padre == area.id
        elif area.nivel == 3:  # 3 Departamentos
            q = db.area.id == area.padre
        elif area.nivel in [4, 5]:  # 4, 5 Áreas externas
            q = db.area.id == 2
        elif area.nivel == 6:  # 6 Grupos de Administración de los Territorios
            q = db.area.id == 2
            q |= db.area.padre == area.id
        elif area.nivel == 7:  # 7 Áreas de los Territorios
            q = db.area.id == area.padre
            
        if search:
            q &= db.area.nombre.contains(search)
        
        # return::
        # sql = db(q)._select(*fds, left=left, **args)
        # rows = db.executesql(sql)
        # sql = db(q)._select(*fds, left=left).split(" FROM ", 1)
        # sql = "SELECT COUNT(DISTINCT solicitudes.id) FROM " + sql[1]
        # count = db.executesql(sql)[0][0]
        # return dict(data=rows, total=count)    
            
        res = db(q).select(*fds, left=left, **args)
        return response.json(res)

    def OPTIONS(*args, **vars):
        raise HTTP(200, **headers)

    return locals()
