# -*- coding: utf-8 -*-
__author__ = 'jorge.santiesteban'


def fetchPOST(url, data):
    from gluon._compat import urllib2, urlencode
    from gluon._compat import to_bytes
    from gluon._compat import urllib2, urlopen
    data_ = to_bytes(urlencode(data).encode('utf-8'))
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    req = urllib2.Request(
        url=url,
        data=data_,
        headers=headers)
    return urlopen(req)
