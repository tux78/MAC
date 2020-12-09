import importlib
import threading, queue

import json
import os

from messageBroker import messageBrokerFactory, appError
from utils import IntegrationHandler

from dxlclient import _cli

import sys
MIN_PYTHON = (3, 9)
assert sys.version_info >= MIN_PYTHON, f"requires Python {'.'.join([str(n) for n in MIN_PYTHON])} or newer"

class appFactory(messageBrokerFactory, threading.Thread):

    def __init__(self, app):
        threading.Thread.__init__(self)
        self.status = 'Initializing App'
        self.app = app
        self.action = threading.Event()
        self.processQueue = queue.Queue()
        self.produceQueue = queue.Queue()

    def run(self):
        self.name = 'APP-' + self.app.appID
        super().__init__(self.app.appID, self.action, self.app.targets,)

        self.status = 'Initializing ' + self.app.module.moduleClassName
        try:
            obj = self.app.module.extClass(**self.app.extParameters)
            self.call = getattr(obj, self.app.runner)
        except Exception as err:
            self.stop(str(err))
        self.status = 'Applying ' + self.app.module.moduleClassName + ' handlers'
        if len(self.call.__code__.co_varnames[1:self.call.__code__.co_argcount]) > 0:
            self.process = self.call
        else:
            self.consume = self.call

        self.status = 'starting'
        consumeThread = threading.Thread(target=self.appConsume, name=self.name + '-consumer')
        processThread = threading.Thread(target=self.appProcess, name=self.name + '-processor')
        produceThread = threading.Thread(target=self.appProduce, name=self.name + '-producer')
        consumeThread.start()
        processThread.start()
        produceThread.start()

        self.status = 'running'
        while not self.action.is_set() and self.status == 'running':
            pass

        obj = ''

    def stop(self, reason = 'regular stop'):
        self.status = 'stopped ' + self.app.module.moduleClassName + '. Reason: ' + reason
        self.action.set()
        threading.Thread.join(self)

    def appConsume(self):
        while not self.action.is_set():
            try:
                for payload in self.consume():
                    self.processQueue.put(payload)
                self.action.wait(self.app.interval)
            except Exception as err:
                self.stop(str(err))

    def appProcess(self):
        while not self.action.is_set():
            if not self.processQueue.empty():
                payload = self.processQueue.get(block=False)
                try:
                    payload = self.process(payload)
                    self.produceQueue.put(payload)
                except Exception as err:
                    self.stop(str(err))

    def appProduce(self):
        while not self.action.is_set():
            if not self.produceQueue.empty():
                payload = self.produceQueue.get(block=False)
                try:
                    self.produce(payload)
                except Exception as err:
                    self.stop(str(err))

    def process(self, payload):
        return payload

    def getThreads(self):
        return [thread.name for thread  in threading.enumerate()]

class core:

    def __init__(self, configFile='config/config.json', basedir='./'):
        self.config = config(configFile=configFile, basedir=basedir)
        self._integration = IntegrationHandler(basedir)

    ############
    # UI actions
    ############
    def getTargets(self):
        return self.config.apps.keys()

    def getStatus(self):
        retVal = {}
        for app in self.config.apps.values():
            retVal[app.appID] = {
                'status'     : app.started(),
                'statusCode' : app.status(),
                'targets'    : app.targets
            }
        return retVal

    def getModuleContent(self, moduleID):
        with open(self.config.modules[moduleID].filename) as moduleFile:
            content = moduleFile.read()
        return content

    #####################
    # Integration Actions
    #####################
    @property
    def integration(self):
        return self._integration

    ################
    # Runner actions
    ################
    def addRunner(self, runnerID, module, runner, interval, targets, extParameters):
        self.config.addApp(appID = runnerID,
            moduleID = module,
            runner = runner,
            interval = interval,
            targets = targets,
            extParameters = extParameters
        )

    #############
    # App actions
    #############
    def addApp(self, appID, moduleID, **kwargs):
        self.config.addApp(appID = appID, moduleID = moduleID)

    def updateApp(self, appID, **kwargs):
        self.config.updateApp(appID = appID, **kwargs)

    def removeApp(self, appID):
        self.config.removeApp(appID)

    def startApp(self, appID):
        self.config.startApp(appID)

    def stopApp(self, appID):
        self.config.stopApp(appID)

    ################
    # Module actions
    ################
    def addModule(self, moduleID):
        self.config.addModule(moduleID = moduleID)

    def updateModule(self, moduleID, content):
        self.config.updateModule(moduleID = moduleID, content = content)

    def removeModule(self, moduleID):
        self.config.removeModule(moduleID = moduleID)

##############
# Data Classes
##############
from dataclasses import dataclass, field

@dataclass
class function:
    call         : type
    inbound      : [str]
    configParams : {str: str}
    annotations  : {str: str}

@dataclass
class module:
    moduleClassName : str
    moduleName      : str
    extClass        : type
    filename        : str
    requiredParams  : [str] = field(init=False, repr=False)
    availCalls      : [str] = field(init=False, repr=False)
    functions       : {str: function} = field(init=False)

    def __post_init__(self):
        if not self.extClass:
            self.extClass = getattr(importlib.import_module(self.moduleName), self.moduleClassName)
        params = self.extClass.__init__.__code__\
            .co_varnames[1:self.extClass.__init__.__code__.co_argcount]
        defaults = self.extClass.__init__.__defaults__
        self.requiredParams = dict(zip(params, ['(String)'] * (len(params)-(0 if not defaults else len(defaults))) + ([] if not defaults else list(defaults))))
        self.availCalls = [call for call in dir(self.extClass) if not call[0] == '_']
        self.functions = {}

        for call in [getattr(self.extClass, call) for call in dir(self.extClass) if not call[0] == '_']:
            self.functions[call] = function(
                call = call,
                inbound = call.__code__.co_varnames[1:call.__code__.co_argcount],
                configParams = call.__kwdefaults__,
                annotations = call.__annotations__
            )

@dataclass
class app:
    appID         : str
    module        : module
    runner        : str = ''
    interval      : int = 0
    targets       : list[str] = ()
    extParameters : list[tuple] = ()

    _appInstance  : type = field(init=False)

    def __post_init__(self):
        self._appInstance = ''

    def start(self):
        if not self._appInstance:
            self._appInstance = appFactory(
                self,
            )
        self._appInstance.start()

    def started(self):
        return True if self._appInstance else False

    def stop(self):
        if self._appInstance:
            self._appInstance.stop()
        self._appInstance = ''

    def status(self):
        return (self._appInstance.status if self._appInstance else 'stopped')

    def write(self):
        return {
            'module'    : self.module.moduleClassName,
            'runner'    : self.runner,
            'interval'  : self.interval,
            'targets'   : self.targets,
            'parameters': self.extParameters
        }

@dataclass
class config:
    basedir    : str
    configFile : str
    modules    : { str : module } = field(init=False)
    apps       : { str : app} = field(init=False)

    def __post_init__(self):
        self.modules = self._getModules()
        self.apps = self._readConfig()

    def _getModules(self):
        _modules = {}
        for subdir, dirs, files in os.walk(self.basedir + 'extensions'):
            for filename in files:
                filepath = subdir + os.sep + filename

                if filename.endswith(".py"):
                    moduleName = filepath[len(self.basedir):-3].replace('/', '.')
                    newModule = importlib.import_module(moduleName)
                    importlib.invalidate_caches()
                    newModule = importlib.reload(newModule)
                    for key, value in newModule.__dict__.items():
                        if type(value) is type and value.__module__ == moduleName:
                            _modules[key] = module(**{
                                'moduleClassName' : key,
                                'moduleName'      : moduleName,
                                'extClass'        : newModule.__dict__[key],
                                'filename'        : filepath
                            })
        return _modules

    def _readConfig(self):
        _apps = {}
        with open(self.basedir + self.configFile) as configFile:
            config = json.load(configFile)

            for key, value in config.items():
                _apps[key] = app(
                    appID = key,
                    module = self.modules[value['module']],
                    runner = value['runner'],
                    interval = int(value['interval']),
                    targets = value['targets'],
                    extParameters = value['parameters']
                )
        return _apps

    def _writeConfig(self, backup=True):
        if backup:
            with open(self.basedir + self.configFile) as configFile:
                config = json.load(configFile)
            with open(self.basedir + self.configFile + '.bak', 'w') as configFile:
                configFile.write(json.dumps(config, indent=4))

        with open(self.basedir + self.configFile, 'w') as configFile:
            config = dict((app.appID, app.write()) for app in self.apps.values())
            configFile.write(json.dumps(config, indent=4))

    ###################
    # Module operations
    ###################
    def addModule(self, moduleID):
        filename = self.basedir + 'extensions/' + moduleID + '.py'
        with open(filename, 'a') as moduleFile:
           moduleFile.write('class ' + moduleID + ':\r\n' +
"""\

    def __init__(self, username, ip):
        self.username = username
        self.ip = ip
        # initialize any required internal variables
        # such as credentials, IP addresses etc

    def getData(self):
        # this is stub code
        # please replace with some functional logic
        myTool = SomeThirdparty.connect(self.ip, self.username)
        payload = myTool.CollectData()
        # yield data to be processed by MAC
        yield payload

    def processData(self, payload):
        # send payload to desired destination
        # file output, consumer
        myTool = SomeThirdparty.connect(self.ip, self.username)
        myTool.PublishData(payload)

        # if data may be processed by subsequent apps/targets,
        # the payload can be yielded
        yield payload
"""
           )
        self.modules = self._getModules()

    def updateModule(self, moduleID, content):
        with open(self.modules[moduleID].filename, "w") as moduleFile:
            moduleFile.write(content)
        self.modules = self._getModules()
        # after the Module update the classes within the Apps 
        # have to be updated as well; based on their status they are restarted
        for app in self.apps.values():
            if app.module.moduleClassName == moduleID:
                status = app.started()
                if status:
                    app.stop()                
                app.module = self.modules[moduleID]
                if status:
                    app.start()

    def removeModule(self, moduleID):
        filename = self.modules[moduleID].filename
        os.remove(filename)
        self.modules = self._getModules()

    ################
    # App Operations
    ################
    def addApp(self, appID, moduleID, **kwargs):
        self.apps[appID] = app(
            appID = appID,
            module = self.modules[moduleID],
            **kwargs
        )
        self._writeConfig()

    def updateApp(self, appID, **kwargs):
        for key, value in kwargs.items():
            setattr(self.apps[appID], key, value)
        self._writeConfig()

    def removeApp(self, appID):
        self.apps.pop(appID)
        self._writeConfig()

    def startApp(self, appID):
        self.apps[appID].start()

    def stopApp(self, appID):
        self.apps[appID].stop()
