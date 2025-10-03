# coding: utf8

from threading import Thread

titles = {
    'inbox': 'Aviso de solicitud recibida',
    'sended': 'Aviso de solicitud enviada',
    'assign': 'Aviso de solicitud asignada',
    'reply': 'Aviso de solicitud respondida',
    'approve': 'Aviso de solicitud respondida',
    'disapprove': 'Aviso de respuesta desaprobada',
    'rate': 'Aviso de respuesta calificada por el usuario',
}

messages = {
    'inbox': 'Recibida la solicitud %(codigo)s\nObjetivo: %(objetivo)s',
    'sended': 'Enviada la solicitud %(codigo)s\nObjetivo: %(objetivo)s',
    'assign': 'Se le ha asignado la solicitud %(codigo)s\nObjetivo: %(objetivo)s',
    'reply': 'Respondida la solicitud  %(codigo)s\nObjetivo: %(objetivo)s',
    'approve': 'Respondida la solicitud  %(codigo)s\nObjetivo: %(objetivo)s',
    'disapprove': 'Desaprobada la respuesta a la solicitud  %(codigo)s\nObjetivo: %(objetivo)s',
    'rate': 'Calificada por el usuario la solicitud  %(codigo)s\nObjetivo: %(objetivo)s',
}


def run_in_thread(fn):
    def run(*k, **kw):
        t = Thread(target=fn, args=k, kwargs=kw)
        t.start()
        return t

    return run


@run_in_thread
def email_send(email_list, subject, message):
    footer = 'Acceda a la plataforma ADMRED en: https://192.168.90.169'
    # mail.send(to=email_list, subject=subject,
    #           message=message + '\n\n' + footer)


@run_in_thread
def sms_send(numbers, text):
    from applications.admred.modules.util import fetchPOST
    url = configuration.get('api_sms.enviar')
    # for number in numbers:
    #     data = {'number': number, 'text': text, 'sender': 'ADM Red'}
    #     fetchPOST(url, data)


@run_in_thread
def ws_send(data):
    import json
    from websocket_messaging import websocket_send
    websocket_send(configuration.get('websocket.url'),
                   json.dumps(data), '', 'admred')


def nota_insert(f, i):
    ws_send({
        'table': 'nota',
        'solicitud': int(f['solicitud'])
    })


db.nota._after_insert.append(nota_insert)


def solicitud_insert(f, i):
    if 'padre' in f:  # OpRow can contains all fields when managed by SQLFORM, and vars if managed by insert
        db.bitacora.insert(solicitud=f['padre'], accion='reenviada',
                           argumentos='generó la solicitud ' + f['codigo'])
    db.bitacora.insert(solicitud=i, accion='creada')
    ws_send({
        'table': 'solicitud',
        'type': 'create',
        'action': 'create',
        'id': i,
        'origen': f['origen'],
        'remitente': f['remitente'],
        'destino': f['destino']
    })
    q = db.auth_user.area == f['destino']
    q &= db.auth_membership.group_id == 2  # supervisor
    join = db.auth_membership.on(db.auth_user.id == db.auth_membership.user_id)
    users_to_notify = db(q).select(db.auth_user.movil,
                                   db.auth_user.email, join=join)
    moviles_to_notify = [r.movil for r in users_to_notify if r.movil]
    emails_to_notify = [r.email for r in users_to_notify if r.email]
    title = titles['inbox'] % f
    message = messages['inbox'] % f
    sms_send(moviles_to_notify, message)
    email_send(emails_to_notify, title, message)
    #  [feb 23, 2022] by Aldo: the 'remitente' must be notify by email
    title = titles['sended'] % f
    message = messages['sended'] % f
    if auth.user.email:
        email_send([auth.user.email], title, message)


db.solicitud._after_insert.append(solicitud_insert)


def solicitud_update(s, f):
    if not response.callback:
        return
    updated = s.select().first()
    ws_send({
        'table': 'solicitud',
        'type': 'update',
        'action': response.callback,
        'id': updated.id,
        'origen': updated.origen,
        'remitente': updated.remitente,
        'destino': updated.destino,
        'tramitador': updated.tramitador
    })
    title = titles[response.callback] % updated
    message = messages[response.callback] % updated
    if response.callback == 'assign':  # send notification via SMS / future: a smart function
        tramitador = db.auth_user(updated.tramitador)
        db.bitacora.insert(solicitud=updated.id, accion='asignada',
                           argumentos='a: ' + tramitador.username)
        if updated.tramitador != updated.supervisor:
            tramitador.movil and sms_send([tramitador.movil], message)
            tramitador.email and email_send([tramitador.email], title, message)

    if response.callback == 'reply':  # send notification via SMS to supervisor
        db.bitacora.insert(solicitud=updated.id, accion='respondida')
        if updated.tramitador != updated.supervisor:
            supervisor = db.auth_user(updated.supervisor)
            supervisor.movil and sms_send([supervisor.movil], message)
            supervisor.email and email_send([supervisor.email], title, message)

    if response.callback == 'approve':  # send notification via SMS to remitente
        db.bitacora.insert(solicitud=updated.id, accion='aprobada')
        if updated.remitente != updated.supervisor:
            remitente = db.auth_user(updated.remitente)
            remitente.movil and sms_send([remitente.movil], message)
            remitente.email and email_send([remitente.email], title, message)

    if response.callback == 'disapprove':  # send notification via SMS to tramitador
        db.bitacora.insert(solicitud=updated.id, accion='desaprobada')
        if updated.tramitador != updated.supervisor:
            tramitador = db.auth_user(updated.tramitador)
            tramitador.movil and sms_send([tramitador.movil], message)
            tramitador.email and email_send([tramitador.email], title, message)

        if request.vars.nota:
            db.nota.insert(
                solicitud=updated.id,
                fecha=request.now,
                # auth.user_id == updated.supervisor (or this action can not happen)
                supervisor=updated.supervisor,
                texto=request.vars.nota,
                evento='Respuesta rechazada'
            )


db.solicitud._after_update.append(solicitud_update)


def bitacora_insert(f, i):
    ws_send({
        'table': 'bitacora',
        'solicitud': int(f['solicitud'])
    })


db.bitacora._after_insert.append(bitacora_insert)
