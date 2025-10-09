# coding: utf8

tabla = db.define_table
url = URL('default', 'download', scheme=True,
          host=True, port=request.env.server_port)

tabla('upload',
      Field(
          'upload',
          'upload',
          # length of file name.
          # Linux: maximum file name 255 bytes (combined with path 4096 bytes)
          # unicode representation of characters can occupy several bytes!!
          length=250,
          uploadseparate=True,
          autodelete=True,
          required=True,
          notnull=True),
      Field('filename', required=True, notnull=True),
      Field('filemodified', required=True, notnull=True),
      Field('filesize', 'integer', required=True, notnull=True),
      Field.Virtual('file', lambda r: url + '/' + r.upload.upload))

tabla('adjunto',
      Field('solicitud_id', 'reference solicitud'),
      Field('upload_id', 'reference upload'),
      Field('tipo', 'integer'))

tabla('nivel',
      Field('nombre', notnull=True),
      Field('descripcion'),
      format=' %(nombre)s')

tabla('area',
      Field('nombre', notnull=True),
      Field('padre', 'reference area', ondelete='NO ACTION'),
      Field('nivel', 'reference nivel'),
      Field('rol_key'),
      auth.signature,
      format=' %(nombre)s')

tabla('tipo',
      Field('nombre', notnull=True),
      Field('descripcion'),
      auth.signature,
      format=' %(nombre)s')

tabla('estado',
      Field('nombre', notnull=True),
      Field('descripcion', notnull=True),
      format=' %(nombre)s')

tabla('solicitud',
      Field('codigo', unique=True, length=9),
      Field('solicitado_en', 'datetime'),
      Field('tipo', 'reference tipo'),
      Field('objetivo', 'text'),
      # Documento de entrada
      Field('origen', 'reference area'),
      Field('destino', 'reference area'),
      Field('tramitador', 'reference auth_user'),
      Field('remitente', 'reference auth_user'),
      Field('estado', 'reference estado'),
      Field('respuesta_en', 'datetime'),
      Field('terminado_en', 'datetime'),
      # Documento de salida
      Field('observaciones', 'text'),
      Field('evaluacion', 'integer'),
      # Campos auxiliares
      Field('supervisor', 'reference auth_user'),
      Field('tramitador_en', 'datetime'),
      Field('padre', 'reference solicitud'),
      Field('cumplir_en', 'datetime'))

tabla('bitacora',
      Field('solicitud', 'reference solicitud'),
      Field('fecha', 'datetime', default=request.now),
      Field('accion'),
      Field('por', 'reference auth_user', default=auth.user_id),
      Field('argumentos'))

tabla('nota',
      Field('solicitud', 'reference solicitud'),
      Field('fecha', 'datetime', default=request.now),
      Field('tramitador', 'reference auth_user'),
      Field('supervisor', 'reference auth_user'),
      Field('texto', 'text'),
      Field('evento')
      )

""" Tables relationships"""
db.auth_user.area.requires = IS_IN_DB(db, 'area.id', ' %(nombre)s')
db.area.nivel.requires = IS_IN_DB(db, 'nivel.id', ' %(nombre)s')
