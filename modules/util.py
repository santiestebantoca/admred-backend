# -*- coding: utf-8 -*-
__author__ = 'jorge.santiesteban'


def search_from_vars(vars):
    from gluon.storage import Storage
    search = {k[2:]: v for k, v in vars.items() if k.startswith('s_')}
    return Storage(search)


def fetchPOST(url, data):
    from gluon._compat import urllib2, urlencode
    from gluon._compat import to_bytes
    from gluon._compat import urllib2, urlopen
    data_ = to_bytes(urlencode(data).encode('utf-8'))
    headers = {'Content-type': 'application/x-www-form-urlencoded',
               'User-agent': 'Mozilla/5.0'}
    req = urllib2.Request(
        url=url,
        data=data_,
        headers=headers)
    return urlopen(req)
