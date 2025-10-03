# -*- coding: utf-8 -*-
__author__ = 'jorge.santiesteban'


def index():
    return dict()


@cache.action()
def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    if request.args(0).startswith('upload'):
        rows = db(db.upload.upload == request.args(0)
                  ).select(db.upload.filename)
        if len(rows) == 1:
            return response.download(request, db, download_filename=rows[0].filename)
        else:
            raise HTTP(404)
    return response.download(request, db)


def smstest():
    from applications.admred.modules.util import fetchPOST
    url = configuration.get('api_sms.enviar')
    data = {
        'number': auth.user.fijo,
        'text': 'Mensaje de prueba',
        'sender': 'ADM Red'
    }
    return fetchPOST(url, data)  # 1 or something else


def emailtest():
    return mail.send(
        to=[auth.user.email],
        subject='Correo de prueba de ADM Red',
        message='Correo de prueba de ADM Red'
    )  # True or False


def user():
    # to use emailtest without previous login
    return dict(form=auth())