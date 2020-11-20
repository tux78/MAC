import importlib
import threading, queue

import json
import os

from messageBroker import messageBrokerFactory, appError
from dxlclient import _cli

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
        processThread = threading.Thread(target=self.appProcess, name=self.name + '-processor')
        produceThread = threading.Thread(target=self.appProduce, name=self.name + '-producer')
        consumeThread.start()
        processThread.start()
        produceThread.start()

        while not self.action.is_set():
            pass

        obj = ''

    def stop(self):
        self.status = 'stopping ' + self.app.module.moduleClassName
        self.action.set()
        threading.Thread.join(self)

    def appConsume(self):
        try:
            for payload in self.consume(**{'sentinel' : self.action, 'interval' : int(self.app.interval)}):
                self.processQueue.put(payload)
        except Exception as err:
            self.status = 'failure (please check module code): ' + str(err)

        self.stop()


    def appProcess(self):
        while not self.action.is_set():
            if not self.processQueue.empty():
                payload = self.processQueue.get(block=False)
                try:
                    payload = self.process(payload)
                except Exception as err:
                    self.status = 'failure (please check module code): ' + str(err)
                self.produceQueue.put(payload)

    def appProduce(self):
        while not self.action.is_set():
            if not self.produceQueue.empty():
                payload = self.produceQueue.get(block=False)
                try:
                    self.produce(payload)
                except Exception as err:
                    self.status = 'failure (please check module code): ' + str(err)

    def process(self, payload):
        return payload

    def getThreads(self):
        return [thread.name for thread  in threading.enumerate()]

class core:

    def __init__(self, configFile='config.json', basedir="/app/"):
        self.config = config(configFile=configFile, basedir=basedir)

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

    #############
    # DXL Actions
    #############
    def getDXLConfig(self):
        try:
            with open(self.config.basedir + 'dxlconfig/dxlclient.config', 'r') as dxlConfigFile:
                content = dxlConfigFile.read()
        except:
            print('File ' + self.config.basedir + 'dxlconfig/dxlclient.config' + ' not found')
            content = ''
        return content

    def provisionDXL(self, host, user, password, port='8443', cn='MAC Application'):
        dxlProvisioningArguments.host = host
        dxlProvisioningArguments.user = user
        dxlProvisioningArguments.password = password
        dxlProvisioningArguments.port = port
        dxlProvisioningArguments.common_or_csrfile_name = cn
        dxlProvisioningArguments.config_dir = self.config.basedir + 'dxlconfig/'
        dxlCommand = _cli.ProvisionDxlClientSubcommand()
        dxlCommand.execute(dxlProvisioningArguments)

    def updateDXL(self, host, user, password, port='8443'):
        dxlProvisioningArguments.host = host
        dxlProvisioningArguments.user = user
        dxlProvisioningArguments.password = password
        dxlProvisioningArguments.port = port
        dxlProvisioningArguments.config_dir = self.config.basedir + 'dxlconfig/'
        dxlCommand = _cli.UpdateConfigSubcommand()
        dxlCommand.execute(dxlProvisioningArguments)


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
        return (self._appInstance.status if self._appInstance else 'stopped')

    def write(self):
        return {
            'module'    : self.module.moduleClassName,
            'consume'   : self.consume,
            'process'   : self.process,
            'produce'   : self.produce,
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
        self.apps = self._getApps()

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

    def _getApps(self):
        _apps = {}
        with open(self.basedir + self.configFile) as configFile:
            config = json.load(configFile)

            for key, value in config.items():
                _apps[key] = app(
                    appID = key,
                    module = self.modules[value['module']],
                    consume = value['consume'],
                    process = value['process'],
                    produce = value['produce'],
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
           moduleFile.write('import threading\r\n\r\nclass ' + moduleID + ':\r\n' +
"""\

    def __init__(self, username, ip):
        self.username = username
        self.ip = ip
        # initialize any required internal variables
        # such as credentials, IP addresses etc

    def getDataOnce(self, **kwargs):
        yield 'some data'

    def getDataAsStream(self, sentinel : threading.Event = threading.Event(), interval : int = 3600):
        while not sentinel.is_set():
            # enter code here
            # for continuous processing, have interval = 0
            # the interval can be configured from within the App configuration
            yield 'some data'
            sentinel.wait(interval)

    def sendData(self, payload):
        # send payload to desired destination
        # file output, consumer
        pass
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

class dxlProvisioningArguments:
    # Hostinfo
    host       = '' # required
    user       = '' # required
    password   = '' # required
    port       = '8443' # default/required
    truststore = ''
    # Config
    config_dir = '' # default
    # Certificate
    file_prefix            = 'client' # default
    san                    = None
    passphrase             = None
    country                = None
    state_or_province      = None
    locality               = None
    organization           = None
    organizational_unit    = None
    email_address          = None
    # optional / provisioning
    cert_request_file      = None
    common_or_csrfile_name = 'MAC Application' # default/required

