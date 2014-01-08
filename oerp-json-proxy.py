#!/usr/bin/env python
from flask import Flask
from flask import g
from flaskext.openerp import OpenERP, Object, Connection
from flaskext.rpc import NetRPC_Exception
from flaskext.rpc import Database,Common
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash , jsonify, escape
import json

class DefaultConfig(object):
    OPENERP_PROTOCOL = 'netrpc'
    OPENERP_HOSTNAME = 'srvopenerp6-prod'
    OPENERP_DATABASE = 'tranquil_production'
    OPENERP_DEFAULT_USER = ''
    OPENERP_DEFAULT_PASSWORD = ''
    OPENERP_PORT = 18070

    SECRET_KEY = 'secret_keysfsdfsdfsdf'

    DEBUG = True

app = Flask(__name__)
app.config.from_object(DefaultConfig())
openerp = OpenERP(app)


@app.route('/models',methods=['GET'])
def models():
    proxy = Object(g.openerp_cnx,'ir.model')
    models = proxy.select([],['model'])
    return json.dumps(models)

@app.route('/object/<object_name>/<method>',methods=['GET','POST'])
def get_object(object_name,method):
    """Generic proxy to OpenERP osv.model methods"""
    context = json.loads(request.args.get('context','{}'))
    oobject = Object(g.openerp_cnx,object_name)
    try:
        if 'args' in request.values:
            args = json.loads(request.values.get('args','null'))
            methodobj = getattr(oobject,method)
            data = methodobj(*args)
        elif method == 'create' and 'values' in request.args:
            values=json.loads(request.args.get('values','null'))
            data = oobject.create(values,context)
        elif method == 'check_access_rule' and 'ids' in request.args:
            ids = request.args.get('ids',None)
            if ids:
                ids = [ int(i) for i in ids.split(',')]
            operation = request.args.get('operation')
            if not operation in ['write','unlink']:
                raise Exception('operation parameter must be either write or unlink')
            data = oobject.check_access_rule(ids,operation,context)
        elif method == 'search':
            domain = json.loads(request.args.get('domain','null'))
            order = request.args.get('order',None)
            offset = request.args.get('offset',None)
            limit  = request.args.get('limit',None)
            count = request.args.get('count','')
            count = True if count == 'true' else False
            data = oobject.search(domain,int(offset) if offset else None,int(limit) if limit else None,order,context,count)
        elif method == 'read':
            ids = request.args.get('ids',None)
            if ids:
                ids = [ int(i) for i in ids.split(',')]
            fields = request.args.get('fields',None)
            if fields:
                fields = fields.split(',')
            data = oobject.read(ids,fields,context)
        elif method == 'write':
            ids = request.args.get('ids',None)
            if ids:
                ids = [ int(i) for i in ids.split(',')]
            values = json.loads(request.args.get('values','null'))
            data = oobject.write(ids,values,context)
        elif method == 'copy' and 'id' in request.args:
            oid = int(request.args.get('id'))
            defaults=json.loads(request.args.get('defaults','null'))
            data = oobject.copy(oid,defaults,context)
        elif method == 'unlink' and 'ids' in request.args:
            ids = request.args.get('ids',None)
            if ids:
                ids = [ int(i) for i in ids.split(',')]
            data = oobject.unlink(ids,context)
        elif method == 'default_get' and 'fields' in request.args:
            fields = request.args.get('fields',None)
            if fields:
                fields = fields.split(',')
            data = oobject.default_get(fields,context)
        elif method == 'perm_read':
            ids = request.args.get('ids',None)
            if ids:
                ids = [ int(i) for i in ids.split(',')]
            details = request.args.get('details','true')
            details = True if details.lower() == 'true' else False
            data = oobject.perm_read(ids,context,details)
        elif method == 'fields_get':
            fields = request.args.get('fields',None)
            if fields:
                fields = fields.split(',')
            data = oobject.fields_get(fields,context)
        elif method == 'select':
            fields = request.args.get('fields',None)
            if fields:
                fields = fields.split(',')
            domain = json.loads(request.args.get('domain','null'))
            order = request.args.get('order',None)
            offset = request.args.get('offset',None)
            limit  = request.args.get('limit',None)
            data = oobject.select(domain=domain,fields=fields,offset=int(offset) if offset else None,limit=int(limit) if limit else None,order=order,context=context)
        elif method == 'name_search':
            name = request.args.get('name','')
            domain=json.loads(request.args.get('domain','null'))
            operator=request.args.get('operator','ilike')
            limit= request.args.get('limit',None)
            data = oobject.name_search(name,domain,operator,context,int(limit) if limit else None)
        elif method == 'name_get':
            ids = request.args.get('ids',None)
            if ids:
                ids = [ int(i) for i in ids.split(',')]
            data = oobject.name_get(ids,context)
        elif method == 'apply_updates':
            delta = json.loads(request.form.get('delta','null'))
            context = json.loads(request.form.get('context','null'))
            print delta
            updated_ids = []
            if delta:
                for rec_update in delta:
                    try:
                        id = rec_update['id']
                        del(rec_update['id'])
                        if len(rec_update) == 0:
                            oobject.unlink(id,context)
                            updated_ids.append([id,None])
                        elif id<=0:
                            updated_ids.append([id, oobject.create(rec_update,context)])
                        else:
                            oobject.write(id,rec_update,context)
                            updated_ids.append([id,id])
                    except NetRPC_Exception,e:
                        #raise
                        updated_ids.append([id,{'error':e.__class__.__name__,'message':"%s" % (e,),'rec_update':rec_update}])

            data = updated_ids

        else:
            args = json.loads(request.values.get('args','null'))
            methodobj = getattr(oobject,method)
            data = methodobj(*args)
    except NetRPC_Exception,e:
        #raise
        return json.dumps({'error':e.__class__.__name__,'message':"%s" % (e,),'url':request.url})

    print "hello"
    try:
        return json.dumps(data)
    except:
        return data

@app.route('/apply_updates',methods=['GET'])
def apply_updates():
    """Prends un tableau de (modelname,dict_updates)
       le dict contient les valeurs pour les mises a jour insert,update,delete et les applique
       retourne un tableau de correspondances (modelname,id temporaires,id inseres pour les inserts)
       si id seul : delete
       si id<=0 : insert
       si id>0 : update"""
    delta = json.loads(request.args.get('delta','null'))
    context = json.loads(request.args.get('context','null'))
    oobjects = {}
    updated_ids = []
    if delta:
        for (modelname,rec_update) in delta:
            if not modelname in oobjects:
                oobjects[modelname] = Object(g.openerp_cnx,modelname)
            oobject = oobjects[modelname]
            id = rec_update['id']
            del(rec_update['id'])
            if len(rec_update) == 0:
                oobject.unlink(id,context)
                updated_ids.append([modelname,id,None])
            elif id<=0:
                updated_ids.append([modelname,id, oobject.create(rec_update,context)])
            else:
                oobject.write(id,rec_update,context)
                updated_ids.append([modelname,id,id])

    return json.dumps(updated_ids)


@app.route('/testgui',methods=['GET'])
def testgui():
    return render_template('testgui.html',json = 'test'  )


@app.route('/')
def index():
    if 'openerp_user_id' in session:
        return "OpenERP JSON -> Net-RPC proxy "+'Logged in as %s' % escape(session['openerp_user_id'])
    return "OpenERP JSON -> Net-RPC proxy"

@app.route('/login', methods=['GET', 'POST'])
def login():
    session['openerp_login'] = request.values.get('openerp_login',None)
    session['openerp_password'] = request.values.get('openerp_password',None)
    try:
        cnx = Connection(openerp.connector,
                              app.config['OPENERP_DATABASE'],
                              session['openerp_login'],
                              session['openerp_password'])
        session['openerp_user_id'] = cnx.user_id
        return "%s" % cnx.user_id
    except:
        session.pop('openerp_user_name', None)
        session.pop('openerp_user_id', None)
        session.pop('openerp_password', None)
        return "-1"


@app.route('/logout')
def logout():
    # remove the username from the session if it's there
    session.pop('openerp_user_name', None)
    session.pop('openerp_user_id', None)
    session.pop('openerp_password', None)
    return 'ok'


@app.route('/db/<method>')
def db(method):
    args = request.values.get('args',[])
    return  json.dumps(getattr(Database(g.openerp_cnx.connector),method)(*args))

@app.route('/common/<method>')
def common(method):
    return  json.dumps(getattr(Common(g.openerp_cnx.connector),method)())


print "test"

if __name__ == "__main__":
  app.run(host='0.0.0.0',port=8000, debug=False)


