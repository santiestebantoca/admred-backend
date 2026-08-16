# coding: utf8

url = URL('default', 'download', scheme=True,
          host=True, port=request.env.server_port)

tabla('vw_usuario',
      Field('name'),
      Field('username'),
      Field('email'),
      Field('fijo'),
      Field('movil'),
      Field('registration_key'),
      Field('created_by'),
      Field('area'),
      Field('area_id', 'reference area'),
      migrate=False)

tabla('solicitudes',
      Field('codigo'),
      Field('objetivo'),
      Field('origen'),
      Field('destino'),
      Field('estado'),
      Field('solicitado_en', 'datetime'),
      Field('terminado_en', 'datetime'),
      Field('origen_id', 'reference area'),
      Field('destino_id', 'reference area'),
      Field('remitente_id', 'reference usuario'),
      Field('tramitador_id', 'reference usuario'),
      Field('supervisor_id', 'reference usuario'),
      Field('tramitador_rk'),
      Field('supervisor_rk'),
      Field('estado_id', 'reference estado'),
      Field('padre_id', 'reference solicitudes'),
      migrate=False)

tabla('areas',
      Field('nombre'),
      Field('padre'),
      Field('nivel'),
      Field('rol_key'),
      Field('padre_id'),
      Field('nivel_id'),
      migrate=False)

tabla('adjuntos',
      Field('solicitud_id', 'referene solicitud'),
      Field('upload_id', 'reference upload'),
      Field('tipo', 'integer'),
      Field('upload'),
      Field('filename'),
      Field('filesize'),
      Field('filemodified'),
      Field.Virtual('file', lambda r: url + '/' + r.adjuntos.upload),
      migrate=False)

tabla('vw_solicitudes_a_provision',
      Field('codigo'),
      Field('origen'),
      Field('objetivo'),
      Field('solicitado_en'),
      Field('terminado_en'),
      Field('h_codigo'),
      Field('h_destino'),
      Field('h_objetivo'),
      Field('h_solicitado_en'),
      Field('h_terminado_en'),
      migrate=False
)
