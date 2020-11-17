import importlib
import threading, queue

import json
import os

from messageBroker import messageBrokerFactory, appError

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
        super().__init__(self.app.appID, self.app.targets)

        self.status = 'Initializing ' + self.app.module.moduleClassName
        obj = self.app.module.extClass(**self.app.extParameters)
        self.status = 'Applying ' + self.app.module.moduleClassName + ' handlers'
        if self.app.consume:
            self.consume = getattr(obj, self.app.consume)
        if self.app.process:
            self.process = getattr(obj, self.app.process)
        if self.app.produce:
            self.produce = getattr(obj, self.app.produce)

        self.status = 'running'

        consumeThread = threading.Thread(target=self.appConsume, name=self.name + '-consumer')
        consumeThread.start()
        processThread = threading.Thread(target=self.appProcess, name=self.name + '-processor')
        processThread.start()
        produceThread = threading.Thread(target=self.appProduce, name=self.name + '-producer')
        produceThread.start()

        while not self.action.is_set():
            pass

        obj = ''

    def stop(self):
        self.status = 'stopping ' + self.app.module.moduleClassName
        self.action.set()
        threading.Thread.join(self)

    def appConsume(self):
        while not self.action.is_set():
            for payload in self.consume(sentinel=self.action, interval=self.app.interval):
                self.processQueue.put(payload)


    def appProcess(self):
        while not self.action.is_set():
            if not self.processQueue.empty():
                payload = self.processQueue.get(block=False)
                payload = self.process(payload)
                self.produceQueue.put(payload)

    def appProduce(self):
        while not self.action.is_set():
            if not self.produceQueue.empty():
                payload = self.produceQueue.get(block=False)
                self.produce(payload)

    def process(self, payload):
        return payload

    def getThreads(self):
        return [thread.name for thread  in threading.enumerate()]

class config:

    _modules_new = {}
    _apps_new = {}

    def __init__(self, configFile='config.json', basedir="/app/"):
        self.basedir = basedir
        self.configFile = self.basedir + configFile
        self.reloadConfig()

    def reloadConfig(self):
        with open(self.configFile) as configFile:
            config = json.load(configFile)
            #for moduleName, moduleContent in self._getModules().items():
            #    self._modules_new[moduleName] = module(**moduleContent)
            self._modules_new = self._getModules()

            for key, value in config.items():
                self._apps_new[key] = app(
                    appID = key,
                    module = self._modules_new[value['module']],
                    consume = value['consume'],
                    process = value['process'],
                    produce = value['produce'],
                    interval = int(value['interval']),
                    targets = value['targets'],
                    extParameters = value['parameters']
                )

    def writeConfig(self, backup=True):
        if backup:
            with open(self.configFile) as configFile:
                config = json.load(configFile)
            with open(self.configFile + '.bak', 'w') as configFile:
                configFile.write(json.dumps(config, indent=4))

        with open(self.configFile, 'w') as configFile:
            config = dict((app.appID, app.write()) for app in self._apps_new.values())
            configFile.write(json.dumps(config, indent=4))

    def getTargets(self):
        return self._apps_new.keys()

    def addApp(self, appID, module, **kwargs):
        self._apps_new[appID] = app(
            appID = appID,
            module = self._modules_new[module]
        )

    def updateApp(self, appID, **kwargs):
        for key, value in kwargs.items():
            setattr(self._apps_new[appID], key, value)
        self.writeConfig()

    def removeApp(self, appID):
        self._apps_new.pop(appID)
        self.writeConfig()

    def startApp(self, appID):
        self._apps_new[appID].start()

    def stopApp(self, appID):
        self._apps_new[appID].stop()

    def addModule(self, module):
        filename = self.basedir + 'extensions/' + module  + '.py'
        with open(filename, 'a') as moduleFile:
           moduleFile.write('import threading\r\n\r\nclass ' + module + ':\r\n' + 
"""\

    def __init__(self, username, ip):
        self.username = username
        self.ip = ip
        # initialize any required internal variables
        # such as credentials, IP addresses etc

    def getData(self, sentinel : threading.Event = threading.Event(), interval : int = 3600):
        while not sentinel.is_set():
            # enter code here
            # for continuous processing, have interval = 0
            sentinel.wait(interval)

    def sendData(self, payload):
        # send payload to desired destination
        # file output, consumer
        pass
"""
           )
        self._modules_new = self._getModules()

    def removeModule(self, module):
        filename = self._modules_new[module].filename
        os.remove(filename)
        self._modules_new = self._getModules()

    ############################
    # private functions
    ############################
    def _getModules(self):
        _modules = {}
        for subdir, dirs, files in os.walk(self.basedir + 'extensions'):
            for filename in files:
                filepath = subdir + os.sep + filename

                if filename.endswith(".py"):
                    moduleName = filepath[len(self.basedir):-3].replace('/', '.')
                    spec = importlib.util.spec_from_file_location(moduleName, filepath)
                    foo = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(foo)
                    for key, value in foo.__dict__.items():
                        if type(value) is type and value.__module__ == moduleName:
                            _modules[key] = module(**{
                                'moduleClassName' : key,
                                'moduleName'      : moduleName,
                                'extClass'        : foo.__dict__[key],
                                'filename'        : filepath
                            })
        return _modules

from dataclasses import dataclass, field

@dataclass
class module:
    moduleClassName : str
    moduleName      : str
    extClass        : type
    filename        : str
    requiredParams  : list[str] = field(init=False, repr=False)
    availCalls      : list[str] = field(init=False, repr=False)

    def __post_init__(self):
        if not self.extClass:
            self.extClass = getattr(importlib.import_module(self.moduleName), self.moduleClassName)
        self.requiredParams = self.extClass.__init__.__code__.co_varnames[1:self.extClass.__init__.__code__.co_argcount]
        self.availCalls = [call for call in dir(self.extClass) if not call[0] == '_']

    def write(self):
        return self.moduleClassName, self.moduleName

@dataclass
class app:
    appID         : str
    module        : module
    consume       : str = ''
    process       : str = ''
    produce       : str = ''
    interval      : int = 0
    targets       : list[str] = ()
    extParameters : list[tuple] = ()

    _appInstance        : type = field(init=False)

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
        return (self._obj.status if self._obj else 'stopped')

    def write(self):
        return {
            'module'    : self.module.moduleClassName,
            'consume'  : self.consume,
            'process'  : self.process,
            'produce'   : self.produce,
            'interval'  : self.interval,
            'targets'   : self.targets,
            'parameters': self.extParameters
        }
