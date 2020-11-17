import os
import threading
import json

from core import config

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
            myConfig.addApp(retVal['appID'], retVal['moduleID'])
            return redirect(url_for('get_config', appID=retVal['appID']))
        elif retVal['action'] == 'delete':
            myConfig.removeApp(retVal['appID'])
        elif retVal['action'] == 'start':
            myConfig.startApp(retVal['appID'])
        elif retVal['action'] == 'stop':
            myConfig.stopApp(retVal['appID'])
        elif retVal['action'] == 'restart':
            myConfig.stopApp(retVal['appID'])
            myConfig.startApp(retVal['appID'])
        else:
            return 'Application Error: unknown action'

    retVal = {}
    for appID, app in myConfig._apps_new.items():
        retVal[appID] = {
            'status' : 'started' if app.started() else 'stopped',
            'targets' : app.targets,
            'actions' : [bn_stop if app.started() else bn_start, bn_restart]
        }
    return render_template('apps.html', appStatus=retVal, modules=myConfig._modules_new)

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

        myConfig.updateApp(appID, **output)
        return redirect(url_for('get_apps'))

    return render_template(
        'config.html', 
        app=myConfig._apps_new[appID], 
        targets=myConfig.getTargets(),
        buttons=[bn_stop if myConfig._apps_new[appID].started() else bn_start]
    )

@api.route('/modules', methods=['GET','POST'])
def get_modules():

    if request.method == 'POST':
        retVal = dict(request.form)
        if retVal['action'] == 'create':
            myConfig.addModule(module=retVal['moduleID'])
            return redirect(url_for('get_module', moduleID=retVal['moduleID']))
        elif retVal['action'] == 'delete':
            myConfig.removeModule(module=retVal['moduleID'])

    return render_template('modules.html', modules=myConfig._modules_new)

@api.route('/module/<moduleID>', methods=['GET','POST'])
def get_module(moduleID):

    content = ''
    if request.method == 'POST':
        content = dict(request.form)['content']
        with open(myConfig._modules_new[moduleID].filename, "w") as moduleFile:
            moduleFile.write(content)
        return redirect(url_for('get_modules'))
    if not content:
        with open(myConfig._modules_new[moduleID].filename) as moduleFile:
            content = moduleFile.read()
    return render_template('module.html', moduleID=moduleID, moduleContent=content)

##### END FLASK #####

myConfig = config(configFile='config.json', basedir='/app/')

appRunning = {}

import importlib
import importlib.util
from core import module

def main():

    api.run(host='0.0.0.0')

if __name__ == "__main__":
    main()

