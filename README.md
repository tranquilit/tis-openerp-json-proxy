tis-openerp-json-proxy
======================

JSON Proxy to OpenERP 6.0 server using NetRPC protocol.


Requirements
------------
python
flask
flask-openerp (https://github.com/matrixise/flask-openerp)
uwsgi

Installation
------------
easy_install uwsgi
easy_install flask
easy_install flask-sqlalchemy

wget "https://bitbucket.org/matrixise/flask-openerp/get/ef7310f26344.tar.gz"
tar -zxvf ef7310f26344.tar.gz
cd matrixise-flask-openerp-ef7310f26344/
python setup.py  install

