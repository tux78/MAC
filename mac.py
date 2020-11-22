import os
import threading
import json

from core import core

from flask import Flask, render_template, request, redirect, url_for
from flask_restful import Resource, Api

bn_config = {
    'action' : 'config',
    'name'   : 'Config',
    'class'  : 'btn btn-outline-secondary'
}
bn_start = {
    'action' : 'start',
    'name'   : 'Start',
    'class'  : 'btn btn-outline-secondary'
}
bn_restart = {
    'action' : 'restart',
    'name'   : 'Restart',
    'class'  : 'btn btn-outline-secondary'
}
bn_stop = {
    'action' : 'stop',
    'name'   : 'Stop',
    'class'  : 'btn btn-outline-secondary'
}

##### FLASK API #####
api = Flask(__name__)

@api.route('/')
def index():
    return render_template('index.html')

@api.route('/debug')
def get_debug():
    return render_template('debug.html', threads=[thread.name for thread in threading.enumerate()])

@api.route('/apps', methods=['GET','POST'])
def get_apps():
    if request.method == 'POST':
        retVal = dict(request.form)

        if retVal['action'] == 'create':
            myCore.addApp(appID=retVal['appID'], moduleID=retVal['moduleID'])
            return redirect(url_for('get_config', appID=retVal['appID']))
        elif retVal['action'] == 'delete':
            myCore.removeApp(retVal['appID'])
        elif retVal['action'] == 'start':
            myCore.startApp(retVal['appID'])
        elif retVal['action'] == 'stop':
            myCore.stopApp(retVal['appID'])
        elif retVal['action'] == 'restart':
            myCore.stopApp(retVal['appID'])
            myCore.startApp(retVal['appID'])
        else:
            return 'Application Error: unknown action'

    retVal = myCore.getStatus()
    for key, value in retVal.items():
        retVal[key]['actions'] = [bn_stop if value['status'] else bn_start, bn_restart]
    return render_template('apps.html', appStatus=retVal, modules=myCore.config.modules)

@api.route('/config/<appID>', methods=['GET','POST'])
def get_config(appID):

    if request.method == 'POST':
        retVal = request.form
        output = {'extParameters' : {}, 'targets' : []}
        for key, value in retVal.items():
            key = key.split("_", 1)
            if key[0] == 'module':
                output[key[1]] = value
            elif key[0] == 'parameters':
                output['extParameters'][key[1]] = value
            elif key[0] == 'targets':
                output[key[0]].append(key[1])

        myCore.updateApp(appID, **output)
        return redirect(url_for('get_apps'))

    return render_template(
        'config.html', 
        app=myCore.config.apps[appID], 
        targets=myCore.getTargets(),
        buttons=[bn_stop if myCore.config.apps[appID].started() else bn_start]
    )

@api.route('/modules', methods=['GET','POST'])
def get_modules():

    if request.method == 'POST':
        retVal = dict(request.form)
        if retVal['action'] == 'create':
            myCore.addModule(moduleID=retVal['moduleID'])
            return redirect(url_for('get_module', moduleID=retVal['moduleID']))
        elif retVal['action'] == 'delete':
            myCore.removeModule(moduleID=retVal['moduleID'])

    return render_template('modules.html', modules=myCore.config.modules)

@api.route('/module/<moduleID>', methods=['GET','POST'])
def get_module(moduleID):

    content = ''
    if request.method == 'POST':
        content = dict(request.form)['content']
        myCore.updateModule(moduleID=moduleID, content=content)
        return redirect(url_for('get_modules'))
    content = myCore.getModuleContent(moduleID)
    return render_template('module.html', moduleID=moduleID, moduleContent=content)

@api.route('/integration', methods=['GET','POST'])
def get_integration():

    if request.method == 'POST':
        retVal = dict(request.form)
        myCore.integration.execute(**retVal)

    return render_template(
        'integration.html', 
        dxl=myCore.integration.execute('dxl', 'getCurrentConfig'),
        esm=myCore.integration.execute('esm', 'getCurrentConfig')
    )

##### END FLASK #####

myCore = core(configFile='config.json', basedir='/app/')

appRunning = {}

def main():

    api.run(host='0.0.0.0')

if __name__ == "__main__":
    main()

