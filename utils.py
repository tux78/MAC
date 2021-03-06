import json
from msiempy import NitroConfig, NitroSession
from mesmpy import ESMSession

from dxlclient import _cli
from dxlclient.client import DxlClient
from dxlclient.client_config import DxlClientConfig

import base64

class IntegrationHandler:

    def __init__(self, basedir='./'):
        self._confDir = basedir + 'config/'
        self._models = {
            'dxl' : dxlConfig,
            'esm' : esmConfig
        }
        for key, value in self._models.items():
            setattr(self, key, value)
            getattr(self, key)._confDir = self._confDir

    def getModel(self, model):
        if model in self._models and hasattr(self, model):
            return getattr(self, model)
        return

    def execute(self, model, action, **kwargs):
        if hasattr(self._models[model], action):
            try:
                return getattr(self._models[model], action)(**kwargs)
            except AttributeError:
                return
        else:
            raise AttributeError

class dxlConfig:

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

    @classmethod
    @property
    def Client(self):
        configFile = self._confDir + 'dxlclient.config'
        config = DxlClientConfig.create_dxl_config_from_file(configFile)
        return DxlClient(config)

    @classmethod
    def getCurrentConfig(self):
        try:
            with open(self._confDir + 'dxlclient.config', 'r') as file:
                return file.read()
        except FileNotFoundError:
            return

    @classmethod
    def provision(self, host, user, password, cn, port='8443'):
        self.dxlProvisioningArguments.host = host
        self.dxlProvisioningArguments.user = user
        self.dxlProvisioningArguments.password = password
        self.dxlProvisioningArguments.port = port
        self.dxlProvisioningArguments.common_or_csrfile_name = cn
        self.dxlProvisioningArguments.config_dir = self._confDir
        dxlCommand = _cli.ProvisionDxlClientSubcommand()
        dxlCommand.execute(self.dxlProvisioningArguments)

    @classmethod
    def update(self, host, user, password, port='8443'):
        self.dxlProvisioningArguments.host = host
        self.dxlProvisioningArguments.user = user
        self.dxlProvisioningArguments.password = password
        self.dxlProvisioningArguments.port = port
        self.dxlProvisioningArguments.config_dir = self._confDir
        self.dxlCommand = _cli.UpdateConfigSubcommand()
        dxlCommand.execute(self.dxlProvisioningArguments)

class esmConfig:

    @classmethod
    @property
    def Session(self):
        return ESMSession(confDir=self._confDir)

    @classmethod
    @property
    def NitroSession(self):
        return NitroSession(NitroConfig(path=self._confDir + 'esmclient.config'))

    @classmethod
    def getCurrentConfig(self):
        try:
            with open(self._confDir + 'esmclient.config', 'r') as file:
                return file.read()
        except FileNotFoundError:
            return

    @classmethod
    def provision(self, host, user, password):
        if not host or not user or not password:
            raise AttributeError
        with open(self._confDir + 'esmclient.config', 'w') as file:
            file.write(self._str(host, user, password))
        return self

    @staticmethod
    def _str(host, user, password):
        return '[esm]\r\n'\
            + 'host = ' + host + '\r\n'\
            + 'user = ' + user + '\r\n'\
            + 'passwd = ' + base64.b64encode(password.encode('utf-8')).decode() + '\r\n'\
            + '[general]\r\n'\
            + 'timeout = 10\r\n'\
            + 'verbose = false\r\n'\
            + 'quiet = true\r\n'\
            + 'logfile = \r\n'\
            + 'ssl_verify = false'

class dsbConfig():
    dsbCaFile   : str = '/app/config/dsb_ca.pem'
    dsbCertFile : str = '/app/config/dsb_client.pem'
    dsbKeyFile  : str = '/app/config/dsb_client.pem'

    @classmethod
    def provision(self, confDir, dsbCaFile, dsbCertFile, dsbKeyFile):
        raise NotImplementedError
