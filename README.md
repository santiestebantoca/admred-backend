## ADMRED

Aplicación web para la gestión de las solicitudes de servicio de la VPOR.

### Despliegue

- Prod:
  IP 192.168.90.169, Centos 7, python 2.7, web2py Version 2.27.1 For Python 2.7

- Dev:
  IP 192.168.11.231, Windows 10, python 3.8, web2py Version 2.27.1 For Python 3.7

#### Notas

La versión que está en este repositorio es la de Desarrollo.
Para Produccion se modifican los archivos que aparecen a continuación; la configuración para Producción aparece comentada.

1. private/appconfig.ini
2. web2py/websocket_messaging.py

Importante!
Se realizó una modificación a la distribución de web2py en Producción:
gluon/packages/dal/pydal/objects.py in store at line 2075
`dir(self)` instead of `self.__dir__()`

### Dependencias

- Prod:
  Python 2.7: Tornado 5.1.1

- Dev:
  Python 3.8: Tornado 6.0.2

### Websocket

Toda la funcionalidad está en: web2py/websocket_messaging.py

Este archivo fue modificado para permitir certificados autofirmados y asyncio en Windows

- Prod:
  Permitir el puerto 8888 en el Firewall
  Ejecutar websocket_messaging.py como servicio
  (https://tecadmin.net/setup-autorun-python-script-using-systemd/)

- Dev:
  Ejecutar D:\web2py\websocket.cmd

### Precisiones sobre Git

Además de lo que normalmente se hace para crear el repositorio, se añadieron dos líneas para manejar el certificado autofirmado y caducado por demás

El certificado .pem lo descargué con Firefox [Ver cetificado/Descargar]

- git config --global user.name "Jorge Lino Santiesteban Toca"
- git config --global user.email "jorge.santiesteban@etecsa.cu"
- git config --global http.sslCAInfo D:git-cav-etecsa-cu.pem
- git config --global http.sslVerify false
- git init
- git remote add origin https://git.cav.etecsa.cu/jorge.santiesteban/admred.git
- git add .
- git commit -m "Initial commit"
- git push -u origin master

---

Editado por: Jorge Lino Santiesteban Toca.
