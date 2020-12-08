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

@api.route('/runners', methods=['GET','POST'])
def get_runners():
    if request.method == 'POST':
        retVal = dict(request.form)

        if retVal['action'] == 'create':
            extParameters = {key.split("_", 1)[1]: value for key, value in retVal.items() if key.startswith('parameters_')}
            targets = [key.split("_", 1)[1] for key in retVal if key.startswith('targets_')]
            print(str(retVal) + '||' + str(extParameters) + '||' + str(targets))
            myCore.addRunner(runnerID=retVal['runnerID'],
                module=retVal['module'],
                runner=retVal['runner'],
                interval = int(retVal['interval']),
                targets = targets,
                extParameters = extParameters
            )
        elif retVal['action'] == 'delete':
            myCore.removeApp(retVal['runnerID'])
        elif retVal['action'] == 'start':
            myCore.startApp(retVal['runnerID'])
        elif retVal['action'] == 'stop':
            myCore.stopApp(retVal['runnerID'])
        elif retVal['action'] == 'restart':
            myCore.stopApp(retVal['runnerID'])
            myCore.startApp(retVal['runnerID'])
        else:
            return 'Application Error: unknown action'

    retVal = myCore.getStatus()
    for key, value in retVal.items():
        retVal[key]['actions'] = [bn_stop if value['status'] else bn_start, bn_restart]
    return render_template('runners.html', runners=myCore.config.apps, modules=myCore.config.modules)

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

myCore = core()

appRunning = {}

def main():

    api.run(host='0.0.0.0')

if __name__ == "__main__":
    main()
