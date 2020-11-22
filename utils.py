import json
from dxlclient import _cli
from msiempy import NitroConfig
from mesmpy import ESMCore

import base64

class IntegrationHandler:

    def __init__(self, basedir):
        self._confDir = basedir + 'config/'
        self._models = {
            'dxl' : dxlConfig,
            'esm' : esmConfig
        }
        for key, value in self._models.items():
            setattr(self, key, value)

    def getModel(self, model):
        if model in self._models and hasattr(self, model):
            return getattr(self, model)
        return

    def execute(self, model, action, **kwargs):
        if hasattr(self._models[model], action):
            try:
                return getattr(self._models[model], action)(confDir=self._confDir, **kwargs)
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
    def getCurrentConfig(self, confDir):
        try:
            with open(confDir + 'dxlclient.config', 'r') as file:
                return file.read()
        except FileNotFoundError:
            return

    @classmethod
    def provision(self, confDir, host, user, password, cn, port='8443'):
        self.dxlProvisioningArguments.host = host
        self.dxlProvisioningArguments.user = user
        self.dxlProvisioningArguments.password = password
        self.dxlProvisioningArguments.port = port
        self.dxlProvisioningArguments.common_or_csrfile_name = cn
        self.dxlProvisioningArguments.config_dir = confDir
        dxlCommand = _cli.ProvisionDxlClientSubcommand()
        dxlCommand.execute(dxlProvisioningArguments)

    @classmethod
    def update(self, confDir, host, user, password, port='8443'):
        self.dxlProvisioningArguments.host = host
        self.dxlProvisioningArguments.user = user
        self.dxlProvisioningArguments.password = password
        self.dxlProvisioningArguments.port = port
        self.dxlProvisioningArguments.config_dir = confDir
        self.dxlCommand = _cli.UpdateConfigSubcommand()
        dxlCommand.execute(dxlProvisioningArguments)

class esmConfig():

    @classmethod
    def getCurrentConfig(self, confDir):
        try:
            with open(confDir + 'esmclient.config', 'r') as file:
                return file.read()
        except FileNotFoundError:
            return

    @classmethod
    def getNitroConfig(self, confDir):
        return NitroConfig(path=confDir + 'esmclient.config')

    @classmethod
    def getESM(self, confDir):
        return ESMCore(confDir=confDir)

    @classmethod
    def provision(self, confDir, host, user, password):
        if not host or not user or not password:
            raise AttributeError
        with open(confDir + 'esmclient.config', 'w') as file:
            file.write(self._str(host, user, password))
        return self

    @staticmethod
    def _str(host, user, password):
        return '[esm]\r\n'\
            + 'host = ' + host + '\r\n'\
            + 'user = ' + user + '\r\n'\
            + 'passwd = ' + base64.b64encode(password.encode('utf-8')).decode()\
            + '[general]\r\n'\
            + 'timeout = 10\r\n'\
            + 'ssl_verify = false'

class dsbConfig():
    dsbCaFile   : str = '/app/config/dsb_ca.pem'
    dsbCertFile : str = '/app/config/dsb_client.pem'
    dsbKeyFile  : str = '/app/config/dsb_client.pem'

    @classmethod
    def provision(self, confDir, dsbCaFile, dsbCertFile, dsbKeyFile):
        raise NotImplementedError
